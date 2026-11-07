"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";
import type { Invitation, MyCeremony, Paginated } from "./types";

const keys = {
  ceremonies: ["me", "ceremonies"] as const,
  ceremony: (id: string) => ["me", "ceremony", id] as const,
  invitations: ["me", "invitations"] as const,
};

export function useMyCeremonies() {
  return useQuery({ queryKey: keys.ceremonies, queryFn: () => api.get<Paginated<MyCeremony>>("/me/ceremonies/", { page_size: 50 }) });
}

export function useMyCeremony(id: string) {
  return useQuery({ queryKey: keys.ceremony(id), queryFn: () => api.get<MyCeremony>(`/me/ceremonies/${id}/`), enabled: Boolean(id) });
}

export function useInvitations() {
  return useQuery({ queryKey: keys.invitations, queryFn: () => api.get<Invitation[]>("/me/invitations/") });
}

export function useRespond() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, answer }: { id: string; answer: "accept" | "decline" }) => api.post<unknown>(`/me/invitations/${id}/${answer}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.invitations });
      qc.invalidateQueries({ queryKey: keys.ceremonies });
    },
  });
}
