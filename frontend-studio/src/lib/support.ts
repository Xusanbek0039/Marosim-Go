"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";
import type { Paginated } from "./types";

export type TicketStatus = "OPEN" | "ANSWERED" | "CLOSED";

export interface TicketMessage {
  id: string;
  author_name: string;
  author_role: string;
  is_staff_reply: boolean;
  is_mine: boolean;
  body: string;
  created_at: string;
}

export interface Ticket {
  id: string;
  subject: string;
  status: TicketStatus;
  studio: { id: string; name: string } | null;
  venue: { id: string; name: string } | null;
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

export const TICKET_STATUS: Record<TicketStatus, { label: string; tone: "warning" | "success" | "neutral" }> = {
  OPEN: { label: "Javob kutilmoqda", tone: "warning" },
  ANSWERED: { label: "Javob keldi", tone: "success" },
  CLOSED: { label: "Yopilgan", tone: "neutral" },
};

const BASE = "/support/tickets/";
const keys = {
  all: ["support"] as const,
  list: ["support", "list"] as const,
  detail: (id: string) => ["support", "detail", id] as const,
};

export function useTickets() {
  return useQuery({ queryKey: keys.list, queryFn: () => api.get<Paginated<Ticket>>(BASE, { page_size: 50 }) });
}

export function useTicket(id: string | null) {
  return useQuery({
    queryKey: keys.detail(id ?? ""),
    queryFn: () => api.get<TicketDetail>(`${BASE}${id}/`),
    enabled: Boolean(id),
    refetchInterval: 30_000,
  });
}

function useSave() {
  const qc = useQueryClient();
  return (ticket: TicketDetail) => {
    qc.setQueryData(keys.detail(ticket.id), ticket);
    qc.invalidateQueries({ queryKey: keys.list });
  };
}

export function useCreateTicket() {
  const save = useSave();
  return useMutation({
    mutationFn: (body: { subject: string; body: string }) => api.post<TicketDetail>(BASE, body),
    onSuccess: save,
  });
}

export function useReply(id: string) {
  const save = useSave();
  return useMutation({
    mutationFn: (body: string) => api.post<TicketDetail>(`${BASE}${id}/messages/`, { body }),
    onSuccess: save,
  });
}

export function useCloseTicket(id: string) {
  const save = useSave();
  return useMutation({ mutationFn: () => api.post<TicketDetail>(`${BASE}${id}/close/`), onSuccess: save });
}
