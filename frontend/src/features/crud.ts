"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, toPayload } from "@/lib/api/client";
import type { ListParams, Paginated } from "@/lib/api/types";

/**
 * Typed CRUD hooks for one REST resource (`/users/`, `/admins/`, `/studios/`).
 * Every mutation invalidates the resource lists and the dashboard.
 */
export function createResource<T extends { id: string }>(resource: string) {
  const base = `/${resource}/`;
  const keys = {
    all: [resource] as const,
    list: (params: ListParams) => [resource, "list", params] as const,
    detail: (id: string) => [resource, "detail", id] as const,
  };

  function useInvalidate() {
    const qc = useQueryClient();
    return () => {
      qc.invalidateQueries({ queryKey: keys.all });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    };
  }

  return {
    keys,
    useList(params: ListParams, enabled = true) {
      return useQuery({
        queryKey: keys.list(params),
        queryFn: ({ signal }) => api.get<Paginated<T>>(base, params, signal),
        placeholderData: keepPreviousData,
        enabled,
      });
    },
    useDetail(id: string | null) {
      return useQuery({
        queryKey: keys.detail(id ?? ""),
        queryFn: ({ signal }) => api.get<T>(`${base}${id}/`, undefined, signal),
        enabled: Boolean(id),
      });
    },
    useCreate() {
      const invalidate = useInvalidate();
      return useMutation({
        mutationFn: (values: Record<string, unknown>) => api.post<T>(base, toPayload(values)),
        onSuccess: invalidate,
      });
    },
    useUpdate() {
      const invalidate = useInvalidate();
      const qc = useQueryClient();
      return useMutation({
        mutationFn: ({ id, values }: { id: string; values: Record<string, unknown> }) =>
          api.patch<T>(`${base}${id}/`, toPayload(values)),
        onSuccess: (data) => {
          qc.setQueryData(keys.detail(data.id), data);
          invalidate();
        },
      });
    },
    useDelete() {
      const invalidate = useInvalidate();
      return useMutation({
        mutationFn: (id: string) => api.delete(`${base}${id}/`),
        onSuccess: invalidate,
      });
    },
  };
}
