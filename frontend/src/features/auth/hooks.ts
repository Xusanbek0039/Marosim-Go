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
    mutationFn: (body: { email: string; password: string }) =>
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

export const isPanelRole = (role?: string) => role === "SUPER_ADMIN" || role === "ADMIN";
