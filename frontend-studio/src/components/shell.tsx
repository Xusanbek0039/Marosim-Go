"use client";

import { LogOutIcon, MoonIcon, SunIcon, UserIcon } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";
import { toast } from "sonner";

import { PaidBadge } from "./paid-badge";

import { APP } from "@/lib/app-config";
import { useLogout, useMe } from "@/lib/auth";

import { Avatar, cn } from "./ui";

const useMounted = () =>
  useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      {/* eslint-disable-next-line @next/next/no-img-element -- static brand asset */}
      <img src="/brand/logo-icon.png" alt="" className="h-8 w-auto" />
      <span className="hidden text-lg font-extrabold tracking-tight min-[380px]:inline">
        Marosim<span className="text-accent">Go</span>
      </span>
    </span>
  );
}

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useMounted();
  const dark = mounted && resolvedTheme === "dark";
  return (
    <button
      type="button"
      onClick={() => setTheme(dark ? "light" : "dark")}
      aria-label={dark ? "Yorug' rejim" : "Qorong'i rejim"}
      className="glass inline-flex size-10 items-center justify-center rounded-xl text-muted-foreground transition hover:text-foreground"
    >
      {mounted && (dark ? <SunIcon className="size-4" /> : <MoonIcon className="size-4" />)}
    </button>
  );
}

export interface NavLink {
  href: string;
  label: string;
}

/** Simple top bar + centered content column — deliberately lighter than the admin panel. */
export function Shell({ nav, children }: { nav: NavLink[]; children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: me } = useMe();
  const logout = useLogout();

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-5xl flex-col gap-6 px-4 pt-4 pb-12 sm:px-6">
      <header className="glass sticky top-3 z-40 flex items-center gap-3 rounded-2xl px-3 py-2.5 sm:px-4">
        <Link href={APP.home} aria-label={`${APP.name} — bosh sahifa`}>
          <Logo />
        </Link>
        <nav aria-label="Asosiy menyu" className="ml-2 hidden items-center gap-1 lg:flex">
          {nav.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative rounded-xl px-3 py-2 text-sm font-semibold transition-colors",
                  active ? "text-white" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {active && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-xl brand-gradient"
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                )}
                <span className="relative">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <Link href="/profile" className="flex items-center gap-2 rounded-xl p-1 pr-2 hover:bg-muted" aria-label="Profil">
            {me ? <Avatar first={me.first_name} last={me.last_name} src={me.profile_picture} className="size-8 text-xs" /> : <UserIcon className="size-5" />}
            <span className="hidden max-w-32 truncate text-sm font-semibold md:inline">{me?.first_name || "Profil"} <PaidBadge verified={me?.is_verified} /></span>
          </Link>
          <button
            type="button"
            aria-label="Chiqish"
            className="inline-flex size-10 items-center justify-center rounded-xl text-muted-foreground hover:bg-muted hover:text-foreground"
            onClick={() =>
              logout.mutate(undefined, {
                onSettled: () => {
                  toast.success("Tizimdan chiqdingiz");
                  router.replace("/login");
                },
              })
            }
          >
            <LogOutIcon className="size-4" />
          </button>
        </div>
      </header>
      {nav.length > 1 && (
        <nav aria-label="Mobil menyu" className="glass flex gap-1 overflow-x-auto rounded-2xl p-1 lg:hidden">
          {nav.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn("min-w-max flex-1 rounded-xl px-3 py-2 text-center text-sm font-semibold", active ? "brand-gradient text-white" : "text-muted-foreground")}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      )}
      <main className="flex flex-col gap-5">{children}</main>
    </div>
  );
}

export function PageTitle({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 px-1">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}
