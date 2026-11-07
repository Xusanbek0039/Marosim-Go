"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, setSessionExpiredHandler } from "./api";
import { APP } from "./app-config";
import type { Me } from "./types";

/** The account is valid but belongs to another MarosimGo app (e.g. an admin on the studio app). */
export class WrongAppError extends Error {
  constructor() {
    super(APP.wrongAppMessage);
    this.name = "WrongAppError";
  }
}

if (typeof window !== "undefined") {
  setSessionExpiredHandler(() => {
    if (!window.location.pathname.startsWith("/login")) {
      window.location.assign(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
    }
  });
}

const ME_KEY = ["auth", "me"] as const;

export function useMe() {
  return useQuery({ queryKey: ME_KEY, queryFn: () => api.get<Me>("/auth/me/"), staleTime: 60_000 });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { phone_number: string; password: string }) => {
      const { user } = await api.post<{ user: Me }>("/auth/login/", body, { noRefresh: true });
      if (user.role !== APP.role) {
        await api.post("/auth/logout/", undefined, { noRefresh: true }).catch(() => undefined);
        throw new WrongAppError();
      }
      return user;
    },
    onSuccess: (user) => qc.setQueryData(ME_KEY, user),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>("/auth/logout/", undefined, { noRefresh: true }),
    onSettled: () => qc.clear(),
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Pick<Me, "first_name" | "last_name" | "address">>) => api.patch<Me>("/auth/me/", body),
    onSuccess: (me) => qc.setQueryData(ME_KEY, me),
  });
}

/** Only same-app relative paths: never an absolute or protocol-relative URL (open redirect). */
export function safeNext(next: string | null): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\") || next.startsWith("/login")) {
    return APP.home;
  }
  return next;
}
