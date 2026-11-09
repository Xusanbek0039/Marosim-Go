"use client";

import { ChevronDownIcon, ChevronsLeftIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { LogoMark, Wordmark } from "@/components/brand/logo";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useCan, useMe } from "@/features/auth/hooks";
import { useRequestsSummary } from "@/features/requests/api";
import { useMySummary, useStaffSummary } from "@/features/support/api";
import { formatPhone } from "@/lib/format";
import { cn } from "@/lib/utils";
import { duration, spring } from "@/motion/tokens";

import { NAV_SECTIONS, type NavItem, canSee, isActive } from "./nav";

export const SIDEBAR_WIDTH = { expanded: 272, collapsed: 84 } as const;

function CountPill({ count, collapsed, label }: { count?: number; collapsed: boolean; label: string }) {
  if (!count) return null;
  return (
    <span
      aria-label={`${count} ta ${label}`}
      className={cn(
        "z-10 inline-flex min-w-5 items-center justify-center rounded-full bg-amber-500 px-1.5 text-[11px] font-bold leading-5 text-white tabular-nums",
        collapsed ? "absolute top-1 right-1" : "relative ml-auto",
      )}
    >
      {count > 99 ? "99+" : count}
    </span>
  );
}

function RequestsCount({ collapsed }: { collapsed: boolean }) {
  const { data } = useRequestsSummary();
  return <CountPill count={data?.pending} collapsed={collapsed} label="kutilayotgan so'rov" />;
}

/** Staff: tickets waiting for an answer; an admin without `support.view`: answers to their own tickets. */
function SupportCount({ collapsed }: { collapsed: boolean }) {
  const { data: me } = useMe();
  const can = useCan();
  const staff = me?.role === "SUPER_ADMIN" || can("support.view");
  const inbox = useStaffSummary(staff);
  const mine = useMySummary(!staff && me?.role === "ADMIN");
  return staff ? (
    <CountPill count={inbox.data?.open} collapsed={collapsed} label="javob kutayotgan xat" />
  ) : (
    <CountPill count={mine.data?.answered} collapsed={collapsed} label="javob kelgan xat" />
  );
}

function NavLink({
  item,
  collapsed,
  active,
  onNavigate,
  layoutGroup,
  compact,
}: {
  item: NavItem;
  collapsed: boolean;
  active: boolean;
  onNavigate?: () => void;
  layoutGroup: string;
  compact?: boolean;
}) {
  const Icon = item.icon;
  const link = (
    <Link
      href={item.href}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group relative flex shrink-0 items-center gap-3 rounded-2xl px-3.5 text-sm font-semibold outline-none transition-colors focus-visible:ring-4 focus-visible:ring-brand/30",
        compact ? "h-10" : "h-12",
        collapsed && "justify-center px-0",
        active ? "text-white" : "text-muted-foreground hover:bg-muted hover:text-foreground",
      )}
    >
      {active && (
        <motion.span
          layoutId={`nav-active-${layoutGroup}`}
          className="absolute inset-0 rounded-2xl bg-gradient-to-r from-blue-600 to-cyan-600 shadow-[0_10px_30px_-12px_rgb(6_182_212/0.75)]"
          transition={spring.sidebar}
          aria-hidden
        />
      )}
      <motion.span className="relative z-10 inline-flex" whileHover={{ scale: 1.12, rotate: -4 }} transition={spring.pop}>
        <Icon className={compact ? "size-[18px]" : "size-5"} aria-hidden />
      </motion.span>
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.span
            className="relative z-10 whitespace-nowrap"
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0, transition: { delay: 0.06, duration: duration.base } }}
            exit={{ opacity: 0, x: -6, transition: { duration: duration.fast } }}
          >
            {item.label}
          </motion.span>
        )}
      </AnimatePresence>
      {item.badge === "requests" && <RequestsCount collapsed={collapsed} />}
      {item.badge === "support" && <SupportCount collapsed={collapsed} />}
    </Link>
  );
  return collapsed ? (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      <TooltipContent side="right">{item.label}</TooltipContent>
    </Tooltip>
  ) : (
    link
  );
}

function NavLinks({ collapsed, onNavigate, layoutGroup }: { collapsed: boolean; onNavigate?: () => void; layoutGroup: string }) {
  const pathname = usePathname();
  const { data: me } = useMe();
  const [closed, setClosed] = useState<Set<string>>(new Set());
  const sections = NAV_SECTIONS.map((s) => ({ ...s, items: s.items.filter((item) => canSee(me, item)) })).filter(
    (s) => s.items.length > 0,
  );

  return (
    <nav aria-label="Asosiy menyu" className="-mx-1 flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-1">
      {sections.map((section) => {
        const hasActive = section.items.some((item) => isActive(pathname, item));
        // A collapsible group stays open while one of its pages is shown.
        const open = !section.collapsible || collapsed || hasActive || !closed.has(section.key);
        const toggle = () =>
          setClosed((prev) => {
            const next = new Set(prev);
            if (next.has(section.key)) next.delete(section.key);
            else next.add(section.key);
            return next;
          });
        return (
          <div key={section.key} className="flex flex-col gap-1.5">
            {!collapsed &&
              (section.collapsible ? (
                <button
                  type="button"
                  onClick={toggle}
                  aria-expanded={open}
                  disabled={hasActive}
                  className="flex items-center justify-between rounded-lg px-3.5 pb-1 text-[11px] font-bold tracking-[0.14em] text-muted-foreground uppercase outline-none hover:text-foreground focus-visible:ring-4 focus-visible:ring-brand/25 disabled:cursor-default disabled:hover:text-muted-foreground"
                >
                  {section.title}
                  <motion.span animate={{ rotate: open ? 0 : -90 }} transition={spring.sidebar} className="inline-flex">
                    <ChevronDownIcon className="size-3.5" aria-hidden />
                  </motion.span>
                </button>
              ) : (
                <p className="px-3.5 pb-1 text-[11px] font-bold tracking-[0.14em] text-muted-foreground uppercase">
                  {section.title}
                </p>
              ))}
            {collapsed && section.collapsible && <span className="mx-auto h-px w-8 bg-border" aria-hidden />}
            <AnimatePresence initial={false}>
              {open && (
                <motion.div
                  key="items"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={spring.sidebar}
                  className="flex flex-col gap-1.5 overflow-hidden"
                >
                  {section.items.map((item) => (
                    <NavLink
                      key={item.href}
                      item={item}
                      collapsed={collapsed}
                      active={isActive(pathname, item)}
                      onNavigate={onNavigate}
                      layoutGroup={layoutGroup}
                      compact={section.collapsible}
                    />
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </nav>
  );
}

function ProfileChip({ collapsed }: { collapsed: boolean }) {
  const { data: me } = useMe();
  if (!me) return null;
  return (
    <Link
      href="/settings"
      className={cn(
        "flex items-center gap-3 rounded-2xl border border-glass-border bg-muted/60 p-2.5 transition hover:border-cyan-400/35",
        collapsed && "justify-center p-2",
      )}
    >
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 text-sm font-bold text-white">
        {(me.first_name[0] ?? "") + (me.last_name[0] ?? "")}
      </span>
      {!collapsed && (
        <span className="flex min-w-0 flex-col">
          <span className="truncate text-sm font-bold">{me.full_name}</span>
          <span className="truncate text-xs text-muted-foreground tabular-nums">{formatPhone(me.phone_number)}</span>
        </span>
      )}
    </Link>
  );
}

export function DesktopSidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? SIDEBAR_WIDTH.collapsed : SIDEBAR_WIDTH.expanded }}
      transition={spring.sidebar}
      className="glass sticky top-4 hidden h-[calc(100dvh-2rem)] shrink-0 flex-col gap-6 overflow-hidden rounded-[28px] px-3 py-5 lg:flex"
    >
      <div className={cn("flex items-center gap-2.5 px-1.5", collapsed ? "flex-col" : "justify-between")}>
        <Link href="/dashboard" className="flex min-w-0 items-center gap-2.5" aria-label="MarosimGo — Dashboard">
          <LogoMark className="h-9" />
          <AnimatePresence initial={false}>
            {!collapsed && (
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-[22px]">
                <Wordmark className="h-full" />
              </motion.span>
            )}
          </AnimatePresence>
        </Link>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              onClick={onToggle}
              aria-label={collapsed ? "Menyuni ochish" : "Menyuni yig'ish"}
              aria-expanded={!collapsed}
              className="inline-flex size-9 shrink-0 items-center justify-center rounded-xl border border-glass-border text-muted-foreground transition hover:bg-muted hover:text-foreground active:scale-95"
            >
              <motion.span animate={{ rotate: collapsed ? 180 : 0 }} transition={spring.sidebar} className="inline-flex">
                <ChevronsLeftIcon className="size-4" />
              </motion.span>
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">{collapsed ? "Ochish" : "Yig'ish"}</TooltipContent>
        </Tooltip>
      </div>
      <NavLinks collapsed={collapsed} layoutGroup="desktop" />
      <div className="mt-auto">
        <ProfileChip collapsed={collapsed} />
      </div>
    </motion.aside>
  );
}

export function MobileNav({ onNavigate }: { onNavigate: () => void }) {
  return (
    <div className="flex h-full flex-col gap-6">
      <div className="flex items-center gap-2.5 px-1.5">
        <LogoMark className="h-9" />
        <Wordmark className="h-[22px]" />
      </div>
      <NavLinks collapsed={false} onNavigate={onNavigate} layoutGroup="mobile" />
      <div className="mt-auto">
        <ProfileChip collapsed={false} />
      </div>
    </div>
  );
}
