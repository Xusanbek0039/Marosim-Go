"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { API_BASE, api } from "./api";
import type { AccessDuration, CeremonyMembers, MyMedia, SentInvitation } from "./types";

/** Free limit (no subscription); the real one comes from `members.viewer_limit`. */
export const MAX_VIEWERS = 5;

export const DURATIONS: { value: AccessDuration; label: string }[] = [
  { value: "24H", label: "24 soat" },
  { value: "3D", label: "3 kun" },
  { value: "1W", label: "1 hafta" },
  { value: "1M", label: "1 oy" },
];
export const DURATION_LABEL = Object.fromEntries(DURATIONS.map((d) => [d.value, d.label])) as Record<AccessDuration, string>;

// Same-origin URLs: the httpOnly session cookie authorizes <img> / <video> requests through the proxy.
const mediaBase = (ceremonyId: string) => `${API_BASE}/me/ceremonies/${ceremonyId}/media`;
export const thumbUrl = (ceremonyId: string, mediaId: string, size: 240 | 480 | 960 = 480) =>
  `${mediaBase(ceremonyId)}/${mediaId}/thumbnail/?size=${size}`;
export const streamUrl = (ceremonyId: string, mediaId: string) => `${mediaBase(ceremonyId)}/${mediaId}/stream/`;
export const downloadUrl = (ceremonyId: string, mediaId: string) => `${mediaBase(ceremonyId)}/${mediaId}/download/`;

const keys = {
  media: (id: string) => ["me", "ceremony", id, "media"] as const,
  members: (id: string) => ["me", "ceremony", id, "members"] as const,
  invitations: (id: string) => ["me", "ceremony", id, "sent-invitations"] as const,
};

export function useCeremonyMedia(ceremonyId: string) {
  return useQuery({
    queryKey: keys.media(ceremonyId),
    queryFn: () => api.get<MyMedia[]>(`/me/ceremonies/${ceremonyId}/media/`),
    // while a video's logo copy is being made, check back every 15 s
    refetchInterval: (q) => (q.state.data?.some((m) => m.processing) ? 15_000 : false),
  });
}

export function useMembers(ceremonyId: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.members(ceremonyId),
    queryFn: () => api.get<CeremonyMembers>(`/me/ceremonies/${ceremonyId}/members/`),
    enabled,
  });
}

export function useSentInvitations(ceremonyId: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.invitations(ceremonyId),
    queryFn: () => api.get<SentInvitation[]>(`/me/ceremonies/${ceremonyId}/invitations/`),
    enabled,
  });
}

function useInvalidate(ceremonyId: string) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: keys.members(ceremonyId) });
    qc.invalidateQueries({ queryKey: keys.invitations(ceremonyId) });
  };
}

export function useShare(ceremonyId: string) {
  const invalidate = useInvalidate(ceremonyId);
  return useMutation({
    mutationFn: (body: { identifier_type: "PHONE" | "PINFL"; identifier: string; access_duration: AccessDuration }) =>
      api.post<SentInvitation>(`/me/ceremonies/${ceremonyId}/invitations/`, { ...body, requested_role: "VIEWER" }),
    onSuccess: invalidate,
  });
}

export function useRevokeInvitation(ceremonyId: string) {
  const invalidate = useInvalidate(ceremonyId);
  return useMutation({
    mutationFn: (invitationId: string) => api.post<void>(`/me/ceremonies/${ceremonyId}/invitations/${invitationId}/revoke/`),
    onSuccess: invalidate,
  });
}

export function useRevokeViewer(ceremonyId: string) {
  const invalidate = useInvalidate(ceremonyId);
  return useMutation({
    mutationFn: (accessId: string) => api.post<void>(`/me/ceremonies/${ceremonyId}/viewers/${accessId}/revoke/`),
    onSuccess: invalidate,
  });
}

/** "2 kun 4 soat" / "5 soat" / "12 daqiqa" until `iso`. */
export function timeLeft(iso: string | null, now = Date.now()): string {
  if (!iso) return "Muddatsiz";
  const ms = new Date(iso).getTime() - now;
  if (ms <= 0) return "Muddati tugagan";
  const minutes = Math.floor(ms / 60_000);
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  if (days) return hours ? `${days} kun ${hours} soat` : `${days} kun`;
  if (hours) return `${hours} soat`;
  return `${Math.max(1, minutes)} daqiqa`;
}
