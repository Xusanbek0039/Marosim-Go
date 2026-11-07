"use client";

import {
  AlertTriangleIcon,
  BookOpenIcon,
  CheckCircle2Icon,
  ClockIcon,
  FileWarningIcon,
  GitCompareArrowsIcon,
  ListTreeIcon,
  RadioIcon,
  ShieldAlertIcon,
  SmartphoneIcon,
} from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";

import { EmptyState, ErrorState, GlassCard, PageHeader } from "@/components/common";
import { ROLE_LABELS, RoleBadge } from "@/components/devcenter/role-badge";
import { RequirePermission } from "@/components/layout/require-permission";
import { AnimatedNumber } from "@/components/motion/animated-number";
import { PageTransition } from "@/components/motion/page-transition";
import { AnimatedTabs, EndpointStatusBadge, MethodBadge } from "@/components/monitoring/primitives";
import { Skeleton } from "@/components/ui/skeleton";
import { EndpointsTab } from "@/features/monitoring/endpoints-tab";
import type { ApiRole, ChangelogEntry, MobileFeature } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { listContainer } from "@/motion/tokens";

import { useChangelog, useDevcenterEndpoints, useDevcenterOverview, useMobileGuide } from "./api";
import { slugOf } from "./roles";

const CRUMB = "Super Admin / Developer Center";

const ROLE_INTRO: Record<ApiRole, string> = {
  PUBLIC: "Autentifikatsiya talab qilmaydigan endpointlar: ro'yxatdan o'tish, login, token, health.",
  USER: "USER rolidagi hisob (kelin, kuyov, mehmon) chaqira oladigan endpointlar — mobil ilova uchun.",
  STUDIO: "STUDIO rolidagi hisob chaqira oladigan endpointlar — studiya mobil ilovasi uchun.",
  VENUE_OWNER: "VENUE_OWNER (to'yxona) hisobi chaqira oladigan endpointlar; qaysi to'yxona va qaysi amal — a'zolik roli hal qiladi.",
  ADMIN: "ADMIN — har bir endpoint uchun Super Admin bergan granular ruxsat kodi ham kerak.",
  SUPER_ADMIN: "SUPER_ADMIN chaqira oladigan barcha endpointlar (granular kodlarning hammasi unda bor).",
};

export function DevPage({ title, actions, children }: { title: string; actions?: React.ReactNode; children: React.ReactNode }) {
  return (
    <RequirePermission requires="super">
      <PageTransition>
        <PageHeader title={title} crumb={CRUMB} actions={actions} />
        <motion.div variants={listContainer()} initial="initial" animate="animate" className="flex flex-col gap-5">
          {children}
        </motion.div>
      </PageTransition>
    </RequirePermission>
  );
}

// ---------------------------------------------------------------- overview
function Stat({
  label,
  value,
  hint,
  icon: Icon,
  tint,
}: {
  label: string;
  value: number;
  hint: string;
  icon: React.ComponentType<{ className?: string }>;
  tint: string;
}) {
  return (
    <GlassCard interactive className="flex flex-col gap-3 p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[13px] font-semibold text-muted-foreground">{label}</p>
        <span className={cn("flex size-9 items-center justify-center rounded-xl text-white shadow-lg", tint)}>
          <Icon className="size-[18px]" />
        </span>
      </div>
      <AnimatedNumber value={value} className="text-3xl font-extrabold tracking-tight tabular-nums" />
      <p className="text-xs text-muted-foreground">{hint}</p>
    </GlassCard>
  );
}

export function DevOverview() {
  const { data, error, isPending, refetch } = useDevcenterOverview();
  if (isPending) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-busy="true">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-3xl" />
        ))}
      </div>
    );
  }
  if (error || !data) return <GlassCard><ErrorState error={error} onRetry={() => refetch()} /></GlassCard>;
  const t = data.totals;

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Operatsiyalar" value={t.operations} hint={`OpenAPI ${data.openapi_version} · API ${data.api_version}`} icon={ListTreeIcon} tint="bg-gradient-to-br from-blue-600 to-cyan-500" />
        <Stat label="Hujjatlashtirilgan" value={t.documented} hint={`${t.documentation_missing} ta — Documentation Missing`} icon={CheckCircle2Icon} tint="bg-gradient-to-br from-emerald-500 to-teal-500" />
        <Stat label="Tekshirish kerak" value={t.review_required} hint="Ruxsat avtomatik aniqlanmagan endpointlar" icon={ShieldAlertIcon} tint="bg-gradient-to-br from-amber-500 to-orange-500" />
        <Stat label="24 soatda chaqirilgan" value={t.called_24h} hint="Haqiqiy so'rovlar jurnali asosida" icon={RadioIcon} tint="bg-gradient-to-br from-violet-600 to-fuchsia-500" />
      </div>

      <GlassCard className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-bold">Rollar bo&apos;yicha</h2>
          <p className="text-xs text-muted-foreground">Bitta endpoint bir nechta rolda bo&apos;lishi mumkin</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {data.roles.map(({ role, count }) => (
            <Link
              key={role}
              href={`/developer/${slugOf(role)}`}
              className="group flex flex-col gap-2 rounded-2xl border border-glass-border bg-muted/40 p-4 transition hover:border-cyan-400/40 hover:bg-muted/70"
            >
              <RoleBadge role={role} className="self-start" />
              <span className="text-2xl font-extrabold tabular-nums">{count}</span>
              <span className="text-xs text-muted-foreground group-hover:text-foreground">{ROLE_LABELS[role]} APIs →</span>
            </Link>
          ))}
        </div>
      </GlassCard>

      <div className="grid gap-5 lg:grid-cols-3">
        <GlassCard className="flex flex-col gap-3">
          <h2 className="flex items-center gap-2 text-base font-bold"><GitCompareArrowsIcon className="size-4" /> Kontrakt</h2>
          <Breakdown values={data.contract} labels={{ MATCHES_CONTRACT: "Kontraktga mos", NOT_IN_CONTRACT: "Kontraktda yo'q", CONTRACT_MISMATCH: "Farq qiladi", REVIEW_REQUIRED: "Tekshirish kerak" }} />
          <p className="text-xs text-muted-foreground">Rollar backend permission class&apos;laridan olinadi va CI&apos;da har bir rol bilan tekshiriladi.</p>
        </GlassCard>
        <GlassCard className="flex flex-col gap-3">
          <h2 className="flex items-center gap-2 text-base font-bold"><RadioIcon className="size-4" /> Holat (24 soat)</h2>
          <Breakdown values={data.health} labels={{ healthy: "Sog'lom", degraded: "Sekin", failing: "Xatoli", idle: "Chaqirilmagan" }} />
          <p className="text-xs text-muted-foreground">Hujjatlashtirilgan bo&apos;lishi endpoint ishlayotganini anglatmaydi.</p>
        </GlassCard>
        <GlassCard className="flex flex-col gap-3">
          <h2 className="flex items-center gap-2 text-base font-bold"><ClockIcon className="size-4" /> Oxirgi o&apos;zgarish</h2>
          {data.last_change ? <ChangeSummary entry={data.last_change} /> : <p className="text-sm text-muted-foreground">Changelog bo&apos;sh</p>}
          <div className="mt-auto flex flex-wrap gap-3 text-xs font-semibold">
            <Link href="/developer/changelog" className="text-brand hover:underline dark:text-cyan-300">Changelog →</Link>
            <a href={data.docs_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand hover:underline dark:text-cyan-300">
              <BookOpenIcon className="size-3.5" /> Swagger
            </a>
            <a href={data.schema_url} target="_blank" rel="noreferrer" className="text-brand hover:underline dark:text-cyan-300">OpenAPI schema</a>
          </div>
        </GlassCard>
      </div>

      <GlassCard className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 text-white"><SmartphoneIcon className="size-5" /></span>
          <div>
            <p className="font-bold">Mobil ilova dasturchilari uchun</p>
            <p className="text-xs text-muted-foreground">User va Studio mobil API — mavjud va rejalashtirilgan funksiyalar alohida.</p>
          </div>
        </div>
        <Link href="/developer/mobile" className="rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 px-4 py-2 text-sm font-semibold text-white shadow-lg">Mobile API →</Link>
      </GlassCard>
    </>
  );
}

function Breakdown({ values, labels }: { values: Partial<Record<string, number>>; labels: Record<string, string> }) {
  const total = Object.values(values).reduce<number>((a, b) => a + (b ?? 0), 0) || 1;
  return (
    <ul className="flex flex-col gap-2">
      {Object.entries(labels).map(([key, label]) => {
        const n = values[key] ?? 0;
        return (
          <li key={key} className="flex flex-col gap-1">
            <div className="flex justify-between text-xs"><span className="text-muted-foreground">{label}</span><b className="tabular-nums">{n}</b></div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <motion.div className="h-full rounded-full bg-gradient-to-r from-blue-600 to-cyan-500" initial={{ width: 0 }} animate={{ width: `${(n / total) * 100}%` }} transition={{ duration: 0.6 }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

// ------------------------------------------------------------- endpoints
export function RoleEndpoints({ role }: { role?: ApiRole }) {
  const { data, error, isPending, refetch } = useDevcenterEndpoints(role);
  return (
    <>
      {role && (
        <GlassCard className="flex flex-wrap items-center gap-3 p-4">
          <RoleBadge role={role} />
          <p className="text-sm text-muted-foreground">{ROLE_INTRO[role]}</p>
        </GlassCard>
      )}
      <EndpointsTab data={data} error={error} isPending={isPending} onRetry={() => refetch()} roleTabs={!role} />
    </>
  );
}

// ---------------------------------------------------------------- mobile
const FEATURE_STATUS: Record<MobileFeature["status"], { label: string; className: string }> = {
  AVAILABLE: { label: "Mavjud", className: "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300" },
  PLANNED: { label: "PLANNED", className: "bg-slate-500/12 text-slate-600 dark:text-slate-300" },
  INCOMPLETE: { label: "Endpoint yo'qolgan", className: "bg-red-500/12 text-red-700 dark:text-red-300" },
};

export function MobileGuideView() {
  const { data, error, isPending, refetch } = useMobileGuide();
  const [app, setApp] = useState<"user" | "studio">("user");
  if (isPending) return <Skeleton className="h-[420px] rounded-3xl" />;
  if (error || !data) return <GlassCard><ErrorState error={error} onRetry={() => refetch()} /></GlassCard>;
  const current = data.apps.find((a) => a.key === app) ?? data.apps[0];
  const available = current.features.filter((f) => f.status !== "PLANNED");
  const planned = current.features.filter((f) => f.status === "PLANNED");

  return (
    <>
      <AnimatedTabs
        layoutId="mobile-app-tab"
        value={app}
        onChange={setApp}
        tabs={data.apps.map((a) => ({ value: a.key, label: a.label, icon: SmartphoneIcon, count: a.features.filter((f) => f.status === "AVAILABLE").length }))}
      />
      <p className="px-1 text-xs text-muted-foreground">
        Barcha so&apos;rovlarda <code className="font-mono">X-Client: mobile</code> va <code className="font-mono">Authorization: Bearer &lt;ACCESS_TOKEN&gt;</code>. Tokenlar javob tanasida qaytadi.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {available.map((feature) => (
          <GlassCard key={feature.key} interactive className="flex flex-col gap-3 p-5">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-bold">{feature.label}</h3>
              <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-semibold", FEATURE_STATUS[feature.status].className)}>{FEATURE_STATUS[feature.status].label}</span>
            </div>
            <ul className="flex flex-col gap-1.5">
              {feature.operations.map((op) => (
                <li key={op.id} className="flex items-center gap-2">
                  <MethodBadge method={op.method} />
                  <span className="flex min-w-0 flex-1 flex-col">
                    <code className="truncate font-mono text-xs font-semibold">{op.path.replace("/api/v1", "")}</code>
                    <span className="truncate text-[11px] text-muted-foreground">{op.summary}</span>
                  </span>
                  <EndpointStatusBadge status={op.status} />
                </li>
              ))}
            </ul>
            {feature.missing_operations.length > 0 && (
              <p className="flex items-center gap-1.5 text-xs font-semibold text-red-600"><AlertTriangleIcon className="size-3.5" /> {feature.missing_operations.join(", ")}</p>
            )}
          </GlassCard>
        ))}
      </div>
      {planned.length > 0 && (
        <GlassCard className="flex flex-col gap-3 border-dashed">
          <h2 className="flex items-center gap-2 font-bold"><FileWarningIcon className="size-4" /> Rejalashtirilgan (hali API yo&apos;q)</h2>
          <p className="text-xs text-muted-foreground">Bu funksiyalar real endpoint emas — mobil ilovada hali ishlatib bo&apos;lmaydi.</p>
          <ul className="grid gap-2 sm:grid-cols-2">
            {planned.map((f) => (
              <li key={f.key} className="rounded-2xl bg-muted/50 p-3">
                <p className="text-sm font-semibold">{f.label} <span className={cn("ml-1 rounded-full px-1.5 text-[10px]", FEATURE_STATUS.PLANNED.className)}>PLANNED</span></p>
                <p className="text-xs text-muted-foreground">{f.planned}</p>
              </li>
            ))}
          </ul>
        </GlassCard>
      )}
    </>
  );
}

// -------------------------------------------------------------- changelog
function ChangeSummary({ entry }: { entry: ChangelogEntry }) {
  return (
    <div className="flex flex-col gap-1.5 text-sm">
      <p className="font-semibold">#{entry.revision} · {entry.date}</p>
      {entry.note && <p className="text-xs text-muted-foreground">{entry.note}</p>}
      <p className="flex flex-wrap gap-2 text-xs">
        <span className="text-emerald-600 dark:text-emerald-300">+{entry.added.length} qo&apos;shildi</span>
        <span className="text-red-600 dark:text-red-300">−{entry.removed.length} olib tashlandi</span>
        <span className="text-amber-600 dark:text-amber-300">~{Object.keys(entry.changed).length} o&apos;zgardi</span>
        {entry.breaking.length > 0 && <span className="font-bold text-red-600">{entry.breaking.length} breaking</span>}
      </p>
    </div>
  );
}

function OpList({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  if (!items.length) return null;
  return (
    <div className="flex flex-col gap-1">
      <p className={cn("text-xs font-bold", tone)}>{title} ({items.length})</p>
      <ul className="flex flex-col gap-0.5">
        {items.map((name) => {
          const [method, path] = name.split(" ");
          return (
            <li key={name} className="flex items-center gap-2">
              <MethodBadge method={method} />
              <code className="truncate font-mono text-xs">{path}</code>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function ChangelogView() {
  const { data, error, isPending, refetch } = useChangelog();
  if (isPending) return <Skeleton className="h-64 rounded-3xl" />;
  if (error || !data) return <GlassCard><ErrorState error={error} onRetry={() => refetch()} /></GlassCard>;
  if (!data.results.length) return <GlassCard><EmptyState title="Changelog bo'sh" description="`python manage.py api_contract --write` birinchi yozuvni yaratadi." /></GlassCard>;

  return (
    <>
      <p className="px-1 text-xs text-muted-foreground">
        Har bir yozuv — CI&apos;da ko&apos;rib chiqilgan kontrakt o&apos;zgarishi (<code className="font-mono">manage.py api_contract --write</code>). Breaking o&apos;zgarishlar yangi API versiyasini talab qilishi mumkin.
      </p>
      {data.results.map((entry) => (
        <GlassCard key={entry.revision} className="flex flex-col gap-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <ChangeSummary entry={entry} />
            {entry.breaking.length > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-red-500/12 px-2.5 py-1 text-xs font-bold text-red-600"><AlertTriangleIcon className="size-3.5" /> Breaking</span>
            )}
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <OpList title="Qo'shildi" items={entry.added} tone="text-emerald-600 dark:text-emerald-300" />
            <OpList title="Olib tashlandi" items={entry.removed} tone="text-red-600 dark:text-red-300" />
            <OpList title="Breaking" items={entry.breaking} tone="text-red-600 dark:text-red-300" />
            {Object.keys(entry.changed).length > 0 && (
              <div className="flex flex-col gap-1">
                <p className="text-xs font-bold text-amber-600 dark:text-amber-300">O&apos;zgardi ({Object.keys(entry.changed).length})</p>
                <ul className="flex flex-col gap-0.5 text-xs">
                  {Object.entries(entry.changed).map(([name, fields]) => (
                    <li key={name}><code className="font-mono">{name}</code> — <span className="text-muted-foreground">{fields.join(", ")}</span></li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </GlassCard>
      ))}
    </>
  );
}

