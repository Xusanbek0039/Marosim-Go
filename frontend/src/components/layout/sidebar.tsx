"use client";

import { ChevronsLeftIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { LogoMark, Wordmark } from "@/components/brand/logo";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useMe } from "@/features/auth/hooks";
import { cn } from "@/lib/utils";
import { duration, spring } from "@/motion/tokens";

import { NAV_ITEMS, canSee } from "./nav";

export const SIDEBAR_WIDTH = { expanded: 272, collapsed: 84 } as const;

function NavLinks({ collapsed, onNavigate, layoutGroup }: { collapsed: boolean; onNavigate?: () => void; layoutGroup: string }) {
  const pathname = usePathname();
  const { data: me } = useMe();
  const items = NAV_ITEMS.filter((item) => canSee(me, item));

  return (
    <nav aria-label="Asosiy menyu" className="flex flex-col gap-1.5">
      {!collapsed && (
        <p className="px-3.5 pb-1 text-[11px] font-bold tracking-[0.14em] text-muted-foreground uppercase">Boshqaruv</p>
      )}
      {items.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;
        const link = (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "group relative flex h-12 items-center gap-3 rounded-2xl px-3.5 text-sm font-semibold outline-none transition-colors focus-visible:ring-4 focus-visible:ring-brand/30",
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
            <motion.span
              className="relative z-10 inline-flex"
              whileHover={{ scale: 1.12, rotate: -4 }}
              transition={spring.pop}
            >
              <Icon className="size-5" aria-hidden />
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
          </Link>
        );
        return collapsed ? (
          <Tooltip key={item.href}>
            <TooltipTrigger asChild>{link}</TooltipTrigger>
            <TooltipContent side="right">{item.label}</TooltipContent>
          </Tooltip>
        ) : (
          link
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
          <span className="truncate text-xs text-muted-foreground">{me.email}</span>
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
