"use client";

import { LogOutIcon, MenuIcon, Settings2Icon, ShieldAlertIcon, XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Dialog as DialogPrimitive } from "radix-ui";
import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { toast } from "sonner";

import { LogoMark } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { isPanelRole, panelAudienceMessage, useLogout, useMe } from "@/features/auth/hooks";
import { ApiError, setSessionExpiredHandler } from "@/lib/api/client";
import { ROLE_LABELS } from "@/lib/format";
import { ease, overlayVariants } from "@/motion/tokens";

import { DesktopSidebar, MobileNav } from "./sidebar";
import { ThemeToggle } from "./theme-toggle";

// ------------------------------------------------------- collapsed preference
const COLLAPSE_KEY = "mg:sidebar-collapsed";
const collapseListeners = new Set<() => void>();
function readCollapsed() {
  try {
    return window.localStorage.getItem(COLLAPSE_KEY) === "1";
  } catch {
    return false;
  }
}
function useCollapsed() {
  const collapsed = useSyncExternalStore(
    (l) => {
      collapseListeners.add(l);
      return () => collapseListeners.delete(l);
    },
    readCollapsed,
    () => false,
  );
  const toggle = useCallback(() => {
    try {
      window.localStorage.setItem(COLLAPSE_KEY, readCollapsed() ? "0" : "1");
    } catch {
      /* ignore */
    }
    collapseListeners.forEach((l) => l());
  }, []);
  return [collapsed, toggle] as const;
}

// ------------------------------------------------------------------ pieces
function FullScreenLoader() {
  return (
    <div className="flex min-h-dvh items-center justify-center" aria-busy="true" aria-label="Yuklanmoqda">
      <motion.div
        animate={{ scale: [1, 1.08, 1], opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
      >
        <LogoMark className="h-16" />
      </motion.div>
    </div>
  );
}

function Forbidden({ onLogout }: { onLogout: () => void }) {
  return (
    <div className="flex min-h-dvh items-center justify-center p-4">
      <div className="glass flex max-w-md flex-col items-center gap-4 rounded-3xl p-8 text-center">
        <ShieldAlertIcon className="size-12 text-amber-500" aria-hidden />
        <h1 className="text-xl font-extrabold">Panelga kirish taqiqlangan</h1>
        <p className="text-sm text-muted-foreground">
          {panelAudienceMessage}
        </p>
        <Button onClick={onLogout}>
          <LogOutIcon /> Chiqish
        </Button>
      </div>
    </div>
  );
}

function UserMenu({ onLogout }: { onLogout: () => void }) {
  const { data: me } = useMe();
  if (!me) return null;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex size-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 text-sm font-bold text-white ring-2 ring-transparent transition hover:ring-cyan-400/50 focus-visible:ring-cyan-400 focus-visible:outline-none"
          aria-label="Profil menyusi"
        >
          {(me.first_name[0] ?? "") + (me.last_name[0] ?? "")}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          <span className="font-bold">{me.full_name}</span>
          <span className="text-xs font-normal text-muted-foreground">{ROLE_LABELS[me.role]}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/settings">
            <Settings2Icon /> Sozlamalar
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem variant="destructive" onSelect={onLogout}>
          <LogOutIcon /> Chiqish
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// ------------------------------------------------------------------- shell
export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: me, error, isPending } = useMe();
  const logout = useLogout();
  const [collapsed, toggleCollapsed] = useCollapsed();
  const [mobileOpen, setMobileOpen] = useState(false);

  const goToLogin = useCallback(() => {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    router.replace(`/login?next=${next}`);
  }, [router]);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      toast.error("Sessiya tugadi. Iltimos, qayta kiring.");
      goToLogin();
    });
  }, [goToLogin]);

  useEffect(() => {
    if (error instanceof ApiError && error.status === 401) goToLogin();
  }, [error, goToLogin]);

  const handleLogout = useCallback(() => {
    logout.mutate(undefined, {
      onSettled: () => {
        toast.success("Tizimdan chiqdingiz");
        router.replace("/login");
      },
    });
  }, [logout, router]);

  if (isPending || (error instanceof ApiError && error.status === 401)) return <FullScreenLoader />;
  if (!me) return <FullScreenLoader />;
  if (!isPanelRole(me.role)) return <Forbidden onLogout={handleLogout} />;

  return (
    <div className="flex min-h-dvh gap-5 p-3 sm:p-4">
      <DesktopSidebar collapsed={collapsed} onToggle={toggleCollapsed} />

      <DialogPrimitive.Root open={mobileOpen} onOpenChange={setMobileOpen}>
        <AnimatePresence>
          {mobileOpen && (
            <DialogPrimitive.Portal forceMount>
              <DialogPrimitive.Overlay asChild forceMount>
                <motion.div
                  className="fixed inset-0 z-50 bg-slate-950/50 backdrop-blur-sm lg:hidden"
                  variants={overlayVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                />
              </DialogPrimitive.Overlay>
              <DialogPrimitive.Content asChild forceMount>
                <motion.aside
                  initial={{ x: "-100%" }}
                  animate={{ x: 0, transition: { duration: 0.36, ease: ease.emphasized } }}
                  exit={{ x: "-100%", transition: { duration: 0.22, ease: ease.exit } }}
                  className="glass-strong fixed inset-y-3 left-3 z-50 w-[min(300px,calc(100vw-1.5rem))] rounded-[28px] p-4 outline-none lg:hidden"
                >
                  <DialogPrimitive.Title className="sr-only">Menyu</DialogPrimitive.Title>
                  <DialogPrimitive.Description className="sr-only">Asosiy navigatsiya</DialogPrimitive.Description>
                  <DialogPrimitive.Close
                    className="absolute top-4 right-4 inline-flex size-9 items-center justify-center rounded-xl text-muted-foreground hover:bg-muted"
                    aria-label="Menyuni yopish"
                  >
                    <XIcon className="size-4" />
                  </DialogPrimitive.Close>
                  <MobileNav onNavigate={() => setMobileOpen(false)} />
                </motion.aside>
              </DialogPrimitive.Content>
            </DialogPrimitive.Portal>
          )}
        </AnimatePresence>
      </DialogPrimitive.Root>

      <div className="flex min-w-0 flex-1 flex-col gap-5">
        <header className="flex items-center justify-between gap-3 px-1 pt-1">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon"
              className="lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Menyuni ochish"
            >
              <MenuIcon />
            </Button>
            <p className="hidden text-sm text-muted-foreground sm:block">
              Xush kelibsiz, <span className="font-semibold text-foreground">{me.first_name}</span>
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            <ThemeToggle />
            <UserMenu onLogout={handleLogout} />
          </div>
        </header>
        <main key={pathname} className="min-w-0 pb-8">
          {children}
        </main>
      </div>
    </div>
  );
}
