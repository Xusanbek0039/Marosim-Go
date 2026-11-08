"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";

// -------------------------------------------------------------------- types
export type Region =
  | "TASHKENT_CITY"
  | "TASHKENT"
  | "ANDIJAN"
  | "BUKHARA"
  | "FERGANA"
  | "JIZZAKH"
  | "KHOREZM"
  | "NAMANGAN"
  | "NAVOI"
  | "KASHKADARYA"
  | "KARAKALPAKSTAN"
  | "SAMARKAND"
  | "SIRDARYO"
  | "SURKHANDARYA";

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

export type BookingStatus = "REQUESTED" | "CONFIRMED" | "BLOCKED" | "REJECTED" | "CANCELLED";

export interface PublicVenue {
  id: string;
  name: string;
  description: string;
  venue_type: string;
  address: string;
  region: Region;
  district: string;
  latitude: string | null;
  longitude: string | null;
  phone_number: string;
  cover_image: string | null;
  capacity_min: number;
  capacity_max: number;
  base_price: string;
  currency: "UZS";
  images: { id: string; image: string; position: number }[];
}

export interface SessionBrief {
  id: string;
  name: string;
  starts_at: string; // "18:00:00"
  ends_at: string;
}

export interface SearchSlot extends SessionBrief {
  is_free: boolean;
}

export interface SearchHall {
  id: string;
  name: string;
  capacity: number;
  price: string;
  slots: SearchSlot[];
}

export interface SearchResult {
  venue: PublicVenue;
  halls: SearchHall[];
  free_slots: number;
}

export interface PublicVenueDetail {
  venue: PublicVenue;
  halls: { id: string; name: string; capacity: number; price: string; sessions: SessionBrief[] }[];
}

export interface Availability {
  date_from: string;
  date_to: string;
  /** hall_id -> date -> free session ids */
  free: Record<string, Record<string, string[]>>;
}

export interface MyBooking {
  id: string;
  venue: { id: string; name: string; address: string; phone_number: string };
  hall: { id: string; name: string };
  session: SessionBrief;
  date: string;
  status: BookingStatus;
  event_type: BookingEventType;
  guest_count: number | null;
  contact_phone: string;
  note: string;
  quoted_price: string | null;
  currency: "UZS";
  decided_at: string | null;
  created_at: string;
}

// ------------------------------------------------------------------- labels
export const REGION_LABELS: Record<Region, string> = {
  TASHKENT_CITY: "Toshkent shahri",
  TASHKENT: "Toshkent viloyati",
  ANDIJAN: "Andijon viloyati",
  BUKHARA: "Buxoro viloyati",
  FERGANA: "Farg'ona viloyati",
  JIZZAKH: "Jizzax viloyati",
  KHOREZM: "Xorazm viloyati",
  NAMANGAN: "Namangan viloyati",
  NAVOI: "Navoiy viloyati",
  KASHKADARYA: "Qashqadaryo viloyati",
  KARAKALPAKSTAN: "Qoraqalpog'iston Respublikasi",
  SAMARKAND: "Samarqand viloyati",
  SIRDARYO: "Sirdaryo viloyati",
  SURKHANDARYA: "Surxondaryo viloyati",
};

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

type Tone = "neutral" | "brand" | "success" | "warning" | "danger";
export const BOOKING_STATUS: Record<BookingStatus, { label: string; tone: Tone; hint: string }> = {
  REQUESTED: { label: "Kutilmoqda", tone: "warning", hint: "To'yxona so'rovingizni ko'rib chiqmoqda." },
  CONFIRMED: { label: "Tasdiqlandi", tone: "success", hint: "Smena siz uchun band qilindi." },
  BLOCKED: { label: "Yopiq", tone: "neutral", hint: "" },
  REJECTED: { label: "Rad etildi", tone: "danger", hint: "Boshqa smena yoki to'yxona tanlang." },
  CANCELLED: { label: "Bekor qilindi", tone: "neutral", hint: "" },
};

/** "18:00:00" -> "18:00". */
export const hhmm = (t: string) => t.slice(0, 5);

const pad = (n: number) => String(n).padStart(2, "0");
/** Local calendar date as YYYY-MM-DD (the venue's calendar is Asia/Tashkent; so is the audience). */
export const isoDate = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const todayIso = () => isoDate(new Date());

// ------------------------------------------------------------------ queries
const keys = {
  search: (p: object) => ["venues", "search", p] as const,
  venue: (id: string) => ["venues", id] as const,
  availability: (id: string, from: string, to: string) => ["venues", id, "availability", from, to] as const,
  mine: ["me", "venue-bookings"] as const,
};

export interface SearchParams {
  date: string;
  region?: Region | "";
  guests?: number | "";
  q?: string;
}

export function useVenueSearch(params: SearchParams) {
  return useQuery({
    queryKey: keys.search(params),
    queryFn: ({ signal }) =>
      api.get<SearchResult[]>(
        "/venues/search/",
        { date: params.date, region: params.region, guests: params.guests, q: params.q },
        signal,
      ),
    enabled: Boolean(params.date),
    placeholderData: keepPreviousData,
  });
}

export function usePublicVenue(id: string) {
  return useQuery({ queryKey: keys.venue(id), queryFn: () => api.get<PublicVenueDetail>(`/venues/${id}/`), enabled: Boolean(id) });
}

export function useAvailability(id: string, from: string, to: string) {
  return useQuery({
    queryKey: keys.availability(id, from, to),
    queryFn: ({ signal }) => api.get<Availability>(`/venues/${id}/availability/`, { from, to }, signal),
    enabled: Boolean(id),
    placeholderData: keepPreviousData,
  });
}

export function useMyBookings() {
  return useQuery({ queryKey: keys.mine, queryFn: () => api.get<MyBooking[]>("/me/venue-bookings/") });
}

export interface BookingRequest {
  session: string;
  date: string;
  event_type: BookingEventType;
  guest_count?: number | null;
  contact_phone?: string;
  note?: string;
}

export function useRequestBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: BookingRequest) => api.post<MyBooking>("/me/venue-bookings/", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.mine }),
  });
}

export function useCancelBooking() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<MyBooking>(`/me/venue-bookings/${id}/cancel/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.mine });
      qc.invalidateQueries({ queryKey: ["venues"] });
    },
  });
}
