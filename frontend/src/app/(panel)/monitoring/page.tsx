"use client";

import { ActivityIcon, BookOpenIcon, ScrollTextIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { PageHeader } from "@/components/common";
import { RequirePermission } from "@/components/layout/require-permission";
import { AnimatedTabs, HealthPill } from "@/components/monitoring/primitives";
import { PageTransition } from "@/components/motion/page-transition";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { healthLevel, useEndpointCatalog, useHealthProbe, useMonitoringOverview } from "@/features/monitoring/api";
import { EndpointsTab } from "@/features/monitoring/endpoints-tab";
import { LogsTab } from "@/features/monitoring/logs-tab";
import { OverviewTab } from "@/features/monitoring/overview-tab";
import type { MonitoringWindow } from "@/lib/api/types";
import { fadeUp } from "@/motion/tokens";

type Tab = "overview" | "endpoints" | "logs";

const WINDOWS: { value: MonitoringWindow; label: string }[] = [
  { value: "15m", label: "Oxirgi 15 daqiqa" },
  { value: "1h", label: "Oxirgi 1 soat" },
  { value: "24h", label: "Oxirgi 24 soat" },
  { value: "7d", label: "Oxirgi 7 kun" },
];

function MonitoringContent() {
  const [tab, setTab] = useState<Tab>("overview");
  const [range, setRange] = useState<MonitoringWindow>("1h");
  const overview = useMonitoringOverview(range);
  const recent = useMonitoringOverview("15m");
  const catalog = useEndpointCatalog();
  const health = useHealthProbe();
  const level = healthLevel(health.data, recent.data);
  const detail = health.data?.latency_ms != null ? `${health.data.latency_ms} ms` : undefined;

  return (
    <>
      <PageHeader
        title="API Monitoring"
        crumb="Super Admin / Monitoring"
        actions={
          <>
            <HealthPill level={level} detail={detail} />
            {tab === "overview" && (
              <Select value={range} onValueChange={(v) => setRange(v as MonitoringWindow)}>
                <SelectTrigger className="min-w-[170px]" aria-label="Vaqt oralig'i">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {WINDOWS.map((w) => (
                    <SelectItem key={w.value} value={w.value}>
                      {w.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </>
        }
      />

      {health.data && health.data.live && Object.keys(health.data.checks).length > 0 && (
        <div className="flex flex-wrap gap-2 px-1 text-xs text-muted-foreground">
          {Object.entries(health.data.checks).map(([name, state]) => (
            <span key={name} className="glass inline-flex items-center gap-1.5 rounded-full px-2.5 py-1">
              <span className={state === "ok" ? "size-1.5 rounded-full bg-emerald-500" : "size-1.5 rounded-full bg-red-500"} />
              {name}: <b className="text-foreground">{state}</b>
            </span>
          ))}
        </div>
      )}

      <AnimatedTabs
        layoutId="monitoring-tab"
        value={tab}
        onChange={setTab}
        tabs={[
          { value: "overview", label: "Umumiy ko'rinish", icon: ActivityIcon },
          { value: "endpoints", label: "Endpointlar", icon: BookOpenIcon, count: catalog.data?.count },
          { value: "logs", label: "So'rovlar jurnali", icon: ScrollTextIcon },
        ]}
      />

      <AnimatePresence mode="wait" initial={false}>
        {/* Variant labels (not object targets) so nested GlassCards inherit "animate". */}
        <motion.div key={tab} variants={fadeUp} initial="initial" animate="animate" exit="exit" className="flex flex-col gap-5">
          {tab === "overview" && (
            <OverviewTab data={overview.data} error={overview.error} isPending={overview.isPending} onRetry={() => overview.refetch()} />
          )}
          {tab === "endpoints" && (
            <EndpointsTab data={catalog.data} error={catalog.error} isPending={catalog.isPending} onRetry={() => catalog.refetch()} />
          )}
          {tab === "logs" && <LogsTab />}
        </motion.div>
      </AnimatePresence>
    </>
  );
}

export default function MonitoringPage() {
  return (
    <RequirePermission requires="super">
      <PageTransition>
        <MonitoringContent />
      </PageTransition>
    </RequirePermission>
  );
}
