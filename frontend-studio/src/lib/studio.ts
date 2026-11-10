"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";
import type { Ceremony, CeremonyStatus, MyStudioMembership, Paginated, Participant, ParticipantType } from "./types";

/** Mirrors backend `ceremonies.models.STUDIO_TRANSITIONS` (the server re-checks every change). */
export const STUDIO_TRANSITIONS: Record<CeremonyStatus, CeremonyStatus[]> = {
  DRAFT: ["READY", "ARCHIVED"],
  READY: ["DRAFT", "ARCHIVED"],
  ARCHIVED: ["DRAFT", "READY"],
  UPLOADING: [],
  PROCESSING: [],
};

const keys = {
  studios: ["studio", "me"] as const,
  ceremonies: ["studio", "ceremonies"] as const,
  ceremony: (id: string) => ["studio", "ceremony", id] as const,
  participants: (id: string) => ["studio", "ceremony", id, "participants"] as const,
};

export function useMyStudios() {
  return useQuery({ queryKey: keys.studios, queryFn: () => api.get<MyStudioMembership[]>("/studios/me/") });
}

export function useStudioCeremonies(filters: { status?: CeremonyStatus; search?: string }) {
  return useQuery({
    queryKey: [...keys.ceremonies, filters],
    queryFn: ({ signal }) => api.get<Paginated<Ceremony>>("/studios/me/ceremonies/", { ...filters, page_size: 50 }, signal),
    placeholderData: keepPreviousData,
  });
}

export function useCreateCeremony() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; event_date: string; description: string; studio_id?: string }) =>
      api.post<Ceremony>("/ceremonies/", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.ceremonies });
      qc.invalidateQueries({ queryKey: keys.studios });
    },
  });
}

export function useCeremony(id: string) {
  return useQuery({ queryKey: keys.ceremony(id), queryFn: () => api.get<Ceremony>(`/ceremonies/${id}/`), enabled: Boolean(id) });
}

export function useUpdateCeremony(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Pick<Ceremony, "title" | "event_date" | "description" | "status">>) =>
      api.patch<Ceremony>(`/ceremonies/${id}/`, body),
    onSuccess: (c) => {
      qc.setQueryData(keys.ceremony(id), c);
      qc.invalidateQueries({ queryKey: keys.ceremonies });
    },
  });
}

export function useParticipants(id: string) {
  return useQuery({
    queryKey: keys.participants(id),
    queryFn: () => api.get<Participant[]>(`/ceremonies/${id}/participants/`),
    enabled: Boolean(id),
  });
}

export function useInvite(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { phone_number: string; participant_type: ParticipantType }) =>
      api.post<Participant>(`/ceremonies/${id}/participants/`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.participants(id) });
      qc.invalidateQueries({ queryKey: keys.ceremony(id) });
    },
  });
}

export function useRevoke(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (participantId: string) => api.delete(`/ceremonies/${id}/participants/${participantId}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.participants(id) });
      qc.invalidateQueries({ queryKey: keys.ceremony(id) });
    },
  });
}

// ---------------------------------------------------------------- portfolio
export interface Engagement {
  like_count: number;
  dislike_count: number;
  comment_count: number;
  my_reaction: "like" | "dislike" | null;
}

export interface PortfolioItem {
  id: string;
  kind: "IMAGE" | "VIDEO";
  /** Photo, or the poster frame of a reel. */
  image: string;
  video: string | null;
  caption: string;
  duration: number;
  position: number;
  created_at: string;
  engagement: Engagement;
}
/** @deprecated kept for older imports */
export type PortfolioImage = PortfolioItem;

export interface PortfolioComment {
  id: string;
  author_name: string;
  text: string;
  created_at: string;
}

export const MAX_PORTFOLIO_IMAGES = 20;
export const MAX_PORTFOLIO_REELS = 15;
/** Mirrors backend `studios.reels`. */
export const REEL_LIMITS = { maxBytes: 100 * 1024 * 1024, minSeconds: 1, maxSeconds: 90, minRatio: 1.5 };

const portfolioKey = (studioId: string) => ["studio", "portfolio", studioId] as const;

/** The studio's public portfolio (shown to customers on its profile). */
export function usePortfolio(studioId: string) {
  return useQuery({
    queryKey: portfolioKey(studioId),
    queryFn: () => api.get<PortfolioItem[]>(`/studios/me/${studioId}/images/`),
  });
}

export function useUploadPortfolio(studioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("image", file);
      return api.post<PortfolioItem>(`/studios/me/${studioId}/images/`, form);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: portfolioKey(studioId) }),
  });
}

export function useUploadReel(studioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ video, poster, caption }: { video: File; poster: Blob | null; caption: string }) => {
      const form = new FormData();
      form.append("video", video);
      if (poster) form.append("poster", poster, "poster.jpg");
      form.append("caption", caption);
      return api.post<PortfolioItem>(`/studios/me/${studioId}/reels/`, form);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: portfolioKey(studioId) }),
  });
}

export function useUpdateCaption(studioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, caption }: { id: string; caption: string }) =>
      api.patch<PortfolioItem>(`/studios/me/${studioId}/images/${id}/`, { caption }),
    onSuccess: () => qc.invalidateQueries({ queryKey: portfolioKey(studioId) }),
  });
}

export function useDeletePortfolio(studioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (imageId: string) => api.delete(`/studios/me/${studioId}/images/${imageId}/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: portfolioKey(studioId) }),
  });
}

const commentsKey = (studioId: string, itemId: string) => ["studio", "portfolio", studioId, itemId, "comments"] as const;

export function useItemComments(studioId: string, itemId: string | null) {
  return useQuery({
    queryKey: commentsKey(studioId, itemId ?? ""),
    queryFn: () => api.get<PortfolioComment[]>(`/studios/me/${studioId}/images/${itemId}/comments/`),
    enabled: Boolean(itemId),
  });
}

export function useDeleteComment(studioId: string, itemId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (commentId: string) => api.delete(`/studios/me/${studioId}/images/${itemId}/comments/${commentId}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: commentsKey(studioId, itemId) });
      qc.invalidateQueries({ queryKey: portfolioKey(studioId) });
    },
  });
}

// ----------------------------------------------------------------- schedule
export type DayStatus = "BUSY" | "OFF";

export interface StudioSchedule {
  date_from: string;
  date_to: string;
  /** date -> ceremonies that day */
  busy: Record<string, number>;
  /** days marked by hand */
  days: Record<string, DayStatus>;
  /** 0 = Monday … 6 = Sunday */
  off_weekdays: number[];
  notes: Record<string, string>;
}

const scheduleKey = (studioId: string) => ["studio", "schedule", studioId] as const;

export function useStudioSchedule(studioId: string, from: string, to: string) {
  return useQuery({
    queryKey: [...scheduleKey(studioId), from, to],
    queryFn: ({ signal }) => api.get<StudioSchedule>(`/studios/me/${studioId}/schedule/`, { from, to }, signal),
    enabled: Boolean(studioId),
    placeholderData: keepPreviousData,
  });
}

export function useSetDay(studioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ date, status, note }: { date: string; status: DayStatus | null; note?: string }) =>
      api.put(`/studios/me/${studioId}/schedule/days/${date}/`, { status, note: note ?? "" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: scheduleKey(studioId) }),
  });
}

export function useSetOffWeekdays(studioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (off_weekdays: number[]) => api.patch(`/studios/me/${studioId}/schedule/`, { off_weekdays }),
    onSuccess: () => qc.invalidateQueries({ queryKey: scheduleKey(studioId) }),
  });
}

// --------------------------------------------------------------------- chat
export interface ChatMessage {
  id: string;
  body: string;
  from_studio: boolean;
  created_at: string;
}

export interface StudioConversation {
  id: string;
  customer: { id: string; name: string };
  last_message_at: string;
  unread: number;
  last_message: ChatMessage | null;
}

export interface StudioThread {
  id: string;
  customer: { id: string; name: string };
  can_write: boolean;
  messages: ChatMessage[];
}

const chatsKey = (studioId: string) => ["studio", "chats", studioId] as const;

export function useStudioChats(studioId: string, enabled = true) {
  return useQuery({
    queryKey: chatsKey(studioId),
    queryFn: () => api.get<StudioConversation[]>(`/studios/me/${studioId}/chats/`),
    enabled: Boolean(studioId) && enabled,
    refetchInterval: 15_000,
  });
}

export function useStudioThread(studioId: string, conversationId: string | null) {
  const qc = useQueryClient();
  return useQuery({
    queryKey: [...chatsKey(studioId), conversationId],
    queryFn: async () => {
      const thread = await api.get<StudioThread>(`/studios/me/${studioId}/chats/${conversationId}/`);
      qc.invalidateQueries({ queryKey: chatsKey(studioId), exact: true });
      return thread;
    },
    enabled: Boolean(conversationId),
    refetchInterval: 5_000,
  });
}

export function useSendStudioMessage(studioId: string, conversationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => api.post<ChatMessage>(`/studios/me/${studioId}/chats/${conversationId}/`, { body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: chatsKey(studioId) }),
  });
}
