"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { AdminVenue, PublicationStatus, VenueHall, VenueImage, VenueMemberRole, VenueRegion, VenueType } from "@/lib/api/types";

import { createResource } from "../crud";

/** Panel API: `/api/v1/admin/venues/` (rights: `venues.*`, granted by the Super Admin). */
export const venuesResource = createResource<AdminVenue>("admin/venues");

export const MAX_GALLERY_IMAGES = 20;
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

export const REGION_LABELS: Record<VenueRegion, string> = {
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

export const PUBLICATION: Record<PublicationStatus, { label: string; className: string }> = {
  PRIVATE: { label: "Yopiq", className: "bg-slate-500/14 text-slate-700 dark:text-slate-300" },
  PENDING_APPROVAL: { label: "Tasdiq kutmoqda", className: "bg-amber-500/16 text-amber-700 dark:text-amber-300" },
  APPROVED: { label: "Ommaga ochiq", className: "bg-emerald-500/16 text-emerald-700 dark:text-emerald-300" },
  REJECTED: { label: "Rad etilgan", className: "bg-red-500/14 text-red-700 dark:text-red-300" },
  SUSPENDED: { label: "To'xtatilgan", className: "bg-red-500/14 text-red-700 dark:text-red-300" },
};

export const MEMBER_ROLE_LABELS: Record<VenueMemberRole, string> = {
  OWNER: "Egasi",
  MANAGER: "Menejer",
  SCHEDULER: "Jadval yurituvchi",
  VIEWER: "Kuzatuvchi",
};

export const formatMoney = (value?: string | number | null) =>
  value === null || value === undefined || value === "" ? "—" : `${String(Math.round(Number(value))).replace(/\B(?=(\d{3})+(?!\d))/g, " ")} so'm`;

function useRefreshVenue() {
  const qc = useQueryClient();
  return (id: string) => {
    qc.invalidateQueries({ queryKey: venuesResource.keys.all });
    qc.invalidateQueries({ queryKey: venuesResource.keys.detail(id) });
  };
}

export function useAddHall(venueId: string) {
  const refresh = useRefreshVenue();
  return useMutation({
    mutationFn: (body: { name: string; capacity: number; base_price: string | null }) =>
      api.post<VenueHall>(`/admin/venues/${venueId}/halls/`, body),
    onSuccess: () => refresh(venueId),
  });
}

export function useUpdateHall(venueId: string) {
  const refresh = useRefreshVenue();
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<Pick<VenueHall, "name" | "capacity" | "base_price" | "is_active">> & { id: string }) =>
      api.patch<VenueHall>(`/admin/venues/${venueId}/halls/${id}/`, body),
    onSuccess: () => refresh(venueId),
  });
}

export function useUploadImage(venueId: string) {
  const refresh = useRefreshVenue();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("image", file);
      return api.post<VenueImage>(`/admin/venues/${venueId}/images/`, form);
    },
    onSuccess: () => refresh(venueId),
  });
}

export function useDeleteImage(venueId: string) {
  const refresh = useRefreshVenue();
  return useMutation({
    mutationFn: (imageId: string) => api.delete(`/admin/venues/${venueId}/images/${imageId}/`),
    onSuccess: () => refresh(venueId),
  });
}
