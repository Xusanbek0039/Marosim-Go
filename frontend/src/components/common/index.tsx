"use client";

import { AlertTriangleIcon, ChevronLeftIcon, ChevronRightIcon, InboxIcon, RotateCwIcon } from "lucide-react";
import { motion } from "motion/react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import type { Role } from "@/lib/api/types";
import { ROLE_LABELS, avatarGradient, formatNumber, initials } from "@/lib/format";
import { cn } from "@/lib/utils";
import { cardHover, fadeUp } from "@/motion/tokens";

// ---------------------------------------------------------------- surfaces
export function GlassCard({
  className,
  interactive,
  children,
  ...props
}: React.ComponentProps<typeof motion.div> & { interactive?: boolean }) {
  return (
    <motion.div
      variants={fadeUp}
      {...(interactive ? cardHover : {})}
      className={cn(
        "glass rounded-3xl p-5 transition-[border-color,box-shadow] duration-300 sm:p-6",
        interactive && "hover:border-cyan-400/35 hover:shadow-glow",
        className,
      )}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export function PageHeader({
  title,
  crumb,
  actions,
}: {
  title: string;
  crumb?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 px-1">
      <div className="flex flex-col gap-1">
        {crumb && <p className="text-sm text-muted-foreground">{crumb}</p>}
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">{title}</h1>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2.5">{actions}</div>}
    </header>
  );
}

// ------------------------------------------------------------------ people
export function UserAvatar({
  id,
  first,
  last,
  src,
  className,
  rounded = "full",
}: {
  id: string;
  first?: string;
  last?: string;
  src?: string | null;
  className?: string;
  rounded?: "full" | "2xl";
}) {
  const radius = rounded === "full" ? "rounded-full" : "rounded-2xl";
  return (
    <Avatar className={cn("size-10 shrink-0", radius, className)}>
      {src ? <AvatarImage src={src} alt="" className={cn("object-cover", radius)} /> : null}
      <AvatarFallback
        className={cn("bg-gradient-to-br font-bold text-white", radius, avatarGradient(id))}
        aria-hidden
      >
        {initials(first, last)}
      </AvatarFallback>
    </Avatar>
  );
}

const ROLE_STYLES: Record<Role, string> = {
  SUPER_ADMIN: "bg-violet-500/14 text-violet-700 dark:text-violet-300",
  ADMIN: "bg-blue-500/14 text-blue-700 dark:text-blue-300",
  STUDIO: "bg-cyan-500/14 text-cyan-800 dark:text-cyan-300",
  USER: "bg-slate-500/12 text-slate-700 dark:text-slate-300",
};

export function RoleBadge({ role }: { role: Role }) {
  return (
    <span className={cn("inline-flex h-6 items-center rounded-full px-2.5 text-xs font-bold", ROLE_STYLES[role])}>
      {ROLE_LABELS[role]}
    </span>
  );
}

export function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-[13px] font-semibold",
        active ? "text-success" : "text-warning",
      )}
    >
      <span className={cn("size-1.5 rounded-full", active ? "bg-success" : "bg-warning")} aria-hidden />
      {active ? "Faol" : "Nofaol"}
    </span>
  );
}

// ----------------------------------------------------------------- states
export function EmptyState({
  title = "Hech narsa topilmadi",
  description,
  action,
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <motion.div variants={fadeUp} initial="initial" animate="animate" className="flex flex-col items-center gap-3 px-6 py-16 text-center">
      <div className="flex size-16 items-center justify-center rounded-3xl bg-gradient-to-br from-blue-500/15 to-cyan-400/15 text-cyan-600 dark:text-cyan-300">
        <InboxIcon className="size-7" aria-hidden />
      </div>
      <h3 className="text-lg font-bold">{title}</h3>
      {description && <p className="max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action}
    </motion.div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message =
    error instanceof ApiError ? error.message : "Ma'lumotlarni yuklab bo'lmadi. Birozdan so'ng qayta urinib ko'ring.";
  return (
    <motion.div
      variants={fadeUp}
      initial="initial"
      animate="animate"
      role="alert"
      className="flex flex-col items-center gap-3 px-6 py-14 text-center"
    >
      <div className="flex size-16 items-center justify-center rounded-3xl bg-red-500/12 text-red-600 dark:text-red-400">
        <AlertTriangleIcon className="size-7" aria-hidden />
      </div>
      <h3 className="text-lg font-bold">Xatolik yuz berdi</h3>
      <p className="max-w-sm text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          <RotateCwIcon /> Qayta urinish
        </Button>
      )}
    </motion.div>
  );
}

export function RowsSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-1" aria-busy="true" aria-label="Yuklanmoqda">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 border-t border-border/60 px-3 py-3.5 first:border-t-0">
          <Skeleton className="size-10 rounded-full" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-3 w-1/4" />
          </div>
          <Skeleton className="hidden h-6 w-20 rounded-full sm:block" />
          <Skeleton className="hidden h-3.5 w-24 md:block" />
        </div>
      ))}
    </div>
  );
}

export function CardsSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(270px,1fr))] gap-5" aria-busy="true" aria-label="Yuklanmoqda">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass flex flex-col gap-4 rounded-3xl p-5">
          <div className="flex items-center gap-3">
            <Skeleton className="size-12 rounded-2xl" />
            <div className="flex flex-1 flex-col gap-2">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-8 w-full rounded-xl" />
        </div>
      ))}
    </div>
  );
}

// -------------------------------------------------------------- pagination
export function Pagination({
  page,
  totalPages,
  count,
  pageSize,
  onPage,
}: {
  page: number;
  totalPages: number;
  count: number;
  pageSize: number;
  onPage: (page: number) => void;
}) {
  if (count === 0) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, count);
  const pages = pageWindow(page, totalPages);
  return (
    <nav aria-label="Sahifalash" className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
      <span>
        {formatNumber(from)}–{formatNumber(to)} / {formatNumber(count)} ta natija
      </span>
      <div className="flex items-center gap-1.5">
        <Button variant="outline" size="icon-sm" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Oldingi sahifa">
          <ChevronLeftIcon />
        </Button>
        {pages.map((p, i) =>
          p === "…" ? (
            <span key={`gap-${i}`} className="px-1.5">
              …
            </span>
          ) : (
            <Button
              key={p}
              size="icon-sm"
              variant={p === page ? "default" : "ghost"}
              onClick={() => onPage(p)}
              aria-current={p === page ? "page" : undefined}
              className="tabular-nums"
            >
              {p}
            </Button>
          ),
        )}
        <Button
          variant="outline"
          size="icon-sm"
          disabled={page >= totalPages}
          onClick={() => onPage(page + 1)}
          aria-label="Keyingi sahifa"
        >
          <ChevronRightIcon />
        </Button>
      </div>
    </nav>
  );
}

function pageWindow(page: number, total: number): (number | "…")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const set = new Set([1, total, page - 1, page, page + 1]);
  const sorted = [...set].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b);
  const out: (number | "…")[] = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) out.push("…");
    out.push(p);
  });
  return out;
}
