"use client";

import { motion } from "motion/react";

import type { HealthLevel } from "@/features/monitoring/api";
import type { EndpointStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { spring } from "@/motion/tokens";

// -------------------------------------------------------------------- tabs
export function AnimatedTabs<T extends string>({
  tabs,
  value,
  onChange,
  layoutId,
  size = "md",
}: {
  tabs: { value: T; label: string; icon?: React.ComponentType<{ className?: string }>; count?: number }[];
  value: T;
  onChange: (value: T) => void;
  layoutId: string;
  size?: "sm" | "md";
}) {
  return (
    <div role="tablist" className="glass inline-flex max-w-full items-center gap-1 overflow-x-auto rounded-2xl p-1">
      {tabs.map((tab) => {
        const active = tab.value === value;
        const Icon = tab.icon;
        return (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(tab.value)}
            className={cn(
              "relative inline-flex shrink-0 items-center gap-2 rounded-xl font-semibold whitespace-nowrap outline-none transition-colors focus-visible:ring-4 focus-visible:ring-brand/25",
              size === "sm" ? "h-8 px-3 text-xs" : "h-10 px-4 text-sm",
              active ? "text-white" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {active && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 shadow-[0_8px_22px_-12px_rgb(6_182_212/0.8)]"
                transition={spring.sidebar}
                aria-hidden
              />
            )}
            {Icon && <Icon className="relative z-10 size-4" />}
            <span className="relative z-10">{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={cn(
                  "relative z-10 rounded-full px-1.5 text-[10px] tabular-nums",
                  active ? "bg-white/20" : "bg-muted",
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ----------------------------------------------------------------- badges
const METHOD_STYLES: Record<string, string> = {
  GET: "bg-blue-500/14 text-blue-700 dark:text-blue-300",
  POST: "bg-emerald-500/14 text-emerald-700 dark:text-emerald-300",
  PUT: "bg-amber-500/14 text-amber-700 dark:text-amber-300",
  PATCH: "bg-violet-500/14 text-violet-700 dark:text-violet-300",
  DELETE: "bg-red-500/14 text-red-700 dark:text-red-300",
};

export function MethodBadge({ method, className }: { method: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-6 w-16 shrink-0 items-center justify-center rounded-md font-mono text-[11px] font-bold tracking-wide",
        METHOD_STYLES[method] ?? "bg-muted text-muted-foreground",
        className,
      )}
    >
      {method}
    </span>
  );
}

export function StatusCode({ code }: { code: number }) {
  const tone =
    code >= 500
      ? "bg-red-500/14 text-red-700 dark:text-red-300"
      : code >= 400
        ? "bg-amber-500/14 text-amber-700 dark:text-amber-300"
        : code >= 300
          ? "bg-slate-500/14 text-slate-700 dark:text-slate-300"
          : "bg-emerald-500/14 text-emerald-700 dark:text-emerald-300";
  return <span className={cn("inline-flex h-6 items-center rounded-md px-2 font-mono text-xs font-bold tabular-nums", tone)}>{code}</span>;
}

const ENDPOINT_STATUS: Record<EndpointStatus, { label: string; dot: string; text: string }> = {
  healthy: { label: "Sog'lom", dot: "bg-emerald-500", text: "text-emerald-700 dark:text-emerald-300" },
  degraded: { label: "Sekin / xatoli", dot: "bg-amber-500", text: "text-amber-700 dark:text-amber-300" },
  failing: { label: "Ishlamayapti", dot: "bg-red-500", text: "text-red-700 dark:text-red-300" },
  idle: { label: "Trafik yo'q", dot: "bg-slate-400", text: "text-muted-foreground" },
};

export function EndpointStatusBadge({ status }: { status: EndpointStatus }) {
  const s = ENDPOINT_STATUS[status];
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-semibold whitespace-nowrap", s.text)}>
      <span className={cn("size-1.5 rounded-full", s.dot)} aria-hidden />
      {s.label}
    </span>
  );
}

const HEALTH: Record<HealthLevel, { label: string; dot: string; ring: string; text: string }> = {
  healthy: {
    label: "Healthy",
    dot: "bg-emerald-500",
    ring: "border-emerald-500/30 bg-emerald-500/10",
    text: "text-emerald-700 dark:text-emerald-300",
  },
  degraded: {
    label: "Degraded",
    dot: "bg-amber-500",
    ring: "border-amber-500/30 bg-amber-500/10",
    text: "text-amber-700 dark:text-amber-300",
  },
  unavailable: {
    label: "Unavailable",
    dot: "bg-red-500",
    ring: "border-red-500/30 bg-red-500/10",
    text: "text-red-700 dark:text-red-300",
  },
  unknown: { label: "Tekshirilmoqda…", dot: "bg-slate-400", ring: "border-glass-border bg-muted/60", text: "text-muted-foreground" },
};

export function HealthPill({ level, detail }: { level: HealthLevel; detail?: string }) {
  const h = HEALTH[level];
  return (
    <motion.span
      key={level}
      initial={{ scale: 0.92, opacity: 0 }}
      animate={{ scale: 1, opacity: 1, transition: spring.pop }}
      className={cn("inline-flex h-10 items-center gap-2.5 rounded-2xl border px-3.5 text-sm font-bold", h.ring, h.text)}
      role="status"
      aria-live="polite"
    >
      <span className="relative flex size-2.5">
        {level !== "unknown" && (
          <motion.span
            className={cn("absolute inset-0 rounded-full", h.dot)}
            animate={{ scale: [1, 2.4], opacity: [0.6, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeOut" }}
          />
        )}
        <span className={cn("relative size-2.5 rounded-full", h.dot)} />
      </span>
      {h.label}
      {detail && <span className="font-medium opacity-75">· {detail}</span>}
    </motion.span>
  );
}
