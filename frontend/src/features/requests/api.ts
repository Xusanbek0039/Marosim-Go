"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

import { createResource } from "../crud";

export type DeletionStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";

export interface DeletionRequest {
  id: string;
  status: DeletionStatus;
  reason: string;
  media: {
    id: string;
    kind: "PHOTO" | "VIDEO";
    status: string;
    original_name: string;
    mime_type: string;
    size_bytes: number;
    uploaded_by_name: string | null;
    completed_at: string | null;
  };
  ceremony: { id: string; title: string; event_date: string | null };
  studio: { id: string; name: string };
  requested_by: { id: string; name: string | null; phone_number: string | null } | null;
  decided_by_name: string | null;
  decided_at: string | null;
  decision_note: string;
  created_at: string;
}

/** `/api/v1/admin/media-deletion-requests/` — `requests.view` to see, `requests.media_delete` to decide. */
export const deletionRequestsResource = createResource<DeletionRequest>("admin/media-deletion-requests");

export const STATUS: Record<DeletionStatus, { label: string; className: string }> = {
  PENDING: { label: "Kutilmoqda", className: "bg-amber-500/16 text-amber-700 dark:text-amber-300" },
  APPROVED: { label: "O'chirildi", className: "bg-emerald-500/16 text-emerald-700 dark:text-emerald-300" },
  REJECTED: { label: "Rad etilgan", className: "bg-red-500/14 text-red-700 dark:text-red-300" },
  CANCELLED: { label: "Studiya qaytarib oldi", className: "bg-slate-500/14 text-slate-700 dark:text-slate-300" },
};

const summaryKey = ["admin/media-deletion-requests", "summary"] as const;

export function useRequestsSummary(enabled = true) {
  return useQuery({
    queryKey: summaryKey,
    queryFn: () => api.get<{ pending: number }>("/admin/media-deletion-requests/summary/"),
    enabled,
    refetchInterval: 60_000,
  });
}

export function useDeletionDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action, note }: { id: string; action: "approve" | "reject"; note: string }) =>
      api.post<DeletionRequest>(`/admin/media-deletion-requests/${id}/${action}/`, { note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: deletionRequestsResource.keys.all });
      qc.invalidateQueries({ queryKey: summaryKey });
    },
  });
}
