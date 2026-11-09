"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { AdminReview, StudioCalendarEntry, VenueBooking, VenueCalendar } from "@/lib/api/types";

import { createResource } from "../crud";
import { studiosResource } from "../resources";

const pad = (n: number) => String(n).padStart(2, "0");
/** Local calendar date as YYYY-MM-DD (schedules are Asia/Tashkent). */
export const isoDate = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const hhmm = (t: string) => t.slice(0, 5);
export const MONTHS = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"];
export const WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];

export const BOOKING_STATUS: Record<VenueBooking["status"], { label: string; className: string }> = {
  REQUESTED: { label: "So'rov", className: "bg-amber-500/16 text-amber-700 dark:text-amber-300" },
  CONFIRMED: { label: "Tasdiqlangan", className: "bg-emerald-500/16 text-emerald-700 dark:text-emerald-300" },
  BLOCKED: { label: "Yopiq", className: "bg-slate-500/16 text-slate-700 dark:text-slate-300" },
  REJECTED: { label: "Rad etilgan", className: "bg-red-500/14 text-red-700 dark:text-red-300" },
  CANCELLED: { label: "Bekor qilingan", className: "bg-slate-500/14 text-slate-600 dark:text-slate-400" },
};

// ----------------------------------------------------------- venue schedule
const venueKey = (id: string) => ["admin/venues", "schedule", id] as const;

export function useVenueCalendar(id: string, from: string, to: string) {
  return useQuery({
    queryKey: [...venueKey(id), "calendar", from, to],
    queryFn: ({ signal }) => api.get<VenueCalendar>(`/admin/venues/${id}/calendar/`, { from, to }, signal),
    placeholderData: keepPreviousData,
  });
}

/** Open requests of one venue, oldest date first — the queue an admin may need to unblock. */
export function useVenueRequests(id: string) {
  return useQuery({
    queryKey: [...venueKey(id), "requests"],
    queryFn: ({ signal }) => api.get<VenueBooking[]>(`/admin/venues/${id}/bookings/`, { status: "REQUESTED" }, signal),
  });
}

export function useBookingAction(venueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action, venue_note }: { id: string; action: "confirm" | "reject" | "cancel"; venue_note?: string }) =>
      api.post<VenueBooking>(`/admin/venues/${venueId}/bookings/${id}/${action}/`, venue_note ? { venue_note } : {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: venueKey(venueId) }),
  });
}

export function useCreateEntry(venueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { session: string; date: string; status: "CONFIRMED" | "BLOCKED"; contact_name?: string; venue_note?: string }) =>
      api.post<VenueBooking>(`/admin/venues/${venueId}/bookings/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: venueKey(venueId) }),
  });
}

// ---------------------------------------------------------- studio schedule
export function useStudioCalendar(id: string, from: string, to: string) {
  return useQuery({
    queryKey: ["studios", "calendar", id, from, to],
    queryFn: ({ signal }) => api.get<StudioCalendarEntry[]>(`/studios/${id}/calendar/`, { from, to }, signal),
    placeholderData: keepPreviousData,
  });
}

function useRefreshStudio() {
  const qc = useQueryClient();
  return (id: string) => {
    qc.invalidateQueries({ queryKey: studiosResource.keys.all });
    qc.invalidateQueries({ queryKey: studiosResource.keys.detail(id) });
  };
}

export function useUploadStudioImage(studioId: string) {
  const refresh = useRefreshStudio();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("image", file);
      return api.post(`/studios/${studioId}/images/`, form);
    },
    onSuccess: () => refresh(studioId),
  });
}

export function useDeleteStudioImage(studioId: string) {
  const refresh = useRefreshStudio();
  return useMutation({
    mutationFn: (imageId: string) => api.delete(`/studios/${studioId}/images/${imageId}/`),
    onSuccess: () => refresh(studioId),
  });
}

// ------------------------------------------------------------------ reviews
export const reviewsResource = createResource<AdminReview>("admin/reviews");
