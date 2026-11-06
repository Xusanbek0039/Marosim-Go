"use client";

import { ActivityIcon, ShieldCheckIcon, TrendingUpIcon, UsersIcon, VideoIcon, type LucideIcon } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";

import { EmptyState, ErrorState, GlassCard, PageHeader, RoleBadge, StatusBadge, UserAvatar } from "@/components/common";
import { AnimatedNumber } from "@/components/motion/animated-number";
import { PageTransition } from "@/components/motion/page-transition";
import { RequirePermission } from "@/components/layout/require-permission";
import { Skeleton } from "@/components/ui/skeleton";
import { useCan } from "@/features/auth/hooks";
import { useDashboardOverview } from "@/features/resources";
import { formatDate, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import { listContainer, spring, stagger } from "@/motion/tokens";

interface Stat {
  label: string;
  value: number;
  hint: string;
  icon: LucideIcon;
  tint: string;
}

function StatCard({ stat }: { stat: Stat }) {
  const Icon = stat.icon;
  return (
    <GlassCard interactive className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-[13px] font-semibold text-muted-foreground">{stat.label}</p>
        <span className={cn("flex size-10 items-center justify-center rounded-xl text-white shadow-lg", stat.tint)}>
          <Icon className="size-5" aria-hidden />
        </span>
      </div>
      <AnimatedNumber value={stat.value} className="text-4xl font-extrabold tracking-tight tabular-nums" />
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <TrendingUpIcon className="size-3.5 text-success" aria-hidden />
        {stat.hint}
      </p>
    </GlassCard>
  );
}

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-5">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="glass flex flex-col gap-4 rounded-3xl p-6">
          <Skeleton className="h-3.5 w-1/2" />
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      ))}
    </div>
  );
}

function DashboardContent() {
  const { data, error, isPending, refetch } = useDashboardOverview();
  const can = useCan();

  if (isPending) {
    return (
      <>
        <StatsSkeleton />
        <div className="glass h-80 rounded-3xl" />
      </>
    );
  }
  if (error) return <GlassCard><ErrorState error={error} onRetry={() => refetch()} /></GlassCard>;

  const t = data.totals;
  const stats: Stat[] = [
    {
      label: "Umumiy foydalanuvchilar",
      value: t.users,
      hint: `oxirgi 30 kunda +${formatNumber(t.new_users_30d)}`,
      icon: UsersIcon,
      tint: "bg-gradient-to-br from-blue-600 to-blue-400",
    },
    {
      label: "Adminlar",
      value: t.admins,
      hint: "panelga kirish huquqi bor",
      icon: ShieldCheckIcon,
      tint: "bg-gradient-to-br from-indigo-600 to-blue-500",
    },
    {
      label: "Studiyalar",
      value: t.studios,
      hint: `${formatNumber(t.active_studios)} tasi faol`,
      icon: VideoIcon,
      tint: "bg-gradient-to-br from-cyan-600 to-cyan-400",
    },
    {
      label: "Faol foydalanuvchilar",
      value: t.active_users,
      hint: t.users ? `umumiydan ${Math.round((t.active_users / t.users) * 100)}%` : "hali foydalanuvchi yo'q",
      icon: ActivityIcon,
      tint: "bg-gradient-to-br from-teal-600 to-cyan-500",
    },
  ];
  const maxRole = Math.max(1, ...data.role_distribution.map((r) => r.count));

  return (
    <>
      <motion.section
        variants={listContainer(stagger.cards)}
        initial="initial"
        animate="animate"
        className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-5"
      >
        {stats.map((s) => (
          <StatCard key={s.label} stat={s} />
        ))}
      </motion.section>

      <motion.section
        variants={listContainer(stagger.cards)}
        initial="initial"
        animate="animate"
        className="flex flex-wrap items-stretch gap-5"
      >
        <GlassCard className="flex min-w-0 flex-[999_1_520px] flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-bold">Oxirgi qo&apos;shilgan profillar</h2>
            {can("users.view") && (
              <Link href="/users" className="text-sm font-semibold text-brand hover:underline dark:text-cyan-300">
                Barchasi →
              </Link>
            )}
          </div>
          {data.recent_profiles.length === 0 ? (
            <EmptyState
              title={can("users.view") ? "Hali profillar yo'q" : "Profillarni ko'rish uchun ruxsat yo'q"}
              description={can("users.view") ? "Yangi foydalanuvchi qo'shilganda shu yerda ko'rinadi." : undefined}
            />
          ) : (
            <motion.ul variants={listContainer()} initial="initial" animate="animate" className="flex flex-col">
              {data.recent_profiles.map((p) => (
                <motion.li
                  key={p.id}
                  variants={{ initial: { opacity: 0, x: -8 }, animate: { opacity: 1, x: 0, transition: spring.soft } }}
                  className="flex items-center gap-3 rounded-2xl border-t border-border/60 px-2 py-3 transition-colors first:border-t-0 hover:bg-muted/60"
                >
                  <UserAvatar id={p.id} first={p.first_name} last={p.last_name} src={p.profile_picture} />
                  <div className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate text-sm font-semibold">{p.full_name}</span>
                    <span className="truncate text-xs text-muted-foreground">{p.email}</span>
                  </div>
                  <span className="hidden sm:inline-flex">
                    <RoleBadge role={p.role} />
                  </span>
                  <span className="hidden w-20 md:inline-flex">
                    <StatusBadge active={p.is_active} />
                  </span>
                  <span className="hidden w-24 text-right text-xs text-muted-foreground tabular-nums lg:block">
                    {formatDate(p.created_at)}
                  </span>
                </motion.li>
              ))}
            </motion.ul>
          )}
        </GlassCard>

        <GlassCard className="flex flex-[1_1_300px] flex-col gap-5">
          <h2 className="text-lg font-bold">Rollar taqsimoti</h2>
          {data.role_distribution.map((r) => (
            <div key={r.role} className="flex flex-col gap-2">
              <div className="flex justify-between text-sm">
                <span className="font-semibold">{r.label}</span>
                <span className="text-muted-foreground tabular-nums">{formatNumber(r.count)}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-blue-600 to-cyan-400"
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.max(3, (r.count / maxRole) * 100)}%` }}
                  transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
                />
              </div>
            </div>
          ))}
          <div className="mt-auto grid grid-cols-2 gap-3 pt-2">
            <div className="rounded-2xl bg-muted/70 p-3.5">
              <p className="text-xs text-muted-foreground">Nofaol hisoblar</p>
              <p className="text-xl font-extrabold tabular-nums">{formatNumber(t.inactive_users)}</p>
            </div>
            <div className="rounded-2xl bg-muted/70 p-3.5">
              <p className="text-xs text-muted-foreground">Yangi (30 kun)</p>
              <p className="text-xl font-extrabold tabular-nums">{formatNumber(t.new_users_30d)}</p>
            </div>
          </div>
        </GlassCard>
      </motion.section>
    </>
  );
}

export default function DashboardPage() {
  return (
    <RequirePermission requires="dashboard.view">
      <PageTransition>
        <PageHeader title="Dashboard" crumb="Umumiy ko'rinish" />
        <DashboardContent />
      </PageTransition>
    </RequirePermission>
  );
}
