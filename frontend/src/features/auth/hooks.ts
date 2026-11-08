"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { Me, PermissionCode } from "@/lib/api/types";

export const meKey = ["auth", "me"] as const;

export function useMe() {
  return useQuery({
    queryKey: meKey,
    queryFn: ({ signal }) => api.get<Me>("/auth/me/", undefined, signal),
    staleTime: 60_000,
    retry: false,
  });
}

export function useCan() {
  const { data } = useMe();
  return (code: PermissionCode) => Boolean(data?.permissions.includes(code));
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { phone_number: string; password: string }) =>
      api.post<{ user: Me }>("/auth/login/", body, { noRefresh: true }),
    onSuccess: ({ user }) => {
      qc.clear();
      qc.setQueryData(meKey, user);
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>("/auth/logout/", undefined, { noRefresh: true }),
    onSettled: () => qc.clear(),
  });
}

/**
 * Which roles this build of the panel admits (NEXT_PUBLIC_PANEL_AUDIENCE, fixed at build time):
 * - "super_admin" — superadmin.marosimgo.uz (served by Django together with the API)
 * - "admin"       — admin.marosimgo.uz
 * - unset         — both (local development)
 * Django still authorizes every API call; this only keeps each panel on its own domain.
 */
const AUDIENCE = process.env.NEXT_PUBLIC_PANEL_AUDIENCE;

export const isPanelRole = (role?: string) =>
  AUDIENCE === "super_admin" ? role === "SUPER_ADMIN" : AUDIENCE === "admin" ? role === "ADMIN" : role === "SUPER_ADMIN" || role === "ADMIN";

export const panelAudienceMessage =
  AUDIENCE === "super_admin"
    ? "Bu panel faqat Super Admin uchun. Adminlar admin.marosimgo.uz orqali kiradi."
    : AUDIENCE === "admin"
      ? "Bu panel faqat adminlar uchun. Super Admin superadmin.marosimgo.uz orqali kiradi."
      : "Bu panel faqat administratorlar uchun.";
