"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";

// -------------------------------------------------------------------- types
export type BookingStatus = "REQUESTED" | "CONFIRMED" | "BLOCKED" | "REJECTED" | "CANCELLED";
export type BookingEventType =
  | "WEDDING"
  | "NAHOR"
  | "ENGAGEMENT"
  | "SUNNAT"
  | "BESHIK"
  | "BIRTHDAY"
  | "ANNIVERSARY"
  | "CORPORATE"
  | "OTHER";

export interface HallSession {
  id: string;
  name: string;
  starts_at: string; // "18:00:00"
  ends_at: string;
  is_active: boolean;
}

export interface CalendarHall {
  id: string;
  name: string;
  capacity: number;
  is_active: boolean;
  sessions: HallSession[];
}

export interface Booking {
  id: string;
  hall: { id: string; name: string };
  session: { id: string; name: string; starts_at: string; ends_at: string };
  date: string;
  status: BookingStatus;
  source: "USER" | "VENUE";
  event_type: BookingEventType;
  guest_count: number | null;
  requester: { id: string; full_name: string; phone_number: string } | null;
  contact_name: string;
  contact_phone: string;
  note: string;
  venue_note: string;
  quoted_price: string | null;
  currency: "UZS";
  decided_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface VenueCalendar {
  date_from: string;
  date_to: string;
  halls: CalendarHall[];
  bookings: Booking[];
}

// ------------------------------------------------------------------- labels
export const EVENT_TYPE_LABELS: Record<BookingEventType, string> = {
  WEDDING: "Nikoh to'yi",
  NAHOR: "Nahorgi osh",
  ENGAGEMENT: "Fotiha / unashtiruv",
  SUNNAT: "Sunnat to'yi",
  BESHIK: "Beshik to'yi",
  BIRTHDAY: "Tug'ilgan kun",
  ANNIVERSARY: "Yubiley",
  CORPORATE: "Korporativ",
  OTHER: "Boshqa",
};

/** Short form for calendar cells. */
export const EVENT_SHORT: Record<BookingEventType, string> = {
  WEDDING: "To'y",
  NAHOR: "Osh",
  ENGAGEMENT: "Fotiha",
  SUNNAT: "Sunnat",
  BESHIK: "Beshik",
  BIRTHDAY: "Tug'ilgan kun",
  ANNIVERSARY: "Yubiley",
  CORPORATE: "Korporativ",
  OTHER: "Marosim",
};

/** One palette for cells, pills and the legend. */
export const SLOT_TONE = {
  FREE: { label: "Bo'sh", className: "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300", dot: "bg-emerald-500" },
  REQUESTED: { label: "So'rov", className: "bg-amber-500/18 text-amber-800 dark:text-amber-300", dot: "bg-amber-500" },
  CONFIRMED: { label: "Band", className: "bg-blue-600/18 text-blue-800 dark:text-blue-300", dot: "bg-blue-600" },
  BLOCKED: { label: "Yopiq", className: "bg-slate-500/20 text-slate-700 dark:text-slate-300", dot: "bg-slate-500" },
} as const;

export const hhmm = (t: string) => t.slice(0, 5);
const pad = (n: number) => String(n).padStart(2, "0");
export const isoDate = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

// ------------------------------------------------------------------ queries
const keys = {
  calendar: (venueId: string) => ["venues", venueId, "calendar"] as const,
  pending: (venueId: string) => ["venues", venueId, "pending"] as const,
};

export function useCalendar(venueId: string, from: string, to: string) {
  return useQuery({
    queryKey: [...keys.calendar(venueId), from, to],
    queryFn: ({ signal }) => api.get<VenueCalendar>(`/venue-owner/venues/${venueId}/calendar/`, { from, to }, signal),
    placeholderData: keepPreviousData,
  });
}

export function usePendingRequests(venueId: string) {
  return useQuery({
    queryKey: keys.pending(venueId),
    queryFn: () =>
      api.get<Booking[]>(`/venue-owner/venues/${venueId}/bookings/`, { status: "REQUESTED", from: isoDate(new Date()) }),
    refetchInterval: 60_000,
  });
}

function useInvalidate(venueId: string) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: keys.calendar(venueId) });
    qc.invalidateQueries({ queryKey: keys.pending(venueId) });
  };
}

export interface EntryWrite {
  session: string;
  date: string;
  status: "CONFIRMED" | "BLOCKED";
  event_type?: BookingEventType;
  guest_count?: number | null;
  contact_name?: string;
  contact_phone?: string;
  venue_note?: string;
}

export function useCreateEntry(venueId: string) {
  const invalidate = useInvalidate(venueId);
  return useMutation({
    mutationFn: (body: EntryWrite) => api.post<Booking>(`/venue-owner/venues/${venueId}/bookings/`, body),
    onSuccess: invalidate,
  });
}

export function useUpdateEntry(venueId: string) {
  const invalidate = useInvalidate(venueId);
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<Omit<EntryWrite, "session" | "date" | "status">> & { id: string }) =>
      api.patch<Booking>(`/venue-owner/venues/${venueId}/bookings/${id}/`, body),
    onSuccess: invalidate,
  });
}

export function useDecide(venueId: string) {
  const invalidate = useInvalidate(venueId);
  return useMutation({
    mutationFn: ({ id, action, venue_note }: { id: string; action: "confirm" | "reject" | "cancel"; venue_note?: string }) =>
      api.post<Booking>(`/venue-owner/venues/${venueId}/bookings/${id}/${action}/`, { venue_note }),
    onSuccess: invalidate,
  });
}

type SessionWrite = Partial<Pick<HallSession, "name" | "starts_at" | "ends_at" | "is_active">>;

export function useCreateSession(venueId: string) {
  const invalidate = useInvalidate(venueId);
  return useMutation({
    mutationFn: ({ hallId, ...body }: SessionWrite & { hallId: string }) =>
      api.post<HallSession>(`/venue-owner/venues/${venueId}/halls/${hallId}/sessions/`, body),
    onSuccess: invalidate,
  });
}

export function useUpdateSession(venueId: string) {
  const invalidate = useInvalidate(venueId);
  return useMutation({
    mutationFn: ({ hallId, id, ...body }: SessionWrite & { hallId: string; id: string }) =>
      api.patch<HallSession>(`/venue-owner/venues/${venueId}/halls/${hallId}/sessions/${id}/`, body),
    onSuccess: invalidate,
  });
}
