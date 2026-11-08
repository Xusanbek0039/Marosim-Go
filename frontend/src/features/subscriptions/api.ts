"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";

import { createResource } from "../crud";

export type SubscriptionState = "PENDING" | "ACTIVE" | "SCHEDULED" | "EXPIRED" | "REJECTED" | "CANCELLED";
export type PaymentMethod = "CARD_TRANSFER" | "CASH" | "CLICK" | "PAYME" | "BANK" | "OTHER";

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

export interface AdminSubscription {
  id: string;
  user: { id: string; full_name: string; phone_number: string };
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
  payment_method: PaymentMethod | "";
  payment_reference: string;
  paid_at: string | null;
  decided_by: { id: string; full_name: string; phone_number: string } | null;
  decided_at: string | null;
  created_at: string;
}

export interface Summary {
  pending: number;
  active: number;
  revenue_month: string;
  revenue_total: string;
}

export interface Payment {
  payment_method?: PaymentMethod | "";
  paid_amount?: string | null;
  payment_reference?: string;
  admin_note?: string;
}

/** `/api/v1/admin/subscriptions/` — rights `subscriptions.*`, granted by the Super Admin. */
export const subscriptionsResource = createResource<AdminSubscription>("admin/subscriptions");

type Tone = string;
export const STATE: Record<SubscriptionState, { label: string; className: Tone }> = {
  PENDING: { label: "To'lov kutilmoqda", className: "bg-amber-500/16 text-amber-700 dark:text-amber-300" },
  ACTIVE: { label: "Faol", className: "bg-emerald-500/16 text-emerald-700 dark:text-emerald-300" },
  SCHEDULED: { label: "Navbatda", className: "bg-blue-500/14 text-blue-700 dark:text-blue-300" },
  EXPIRED: { label: "Tugagan", className: "bg-slate-500/14 text-slate-700 dark:text-slate-300" },
  REJECTED: { label: "Rad etilgan", className: "bg-red-500/14 text-red-700 dark:text-red-300" },
  CANCELLED: { label: "Bekor qilingan", className: "bg-slate-500/14 text-slate-700 dark:text-slate-300" },
};

export const PAYMENT_METHODS: Record<PaymentMethod, string> = {
  CARD_TRANSFER: "Kartadan kartaga",
  CASH: "Naqd",
  CLICK: "Click",
  PAYME: "Payme",
  BANK: "Bank o'tkazmasi",
  OTHER: "Boshqa",
};

const keys = {
  summary: ["admin/subscriptions", "summary"] as const,
  plans: ["admin/subscription-plans"] as const,
  settings: ["admin/subscription-settings"] as const,
};

function useRefresh() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: subscriptionsResource.keys.all });
    qc.invalidateQueries({ queryKey: keys.summary });
  };
}

export function useSummary() {
  return useQuery({ queryKey: keys.summary, queryFn: () => api.get<Summary>("/admin/subscriptions/summary/") });
}

export function useDecision() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ id, action, body }: { id: string; action: "approve" | "reject" | "cancel"; body: Payment }) =>
      api.post<AdminSubscription>(`/admin/subscriptions/${id}/${action}/`, body),
    onSuccess: refresh,
  });
}

export function useGrant() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (body: Payment & { user_id: string; plan: string }) => api.post<AdminSubscription>("/admin/subscriptions/", body),
    onSuccess: refresh,
  });
}

export function usePlans(enabled = true) {
  return useQuery({ queryKey: keys.plans, queryFn: () => api.get<Plan[]>("/admin/subscription-plans/"), enabled });
}

export function useUpdatePlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<Plan> & { id: string }) => api.patch<Plan>(`/admin/subscription-plans/${id}/`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.plans }),
  });
}

export function useSettings() {
  return useQuery({
    queryKey: keys.settings,
    queryFn: () => api.get<{ payment_instructions: string; updated_at: string }>("/admin/subscription-settings/"),
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { payment_instructions: string }) => api.patch("/admin/subscription-settings/", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.settings }),
  });
}

export const formatMoney = (value?: string | number | null) =>
  value === null || value === undefined || value === "" ? "—" : `${String(Math.round(Number(value))).replace(/\B(?=(\d{3})+(?!\d))/g, " ")} so'm`;
