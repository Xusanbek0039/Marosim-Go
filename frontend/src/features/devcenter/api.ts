"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { ApiRole, ChangelogEntry, DevcenterOverview, EndpointCatalog, MobileGuide } from "@/lib/api/types";

/** Every list here comes from the backend's live OpenAPI schema — nothing is hardcoded in the UI. */
const STALE_MS = 60_000;

export function useDevcenterOverview() {
  return useQuery({
    queryKey: ["devcenter", "overview"],
    queryFn: ({ signal }) => api.get<DevcenterOverview>("/devcenter/overview/", undefined, signal),
    staleTime: STALE_MS,
  });
}

export function useDevcenterEndpoints(role?: ApiRole) {
  return useQuery({
    queryKey: ["devcenter", "endpoints", role ?? "ALL"],
    queryFn: ({ signal }) => api.get<EndpointCatalog>("/devcenter/endpoints/", role ? { role } : undefined, signal),
    staleTime: STALE_MS,
  });
}

export function useMobileGuide() {
  return useQuery({
    queryKey: ["devcenter", "mobile"],
    queryFn: ({ signal }) => api.get<MobileGuide>("/devcenter/mobile/", undefined, signal),
    staleTime: STALE_MS,
  });
}

export function useChangelog() {
  return useQuery({
    queryKey: ["devcenter", "changelog"],
    queryFn: ({ signal }) => api.get<{ count: number; results: ChangelogEntry[] }>("/devcenter/changelog/", undefined, signal),
    staleTime: STALE_MS,
  });
}
