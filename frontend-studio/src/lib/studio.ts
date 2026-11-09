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
export interface PortfolioImage {
  id: string;
  image: string;
  position: number;
  created_at: string;
}

export const MAX_PORTFOLIO_IMAGES = 20;
const portfolioKey = (studioId: string) => ["studio", "portfolio", studioId] as const;

/** The studio's public portfolio (shown to customers on its profile). */
export function usePortfolio(studioId: string) {
  return useQuery({
    queryKey: portfolioKey(studioId),
    queryFn: () => api.get<PortfolioImage[]>(`/studios/me/${studioId}/images/`),
  });
}

export function useUploadPortfolio(studioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("image", file);
      return api.post<PortfolioImage>(`/studios/me/${studioId}/images/`, form);
    },
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
