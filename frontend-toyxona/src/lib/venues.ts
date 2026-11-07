"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";
import type { Capability, MembershipRole, Paginated, PublicationStatus, Region, Venue, VenueHall, VenueImage, VenueMember, VenueType } from "./types";

// ------------------------------------------------------------------ labels
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

export const VENUE_TYPE_LABELS: Record<VenueType, string> = {
  BANQUET_HALL: "To'yxona",
  RESTAURANT: "Restoran",
  CAFE: "Kafe",
  OUTDOOR: "Ochiq maydon",
  OTHER: "Boshqa",
};

type Tone = "neutral" | "brand" | "success" | "warning" | "danger";
export const PUBLICATION: Record<PublicationStatus, { label: string; tone: Tone; hint: string }> = {
  PRIVATE: { label: "Yopiq", tone: "neutral", hint: "Faqat sizning jamoangizga ko'rinadi." },
  PENDING_APPROVAL: { label: "Tasdiq kutilmoqda", tone: "warning", hint: "Administrator ko'rib chiqmoqda." },
  APPROVED: { label: "Ommaga ochiq", tone: "success", hint: "Mijozlar qidiruvda ko'radi." },
  REJECTED: { label: "Rad etilgan", tone: "danger", hint: "Tuzatib, qayta yuboring." },
  SUSPENDED: { label: "To'xtatilgan", tone: "danger", hint: "Administrator vaqtincha yopgan." },
};

export const MEMBER_ROLES: Record<MembershipRole, { label: string; hint: string }> = {
  OWNER: { label: "Egasi", hint: "Hamma narsa, jamoa va ommaga chiqarish" },
  MANAGER: { label: "Menejer", hint: "Profil, zallar, jadval, narx va bronlar" },
  SCHEDULER: { label: "Jadval yurituvchi", hint: "Faqat bandlik jadvali" },
  VIEWER: { label: "Kuzatuvchi", hint: "Faqat ko'rish" },
};

export const can = (venue: Pick<Venue, "membership_capabilities"> | undefined, cap: Capability) =>
  Boolean(venue?.membership_capabilities.includes(cap));

// ------------------------------------------------------------------ queries
const keys = {
  venues: ["venues"] as const,
  venue: (id: string) => ["venues", id] as const,
  members: (id: string) => ["venues", id, "members"] as const,
};

export type VenueWrite = Partial<
  Pick<
    Venue,
    | "name"
    | "description"
    | "venue_type"
    | "address"
    | "region"
    | "district"
    | "phone_number"
    | "capacity_min"
    | "capacity_max"
    | "base_price"
    | "latitude"
    | "longitude"
  >
>;

export function useMyVenues(search?: string) {
  return useQuery({
    queryKey: [...keys.venues, { search }],
    queryFn: ({ signal }) => api.get<Paginated<Venue>>("/venue-owner/venues/", { search, page_size: 50 }, signal),
    placeholderData: keepPreviousData,
  });
}

export function useVenue(id: string) {
  return useQuery({ queryKey: keys.venue(id), queryFn: () => api.get<Venue>(`/venue-owner/venues/${id}/`), enabled: Boolean(id) });
}

export function useCreateVenue() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: VenueWrite) => api.post<Venue>("/venue-owner/venues/", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.venues }),
  });
}

export function useUpdateVenue(id: string) {
  const qc = useQueryClient();
  return useMutation({
    /** JSON for fields; FormData when a cover image is uploaded. */
    mutationFn: (body: VenueWrite | FormData) => api.patch<Venue>(`/venue-owner/venues/${id}/`, body),
    onSuccess: (venue) => {
      qc.setQueryData(keys.venue(id), venue);
      qc.invalidateQueries({ queryKey: keys.venues, exact: false });
    },
  });
}

type HallWrite = Partial<Pick<VenueHall, "name" | "capacity" | "base_price" | "is_active">>;

export function useCreateHall(venueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: HallWrite) => api.post<VenueHall>(`/venue-owner/venues/${venueId}/halls/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.venue(venueId) }),
  });
}

export function useUpdateHall(venueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: HallWrite & { id: string }) => api.patch<VenueHall>(`/venue-owner/venues/${venueId}/halls/${id}/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.venue(venueId) }),
  });
}

export function useMembers(venueId: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.members(venueId),
    queryFn: () => api.get<VenueMember[]>(`/venue-owner/venues/${venueId}/members/`),
    enabled: Boolean(venueId) && enabled,
  });
}

export function useAddMember(venueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { phone_number: string; role: MembershipRole }) => api.post<VenueMember>(`/venue-owner/venues/${venueId}/members/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.members(venueId) }),
  });
}

export function useUpdateMember(venueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; role?: MembershipRole; is_active?: boolean }) =>
      api.patch<VenueMember>(`/venue-owner/venues/${venueId}/members/${id}/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.members(venueId) }),
  });
}

// ------------------------------------------------------------------ gallery
export const MAX_GALLERY_IMAGES = 20;
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

export function useUploadImage(venueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("image", file);
      return api.post<VenueImage>(`/venue-owner/venues/${venueId}/images/`, form);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.venue(venueId) }),
  });
}

export function useDeleteImage(venueId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (imageId: string) => api.delete(`/venue-owner/venues/${venueId}/images/${imageId}/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.venue(venueId) }),
  });
}
