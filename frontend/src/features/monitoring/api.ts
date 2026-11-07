"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { API_BASE, api } from "@/lib/api/client";
import type {
  EndpointCatalog,
  HealthProbe,
  MonitoringOverview,
  MonitoringWindow,
  Paginated,
  RequestLogEntry,
} from "@/lib/api/types";

/** Every number on the monitoring page comes from these real endpoints — nothing is synthesized. */
const POLL_MS = 15_000;

export function useMonitoringOverview(window: MonitoringWindow) {
  return useQuery({
    queryKey: ["monitoring", "overview", window],
    queryFn: ({ signal }) => api.get<MonitoringOverview>("/monitoring/overview/", { window }, signal),
    refetchInterval: POLL_MS,
    placeholderData: keepPreviousData,
  });
}

export type LogParams = Record<string, string | number | undefined>;

export function useRequestLogs(params: LogParams, live: boolean) {
  return useQuery({
    queryKey: ["monitoring", "logs", params],
    queryFn: ({ signal }) => api.get<Paginated<RequestLogEntry>>("/monitoring/logs/", params, signal),
    refetchInterval: live ? 5_000 : false,
    placeholderData: keepPreviousData,
  });
}

export function useEndpointCatalog() {
  return useQuery({
    queryKey: ["monitoring", "endpoints"],
    queryFn: ({ signal }) => api.get<EndpointCatalog>("/monitoring/endpoints/", undefined, signal),
    staleTime: 60_000,
  });
}

/**
 * Calls the public probes exactly like a load balancer would and measures the round trip.
 * Raw fetch on purpose: a 503 readiness body is data here, not an error.
 */
async function probe(signal?: AbortSignal): Promise<HealthProbe> {
  const started = performance.now();
  const checked_at = new Date().toISOString();
  let live = false;
  try {
    const res = await fetch(`${API_BASE}/health/live/`, { cache: "no-store", signal });
    live = res.ok;
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
  }
  const latency_ms = live ? Math.round(performance.now() - started) : null;
  if (!live) return { live, ready: "unavailable", checks: {}, latency_ms, checked_at };

  try {
    const res = await fetch(`${API_BASE}/health/ready/`, { cache: "no-store", signal });
    const body = (await res.json()) as { status?: HealthProbe["ready"]; checks?: HealthProbe["checks"] };
    return { live, ready: body.status ?? (res.ok ? "ok" : "unavailable"), checks: body.checks ?? {}, latency_ms, checked_at };
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    return { live, ready: "unavailable", checks: {}, latency_ms, checked_at };
  }
}

export function useHealthProbe() {
  return useQuery({
    queryKey: ["monitoring", "health"],
    queryFn: ({ signal }) => probe(signal),
    refetchInterval: POLL_MS,
    retry: false,
  });
}

export type HealthLevel = "healthy" | "degraded" | "unavailable" | "unknown";

/** Probes decide availability; the recent 5xx rate / latency can only downgrade a healthy API. */
export function healthLevel(probe: HealthProbe | undefined, recent: MonitoringOverview | undefined): HealthLevel {
  if (!probe) return "unknown";
  if (!probe.live || probe.ready === "unavailable") return "unavailable";
  if (probe.ready === "degraded") return "degraded";
  const t = recent?.totals;
  if (t && t.total >= 20 && t.server_errors / t.total >= 0.05) return "degraded";
  if (t && (t.p95_ms ?? 0) > 2000) return "degraded";
  return "healthy";
}
