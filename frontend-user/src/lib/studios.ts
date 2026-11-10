"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, apiRequest } from "./api";
import type { Stats } from "./reviews";

export interface PublicStudio {
  is_verified: boolean;
  id: string;
  name: string;
  description: string;
  profile_picture: string | null;
  address: string;
  phone_number: string;
  /** Photos only. */
  images: PortfolioItem[];
  /** Vertical videos — empty unless the studio's galichka is active. */
  reels: PortfolioItem[];
  /** Customers may write to the studio (galichka active). */
  chat_enabled: boolean;
  stats: Stats;
}

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

export interface PortfolioComment {
  id: string;
  author_name: string;
  text: string;
  created_at: string;
  is_mine: boolean;
}

export interface StudioSchedule {
  date_from: string;
  date_to: string;
  /** date -> ceremonies that day (free days are absent) */
  busy: Record<string, number>;
  /** days the studio marked by hand */
  days: Record<string, "BUSY" | "OFF">;
  /** weekly days off, 0 = Monday … 6 = Sunday */
  off_weekdays: number[];
}

export function usePublicStudios(q: string) {
  return useQuery({
    queryKey: ["studios", "catalog", q] as const,
    queryFn: ({ signal }) => api.get<PublicStudio[]>("/public/studios/", { q }, signal),
    placeholderData: keepPreviousData,
  });
}

export function usePublicStudio(id: string) {
  return useQuery({
    queryKey: ["studios", id] as const,
    queryFn: () => api.get<PublicStudio>(`/public/studios/${id}/`),
    enabled: Boolean(id),
  });
}

export function useStudioSchedule(id: string, from: string, to: string) {
  return useQuery({
    queryKey: ["studios", id, "schedule", from, to] as const,
    queryFn: ({ signal }) => api.get<StudioSchedule>(`/public/studios/${id}/schedule/`, { from, to }, signal),
    enabled: Boolean(id),
    placeholderData: keepPreviousData,
  });
}

export const studioCover = (s: Pick<PublicStudio, "images" | "profile_picture">) => s.images[0]?.image ?? s.profile_picture;

// ------------------------------------------------- reactions and comments
const itemBase = (studioId: string, itemId: string) => `/public/studios/${studioId}/portfolio/${itemId}`;

/** Writes fresh counts of one item into the cached studio profile. */
function usePatchEngagement(studioId: string) {
  const qc = useQueryClient();
  return (itemId: string, patch: Partial<Engagement>) =>
    qc.setQueryData<PublicStudio>(["studios", studioId], (s) => {
      if (!s) return s;
      const fix = (list: PortfolioItem[]) => list.map((i) => (i.id === itemId ? { ...i, engagement: { ...i.engagement, ...patch } } : i));
      return { ...s, images: fix(s.images), reels: fix(s.reels) };
    });
}

export function useReact(studioId: string) {
  const patch = usePatchEngagement(studioId);
  return useMutation({
    mutationFn: ({ itemId, value }: { itemId: string; value: "like" | "dislike" | null }) =>
      value
        ? api.put<Engagement>(`${itemBase(studioId, itemId)}/reaction/`, { value })
        : apiRequest<Engagement>(`${itemBase(studioId, itemId)}/reaction/`, { method: "DELETE" }),
    onSuccess: (engagement, { itemId }) => patch(itemId, engagement),
  });
}

const commentsKey = (studioId: string, itemId: string) => ["studios", studioId, "comments", itemId] as const;

export function useComments(studioId: string, itemId: string | null) {
  return useQuery({
    queryKey: commentsKey(studioId, itemId ?? ""),
    queryFn: () => api.get<PortfolioComment[]>(`${itemBase(studioId, itemId!)}/comments/`),
    enabled: Boolean(itemId),
  });
}

export function useAddComment(studioId: string, itemId: string) {
  const qc = useQueryClient();
  const patch = usePatchEngagement(studioId);
  return useMutation({
    mutationFn: (text: string) => api.post<PortfolioComment>(`${itemBase(studioId, itemId)}/comments/`, { text }),
    onSuccess: (comment) => {
      const list = qc.setQueryData<PortfolioComment[]>(commentsKey(studioId, itemId), (old) => [comment, ...(old ?? [])]);
      patch(itemId, { comment_count: list?.length ?? 1 });
    },
  });
}

export function useDeleteMyComment(studioId: string, itemId: string) {
  const qc = useQueryClient();
  const patch = usePatchEngagement(studioId);
  return useMutation({
    mutationFn: (commentId: string) => api.delete(`${itemBase(studioId, itemId)}/comments/${commentId}/`),
    onSuccess: (_, commentId) => {
      const list = qc.setQueryData<PortfolioComment[]>(commentsKey(studioId, itemId), (old) => (old ?? []).filter((c) => c.id !== commentId));
      patch(itemId, { comment_count: list?.length ?? 0 });
    },
  });
}

// --------------------------------------------------------------------- chat
export interface ChatMessage {
  id: string;
  body: string;
  from_studio: boolean;
  created_at: string;
}

export interface ChatStudio {
  is_verified: boolean;
  id: string;
  name: string;
  profile_picture: string | null;
}

export interface MyConversation {
  id: string;
  studio: ChatStudio;
  last_message_at: string;
  unread: number;
  last_message: ChatMessage | null;
}

export interface MyThread {
  studio: ChatStudio;
  can_write: boolean;
  messages: ChatMessage[];
}

const chatsKey = ["studio-chats"] as const;

export function useMyChats() {
  return useQuery({
    queryKey: chatsKey,
    queryFn: () => api.get<MyConversation[]>("/me/studio-chats/"),
    refetchInterval: 15_000,
  });
}

export function useMyThread(studioId: string | null) {
  const qc = useQueryClient();
  return useQuery({
    queryKey: [...chatsKey, studioId],
    queryFn: async () => {
      const thread = await api.get<MyThread>(`/me/studio-chats/${studioId}/`);
      qc.invalidateQueries({ queryKey: chatsKey, exact: true });
      return thread;
    },
    enabled: Boolean(studioId),
    refetchInterval: 5_000,
  });
}

export function useSendToStudio(studioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => api.post<ChatMessage>(`/me/studio-chats/${studioId}/`, { body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: chatsKey }),
  });
}
