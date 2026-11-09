"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, apiRequest } from "./api";

export type ReviewKind = "venue" | "studio";

export interface Stats {
  rating_avg: number | null;
  rating_count: number;
  like_count: number;
}

export interface PublicReview {
  id: string;
  author_name: string;
  rating: number;
  text: string;
  created_at: string;
  updated_at: string;
}

export interface ReviewPage {
  summary: Stats & { liked: boolean; my_review: PublicReview | null };
  results: PublicReview[];
}

/** API base of one business: venues live under /venues/, studios under /public/studios/. */
const base = (kind: ReviewKind, id: string) => (kind === "venue" ? `/venues/${id}` : `/public/studios/${id}`);
const key = (kind: ReviewKind, id: string) => ["reviews", kind, id] as const;

export function useReviews(kind: ReviewKind, id: string) {
  return useQuery({
    queryKey: key(kind, id),
    queryFn: () => api.get<ReviewPage>(`${base(kind, id)}/reviews/`),
    enabled: Boolean(id),
  });
}

function useRefresh(kind: ReviewKind, id: string) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: key(kind, id) });
    // cards on catalog pages show the same numbers
    qc.invalidateQueries({ queryKey: [kind === "venue" ? "venues" : "studios"] });
  };
}

export function useSaveReview(kind: ReviewKind, id: string) {
  const refresh = useRefresh(kind, id);
  return useMutation({
    mutationFn: (body: { rating: number; text: string }) => api.put<PublicReview>(`${base(kind, id)}/reviews/mine/`, body),
    onSuccess: refresh,
  });
}

export function useDeleteReview(kind: ReviewKind, id: string) {
  const refresh = useRefresh(kind, id);
  return useMutation({ mutationFn: () => api.delete(`${base(kind, id)}/reviews/mine/`), onSuccess: refresh });
}

export function useToggleLike(kind: ReviewKind, id: string) {
  const refresh = useRefresh(kind, id);
  return useMutation({
    mutationFn: (liked: boolean) =>
      apiRequest<{ liked: boolean; like_count: number }>(`${base(kind, id)}/like/`, { method: liked ? "POST" : "DELETE" }),
    onSuccess: refresh,
  });
}
