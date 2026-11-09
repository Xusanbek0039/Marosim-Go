"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "./api";
import type { Stats } from "./reviews";

export interface PublicStudio {
  is_verified: boolean;
  id: string;
  name: string;
  description: string;
  profile_picture: string | null;
  address: string;
  phone_number: string;
  images: { id: string; image: string; position: number }[];
  stats: Stats;
}

export interface StudioSchedule {
  date_from: string;
  date_to: string;
  /** date -> ceremonies that day (free days are absent) */
  busy: Record<string, number>;
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
