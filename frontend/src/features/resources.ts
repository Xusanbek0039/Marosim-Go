"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { Admin, DashboardOverview, ManagedUser, PermissionDef, Studio } from "@/lib/api/types";

import { createResource } from "./crud";

export const usersResource = createResource<ManagedUser>("users");
export const adminsResource = createResource<Admin>("admins");
export const studiosResource = createResource<Studio>("studios");

export function useDashboardOverview() {
  return useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: ({ signal }) => api.get<DashboardOverview>("/dashboard/overview/", undefined, signal),
  });
}

export function usePermissionCatalog(enabled = true) {
  return useQuery({
    queryKey: ["admins", "permission-catalog"],
    queryFn: ({ signal }) => api.get<PermissionDef[]>("/admins/permissions/", undefined, signal),
    staleTime: Infinity,
    enabled,
  });
}

/** Full PINFL — never cached; the backend audits every call. */
export function useRevealPinfl(resource: "users" | "admins") {
  return useMutation({
    mutationFn: (id: string) => api.get<{ pinfl: string }>(`/${resource}/${id}/pinfl/`),
  });
}
