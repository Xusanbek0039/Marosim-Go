"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";

export interface Plan {
  id: string;
  code: string;
  name: string;
  duration_months: number;
  price: string;
  currency: "UZS";
  max_viewers: number;
  is_active: boolean;
  position: number;
}

export type SubscriptionState = "PENDING" | "ACTIVE" | "SCHEDULED" | "EXPIRED" | "REJECTED" | "CANCELLED";

export interface MySubscription {
  id: string;
  plan: { id: string; code: string; name: string };
  status: string;
  state: SubscriptionState;
  price: string;
  currency: "UZS";
  duration_months: number;
  max_viewers: number;
  starts_at: string | null;
  ends_at: string | null;
  user_note: string;
  admin_note: string;
  paid_amount: string | null;
  created_at: string;
  decided_at: string | null;
}

export interface SubscriptionStatus {
  active: MySubscription | null;
  pending: MySubscription | null;
  paid_until: string | null;
  clean_access: boolean;
  viewer_limit: number;
  payment_instructions: string;
  plans: Plan[];
}

type Tone = "neutral" | "brand" | "success" | "warning" | "danger";
export const STATE: Record<SubscriptionState, { label: string; tone: Tone }> = {
  PENDING: { label: "To'lov tasdig'i kutilmoqda", tone: "warning" },
  ACTIVE: { label: "Faol", tone: "success" },
  SCHEDULED: { label: "Navbatda (keyingi davr)", tone: "brand" },
  EXPIRED: { label: "Muddati tugagan", tone: "neutral" },
  REJECTED: { label: "Rad etilgan", tone: "danger" },
  CANCELLED: { label: "Bekor qilingan", tone: "neutral" },
};

const keys = { status: ["me", "subscription"] as const, list: ["me", "subscriptions"] as const };

export function useSubscriptionStatus() {
  return useQuery({ queryKey: keys.status, queryFn: () => api.get<SubscriptionStatus>("/me/subscriptions/status/") });
}

export function useMySubscriptions() {
  return useQuery({ queryKey: keys.list, queryFn: () => api.get<MySubscription[]>("/me/subscriptions/") });
}

function useInvalidate() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: keys.status });
    qc.invalidateQueries({ queryKey: keys.list });
  };
}

export function useRequestSubscription() {
  return useMutation({
    mutationFn: (body: { plan: string; user_note?: string }) => api.post<MySubscription>("/me/subscriptions/", body),
    onSuccess: useInvalidate(),
  });
}

export function useCancelRequest() {
  return useMutation({
    mutationFn: (id: string) => api.post<MySubscription>(`/me/subscriptions/${id}/cancel/`),
    onSuccess: useInvalidate(),
  });
}
