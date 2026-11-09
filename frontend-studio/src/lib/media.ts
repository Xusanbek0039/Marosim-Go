"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";
import type { Paginated } from "./types";

export type MediaKind = "PHOTO" | "VIDEO";
export type MediaStatus = "UPLOADING" | "READY" | "FAILED" | "CANCELLED" | "EXPIRED" | "DELETED";

export interface StudioMedia {
  id: string;
  kind: MediaKind;
  status: MediaStatus;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  duration_ms: number | null;
  error_code: string;
  uploaded_by_name: string | null;
  /** Pending request for an admin to delete this READY file, or null. */
  deletion_request: { id: string; reason: string; requested_by_name: string | null; created_at: string } | null;
  created_at: string;
  completed_at: string | null;
}

interface UploadSession {
  media: StudioMedia;
  upload_url: string | null;
  session_expires_at: string | null;
  received_bytes: number | null;
  chunk_size_multiple: number;
}

/** Mirrors backend `media.models.MIME_TYPES`; the server re-checks the real type in Drive. */
export const ACCEPTED_TYPES: Record<string, MediaKind> = {
  "image/jpeg": "PHOTO",
  "image/png": "PHOTO",
  "image/webp": "PHOTO",
  "image/heic": "PHOTO",
  "image/heif": "PHOTO",
  "video/mp4": "VIDEO",
  "video/quicktime": "VIDEO",
  "video/x-m4v": "VIDEO",
  "video/webm": "VIDEO",
  "video/x-matroska": "VIDEO",
};
const BY_EXTENSION: Record<string, string> = {
  heic: "image/heic",
  heif: "image/heif",
  mkv: "video/x-matroska",
  m4v: "video/x-m4v",
  mov: "video/quicktime",
};
/** Browsers leave `File.type` empty for HEIC / MKV on some systems: fall back to the extension. */
export function mimeOf(file: File): string | null {
  const type = file.type || BY_EXTENSION[file.name.split(".").pop()?.toLowerCase() ?? ""] || "";
  return type in ACCEPTED_TYPES ? type : null;
}

const base = (ceremonyId: string) => `/ceremonies/${ceremonyId}/media/`;
const key = (ceremonyId: string) => ["studio", "ceremony", ceremonyId, "media"] as const;

export function useCeremonyMedia(ceremonyId: string) {
  return useQuery({
    queryKey: key(ceremonyId),
    queryFn: () => api.get<Paginated<StudioMedia>>(base(ceremonyId), { page_size: 100 }),
    enabled: Boolean(ceremonyId),
  });
}

export function useRefreshMedia(ceremonyId: string) {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: key(ceremonyId) });
}

export function useCancelUpload(ceremonyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mediaId: string) => api.post<UploadSession>(`${base(ceremonyId)}uploads/${mediaId}/cancel/`),
    onSettled: () => qc.invalidateQueries({ queryKey: key(ceremonyId) }),
  });
}

/** Unfinished uploads (never a usable file) are removed by the studio itself. */
export function useDismissUpload(ceremonyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mediaId: string) => api.delete(`${base(ceremonyId)}uploads/${mediaId}/`),
    onSettled: () => qc.invalidateQueries({ queryKey: key(ceremonyId) }),
  });
}

/** READY files are deleted only after an admin approves the request. */
export function useRequestDeletion(ceremonyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ mediaId, reason }: { mediaId: string; reason: string }) =>
      api.post(`${base(ceremonyId)}${mediaId}/delete-request/`, { reason }),
    onSettled: () => qc.invalidateQueries({ queryKey: key(ceremonyId) }),
  });
}

export function useWithdrawDeletion(ceremonyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mediaId: string) => api.post(`${base(ceremonyId)}${mediaId}/delete-request/cancel/`),
    onSettled: () => qc.invalidateQueries({ queryKey: key(ceremonyId) }),
  });
}

// ------------------------------------------------------------------ upload
/** 8 MiB: a multiple of Google's 256 KiB chunk rule, small enough to retry cheaply on mobile data. */
const CHUNK = 8 * 1024 * 1024;
const MAX_RETRIES = 4;

export class UploadAborted extends Error {}

interface ChunkResult {
  done: boolean;
  /** Bytes Google has stored so far. */
  received: number;
}

function putChunk(url: string, file: File, start: number, onBytes: (sent: number) => void, signal: AbortSignal): Promise<ChunkResult> {
  const end = Math.min(start + CHUNK, file.size);
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Range", `bytes ${start}-${end - 1}/${file.size}`);
    xhr.upload.onprogress = (e) => onBytes(start + e.loaded);
    xhr.onload = () => {
      if (xhr.status === 200 || xhr.status === 201) return resolve({ done: true, received: file.size });
      if (xhr.status === 308) return resolve({ done: false, received: rangeEnd(xhr.getResponseHeader("Range")) });
      reject(new Error(`drive_${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("network"));
    const abort = () => xhr.abort();
    signal.addEventListener("abort", abort, { once: true });
    xhr.onabort = () => reject(new UploadAborted());
    xhr.send(file.slice(start, end));
  });
}

/** Ask the session how far it got (after a dropped connection). */
function probe(url: string, size: number): Promise<ChunkResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Range", `bytes */${size}`);
    xhr.onload = () => {
      if (xhr.status === 200 || xhr.status === 201) return resolve({ done: true, received: size });
      if (xhr.status === 308) return resolve({ done: false, received: rangeEnd(xhr.getResponseHeader("Range")) });
      reject(new Error(`drive_${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("network"));
    xhr.send();
  });
}

const rangeEnd = (range: string | null) => {
  const last = range?.split("-")[1];
  return last ? Number(last) + 1 : 0;
};
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Full upload of one file: open a session on our server, PUT the bytes straight to Google in chunks
 * (resuming after network drops), then let the server verify the result in Drive.
 */
export async function uploadFile(
  ceremonyId: string,
  file: File,
  mime: string,
  onProgress: (sentBytes: number, mediaId?: string) => void,
  signal: AbortSignal,
): Promise<StudioMedia> {
  const session = await api.post<UploadSession>(`${base(ceremonyId)}uploads/`, {
    filename: file.name,
    mime_type: mime,
    size_bytes: file.size,
  });
  const url = session.upload_url;
  const mediaId = session.media.id;
  onProgress(0, mediaId);
  if (!url) throw new Error("no_session");

  const complete = () => api.post<UploadSession>(`${base(ceremonyId)}uploads/${mediaId}/complete/`);
  let offset = 0;
  let failures = 0;
  let sentAll = false;
  while (true) {
    if (signal.aborted) throw new UploadAborted();
    try {
      const res = await putChunk(url, file, offset, (sent) => {
        if (sent >= file.size) sentAll = true;
        onProgress(sent, mediaId);
      }, signal);
      failures = 0;
      if (res.done) break;
      offset = res.received;
    } catch (err) {
      if (err instanceof UploadAborted) throw err;
      // Every byte went out but Google's final response was unreadable (e.g. CORS for an origin the
      // session was not opened with): the server checks the session itself, so ask it to finish.
      if (sentAll) {
        const done = await complete().catch(() => null);
        if (done) return done.media;
      }
      if (++failures > MAX_RETRIES) throw err;
      await sleep(1000 * 2 ** failures);
      const state = await probe(url, file.size).catch(() => null);
      if (state?.done) break;
      if (state) offset = state.received;
    }
  }
  onProgress(file.size, mediaId);
  return (await complete()).media;
}
