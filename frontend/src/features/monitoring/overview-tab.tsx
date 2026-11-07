"use client";

import {
  ActivityIcon,
  AlertOctagonIcon,
  AlertTriangleIcon,
  CheckCircle2Icon,
  GaugeIcon,
  KeyRoundIcon,
  LayersIcon,
  ShieldAlertIcon,
  TimerIcon,
  ZapIcon,
  type LucideIcon,
} from "lucide-react";
import { motion } from "motion/react";

import { ErrorState, GlassCard } from "@/components/common";
import { ChartLegend, LatencyChart, TrafficChart } from "@/components/monitoring/charts";
import { EndpointStatusBadge, MethodBadge } from "@/components/monitoring/primitives";
import { AnimatedNumber } from "@/components/motion/animated-number";
import { Skeleton } from "@/components/ui/skeleton";
import type { MonitoringOverview } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import { listContainer, spring, stagger } from "@/motion/tokens";

const fmtMs = (n: number) => (n < 10 ? n.toFixed(1) : formatNumber(n));
const fmtRate = (n: number) => (n < 10 ? n.toFixed(2) : formatNumber(n));

interface Stat {
  label: string;
  value: number | null;
  suffix?: string;
  hint: string;
  icon: LucideIcon;
  tint: string;
  format?: (n: number) => string;
}

function StatCard({ stat }: { stat: Stat }) {
  const Icon = stat.icon;
  return (
    <GlassCard interactive className="flex flex-col gap-3 p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[13px] font-semibold text-muted-foreground">{stat.label}</p>
        <span className={cn("flex size-9 items-center justify-center rounded-xl text-white shadow-lg", stat.tint)}>
          <Icon className="size-[18px]" aria-hidden />
        </span>
      </div>
      <p className="flex items-baseline gap-1.5">
        {stat.value === null ? (
          <span className="text-3xl font-extrabold text-muted-foreground">—</span>
        ) : (
          <AnimatedNumber value={stat.value} format={stat.format} className="text-3xl font-extrabold tracking-tight tabular-nums" />
        )}
        {stat.suffix && stat.value !== null && <span className="text-sm font-semibold text-muted-foreground">{stat.suffix}</span>}
      </p>
      <p className="text-xs text-muted-foreground">{stat.hint}</p>
    </GlassCard>
  );
}

export function OverviewSkeleton() {
  return (
    <div className="flex flex-col gap-5" aria-busy="true" aria-label="Yuklanmoqda">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(210px,1fr))] gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="glass flex flex-col gap-3 rounded-3xl p-5">
            <Skeleton className="h-3.5 w-1/2" />
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-3 w-2/3" />
          </div>
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <Skeleton className="h-72 rounded-3xl" />
        <Skeleton className="h-72 rounded-3xl" />
      </div>
    </div>
  );
}

const pct = (part: number, total: number) => (total ? `${((part / total) * 100).toFixed(1)}%` : "0%");

export function OverviewTab({
  data,
  error,
  isPending,
  onRetry,
}: {
  data: MonitoringOverview | undefined;
  error: unknown;
  isPending: boolean;
  onRetry: () => void;
}) {
  if (isPending) return <OverviewSkeleton />;
  if (error || !data) return <GlassCard><ErrorState error={error} onRetry={onRetry} /></GlassCard>;

  const t = data.totals;
  const stats: Stat[] = [
    { label: "Jami so'rovlar", value: t.total, hint: `oxirgi daqiqada ${formatNumber(t.rpm_last_minute)} ta`, icon: ActivityIcon, tint: "bg-gradient-to-br from-blue-600 to-blue-400" },
    { label: "Muvaffaqiyatli", value: t.success, hint: t.success_rate === null ? "hali so'rov yo'q" : `${t.success_rate}% (2xx/3xx)`, icon: CheckCircle2Icon, tint: "bg-gradient-to-br from-emerald-600 to-teal-400" },
    { label: "Mijoz xatolari", value: t.client_errors, hint: `${pct(t.client_errors, t.total)} · 4xx, shundan ${formatNumber(t.throttled)} ta 429`, icon: AlertTriangleIcon, tint: "bg-gradient-to-br from-amber-500 to-orange-400" },
    { label: "Server xatolari", value: t.server_errors, hint: `${pct(t.server_errors, t.total)} · 5xx`, icon: AlertOctagonIcon, tint: "bg-gradient-to-br from-red-600 to-rose-400" },
    { label: "O'rtacha javob vaqti", value: t.avg_ms, suffix: "ms", format: fmtMs, hint: "server ichidagi to'liq ishlov", icon: TimerIcon, tint: "bg-gradient-to-br from-cyan-600 to-cyan-400" },
    { label: "P95 kechikish", value: t.p95_ms, suffix: "ms", format: fmtMs, hint: "so'rovlarning 95% shundan tezroq", icon: GaugeIcon, tint: "bg-gradient-to-br from-sky-600 to-indigo-500" },
    { label: "Daqiqasiga so'rov", value: t.rpm, format: fmtRate, hint: "tanlangan oraliq bo'yicha o'rtacha", icon: ZapIcon, tint: "bg-gradient-to-br from-indigo-600 to-blue-500" },
    { label: "Faol endpointlar", value: t.active_endpoints, hint: `${formatNumber(t.documented_endpoints)} ta hujjatlashtirilgan`, icon: LayersIcon, tint: "bg-gradient-to-br from-teal-600 to-cyan-500" },
  ];
  const maxStatus = Math.max(1, ...data.status_codes.map((s) => s.count));
  const s = data.security;

  return (
    <div className="flex flex-col gap-5">
      <motion.section
        variants={listContainer(stagger.cards)}
        initial="initial"
        animate="animate"
        className="grid grid-cols-[repeat(auto-fit,minmax(210px,1fr))] gap-4"
      >
        {stats.map((stat) => (
          <StatCard key={stat.label} stat={stat} />
        ))}
      </motion.section>

      <motion.section variants={listContainer(stagger.cards)} initial="initial" animate="animate" className="grid gap-5 xl:grid-cols-2">
        <GlassCard className="flex min-w-0 flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-bold">Trafik</h2>
            <ChartLegend items={[{ label: "Jami", color: "#2563eb" }, { label: "4xx", color: "#f59e0b" }, { label: "5xx", color: "#ef4444" }]} />
          </div>
          <TrafficChart key={data.window} series={data.series} bucket={data.bucket} />
        </GlassCard>
        <GlassCard className="flex min-w-0 flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-bold">O&apos;rtacha kechikish</h2>
            <ChartLegend items={[{ label: "avg ms", color: "#06b6d4" }]} />
          </div>
          <LatencyChart key={data.window} series={data.series} bucket={data.bucket} />
        </GlassCard>
      </motion.section>

      <motion.section variants={listContainer(stagger.cards)} initial="initial" animate="animate" className="flex flex-wrap items-stretch gap-5">
        <GlassCard className="flex min-w-0 flex-[999_1_560px] flex-col gap-3">
          <h2 className="text-lg font-bold">Eng faol endpointlar</h2>
          {data.top_endpoints.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">Bu oraliqda trafik yo&apos;q.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="text-left text-xs text-muted-foreground">
                    <th className="px-2 py-2 font-semibold">Endpoint</th>
                    <th className="px-2 py-2 text-right font-semibold">So&apos;rov</th>
                    <th className="px-2 py-2 text-right font-semibold">4xx / 5xx</th>
                    <th className="px-2 py-2 text-right font-semibold">avg</th>
                    <th className="px-2 py-2 font-semibold">Holat</th>
                  </tr>
                </thead>
                <tbody>
                  {data.top_endpoints.map((e, i) => (
                    <motion.tr
                      key={`${e.method} ${e.route}`}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0, transition: { ...spring.soft, delay: i * 0.03 } }}
                      className="border-t border-border/70"
                    >
                      <td className="px-2 py-2.5">
                        <span className="flex min-w-0 items-center gap-2.5">
                          <MethodBadge method={e.method} />
                          <span className="truncate font-mono text-xs">{e.route}</span>
                        </span>
                      </td>
                      <td className="px-2 py-2.5 text-right font-semibold tabular-nums">{formatNumber(e.count)}</td>
                      <td className="px-2 py-2.5 text-right text-muted-foreground tabular-nums">
                        {formatNumber(e.client_errors)} / <span className={e.server_errors ? "font-semibold text-red-600 dark:text-red-400" : ""}>{formatNumber(e.server_errors)}</span>
                      </td>
                      <td className="px-2 py-2.5 text-right text-muted-foreground tabular-nums">{e.avg_ms === null ? "—" : `${fmtMs(e.avg_ms)} ms`}</td>
                      <td className="px-2 py-2.5">
                        <EndpointStatusBadge status={e.status} />
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </GlassCard>

        <div className="flex flex-[1_1_300px] flex-col gap-5">
          <GlassCard className="flex flex-col gap-4">
            <h2 className="text-lg font-bold">Status kodlar</h2>
            {data.status_codes.length === 0 && <p className="text-sm text-muted-foreground">Ma&apos;lumot yo&apos;q.</p>}
            {data.status_codes.map((row) => (
              <div key={row.status_code} className="flex flex-col gap-1.5">
                <div className="flex justify-between text-sm">
                  <span className="font-mono font-semibold">{row.status_code}</span>
                  <span className="text-muted-foreground tabular-nums">{formatNumber(row.count)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <motion.div
                    className={cn(
                      "h-full rounded-full",
                      row.status_code >= 500 ? "bg-red-500" : row.status_code >= 400 ? "bg-amber-500" : "bg-gradient-to-r from-blue-600 to-cyan-400",
                    )}
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.max(3, (row.count / maxStatus) * 100)}%` }}
                    transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
                  />
                </div>
              </div>
            ))}
          </GlassCard>

          <GlassCard className="flex flex-col gap-3">
            <h2 className="flex items-center gap-2 text-lg font-bold">
              <ShieldAlertIcon className="size-5 text-cyan-600 dark:text-cyan-300" aria-hidden /> Autentifikatsiya xavfsizligi
            </h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                ["Muvaffaqiyatsiz kirish", s.failed_logins, s.failed_logins > 0],
                ["Bloklangan hisoblar", s.lockouts, s.lockouts > 0],
                ["Token qayta ishlatish", s.token_reuse, s.token_reuse > 0],
                ["Throttled (429)", t.throttled, t.throttled > 0],
                ["Muvaffaqiyatli kirish", s.logins, false],
                ["Ro'yxatdan o'tish", s.registrations, false],
              ].map(([label, value, alert]) => (
                <div key={String(label)} className={cn("rounded-2xl p-3", alert ? "bg-amber-500/12" : "bg-muted/70")}>
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className={cn("text-xl font-extrabold tabular-nums", alert && "text-amber-700 dark:text-amber-300")}>
                    {formatNumber(Number(value))}
                  </p>
                </div>
              ))}
            </div>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <KeyRoundIcon className="size-3.5" aria-hidden /> Audit jurnalidan, tanlangan oraliq bo&apos;yicha.
            </p>
          </GlassCard>
        </div>
      </motion.section>
    </div>
  );
}
