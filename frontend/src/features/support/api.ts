"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { Role } from "@/lib/api/types";

import { createResource } from "../crud";

export type TicketStatus = "OPEN" | "ANSWERED" | "CLOSED";
export type TicketAudience = "STAFF" | "SUPER_ADMIN";

export interface TicketMessage {
  id: string;
  author_name: string;
  author_role: Role;
  is_staff_reply: boolean;
  is_mine: boolean;
  body: string;
  created_at: string;
}

export interface Ticket {
  id: string;
  subject: string;
  status: TicketStatus;
  audience: TicketAudience;
  author: { id: string; name: string | null; phone_number: string | null; role: Role };
  author_role: Role;
  studio: { id: string; name: string } | null;
  venue: { id: string; name: string } | null;
  handled_by_name: string | null;
  closed_by_name: string | null;
  message_count: number;
  last_message: string;
  last_message_at: string;
  closed_at: string | null;
  created_at: string;
}

export interface TicketDetail extends Ticket {
  messages: TicketMessage[];
  can_reply: boolean;
}

export interface SupportSummary {
  open: number;
  answered: number;
  closed: number;
}

export const STATUS: Record<TicketStatus, { label: string; className: string }> = {
  OPEN: { label: "Javob kutilmoqda", className: "bg-amber-500/16 text-amber-700 dark:text-amber-300" },
  ANSWERED: { label: "Javob berildi", className: "bg-emerald-500/16 text-emerald-700 dark:text-emerald-300" },
  CLOSED: { label: "Yopilgan", className: "bg-slate-500/14 text-slate-700 dark:text-slate-300" },
};

export const AUTHOR_ROLES: Partial<Record<Role, string>> = {
  USER: "Foydalanuvchi",
  STUDIO: "Studiya",
  VENUE_OWNER: "To'yxona",
  ADMIN: "Admin",
};

/** Staff queue `/admin/support/tickets/` — `support.view` (+ `support.monitor` for the admins' tickets). */
export const staffTickets = createResource<Ticket>("admin/support/tickets");
/** The signed-in admin's own tickets to the Super Admin. */
export const myTickets = createResource<Ticket>("support/tickets");

const summaryKeys = {
  staff: ["admin/support/tickets", "summary"] as const,
  mine: ["support/tickets", "summary"] as const,
};

export function useStaffSummary(enabled = true) {
  return useQuery({
    queryKey: summaryKeys.staff,
    queryFn: () => api.get<SupportSummary>("/admin/support/tickets/summary/"),
    enabled,
    refetchInterval: 60_000,
  });
}

export function useMySummary(enabled = true) {
  return useQuery({
    queryKey: summaryKeys.mine,
    queryFn: () => api.get<SupportSummary>("/support/tickets/summary/"),
    enabled,
    refetchInterval: 60_000,
  });
}

/** One thread, from either side: `staff` uses the queue endpoints, otherwise the author's own. */
export function useThread(id: string | null, staff: boolean) {
  const base = staff ? "/admin/support/tickets/" : "/support/tickets/";
  const qc = useQueryClient();
  const key = [staff ? "admin/support/tickets" : "support/tickets", "detail", id ?? ""] as const;
  const save = (t: TicketDetail) => {
    qc.setQueryData(key, t);
    qc.invalidateQueries({ queryKey: [staff ? "admin/support/tickets" : "support/tickets"] });
  };
  const query = useQuery({
    queryKey: key,
    queryFn: () => api.get<TicketDetail>(`${base}${id}/`),
    enabled: Boolean(id),
    refetchInterval: 30_000,
  });
  const reply = useMutation({
    mutationFn: (body: string) => api.post<TicketDetail>(`${base}${id}/messages/`, { body }),
    onSuccess: save,
  });
  const close = useMutation({ mutationFn: () => api.post<TicketDetail>(`${base}${id}/close/`), onSuccess: save });
  return { query, reply, close };
}

export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { subject: string; body: string }) => api.post<TicketDetail>("/support/tickets/", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["support/tickets"] }),
  });
}


// ------------------------------------------------------------ partner applications (landing page)
export type ApplicationKind = "STUDIO" | "VENUE";
export type ApplicationStatus = "NEW" | "IN_REVIEW" | "APPROVED" | "REJECTED";

export interface PartnerApplication {
  id: string;
  kind: ApplicationKind;
  status: ApplicationStatus;
  full_name: string;
  phone_number: string;
  business_name: string;
  region: string;
  region_label: string;
  message: string;
  staff_note: string;
  handled_by_name: string | null;
  handled_at: string | null;
  created_at: string;
}

export const APPLICATION_KIND: Record<ApplicationKind, string> = { STUDIO: "Video studiya", VENUE: "To'yxona" };
export const APPLICATION_STATUS: Record<ApplicationStatus, { label: string; className: string }> = {
  NEW: { label: "Yangi", className: "bg-amber-500/16 text-amber-700 dark:text-amber-300" },
  IN_REVIEW: { label: "Ko'rib chiqilmoqda", className: "bg-blue-500/14 text-blue-700 dark:text-blue-300" },
  APPROVED: { label: "Qabul qilindi", className: "bg-emerald-500/16 text-emerald-700 dark:text-emerald-300" },
  REJECTED: { label: "Rad etildi", className: "bg-red-500/14 text-red-700 dark:text-red-300" },
};

/** `/admin/support/applications/` — staff with `support.view`. */
export const applicationsResource = createResource<PartnerApplication>("admin/support/applications");

export function useApplicationsSummary(enabled = true) {
  return useQuery({
    queryKey: ["admin/support/applications", "summary"] as const,
    queryFn: () => api.get<{ new: number; in_review: number }>("/admin/support/applications/summary/"),
    enabled,
    refetchInterval: 60_000,
  });
}
