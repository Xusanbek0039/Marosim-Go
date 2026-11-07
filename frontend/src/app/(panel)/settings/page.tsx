"use client";

import { LaptopIcon, LogOutIcon, MoonIcon, SunIcon, type LucideIcon } from "lucide-react";
import { motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";
import { toast } from "sonner";

import { GlassCard, PageHeader, RoleBadge, UserAvatar } from "@/components/common";
import { useThemeSwitch } from "@/components/layout/theme-toggle";
import { PageTransition } from "@/components/motion/page-transition";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { useLogout, useMe } from "@/features/auth/hooks";
import { formatDate, formatDateTime, formatPhone } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useMotionPreference } from "@/motion/preference";
import { listContainer, spring, stagger } from "@/motion/tokens";

const THEMES: { value: string; label: string; icon: LucideIcon }[] = [
  { value: "light", label: "Yorug'", icon: SunIcon },
  { value: "dark", label: "Qorong'i", icon: MoonIcon },
  { value: "system", label: "Tizim", icon: LaptopIcon },
];

const useMounted = () =>
  useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

export default function SettingsPage() {
  const { data: me } = useMe();
  const { theme } = useTheme();
  const mounted = useMounted();
  const switchTheme = useThemeSwitch();
  const { userReduced, setUserReduced } = useMotionPreference();
  const logout = useLogout();
  const router = useRouter();

  if (!me) return null;

  return (
    <PageTransition>
      <PageHeader title="Sozlamalar" crumb="Profil va interfeys" />
      <motion.div
        variants={listContainer(stagger.cards)}
        initial="initial"
        animate="animate"
        className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]"
      >
        <GlassCard className="flex flex-col gap-5">
          <div className="flex items-center gap-4">
            <UserAvatar id={me.id} first={me.first_name} last={me.last_name} src={me.profile_picture} className="size-16 text-lg" />
            <div className="flex min-w-0 flex-col gap-1">
              <h2 className="truncate text-lg font-bold">{me.full_name}</h2>
              <RoleBadge role={me.role} />
            </div>
          </div>
          <dl className="rounded-2xl border border-glass-border bg-muted/40 px-4 text-sm">
            {[
              ["Telefon", formatPhone(me.phone_number)],
              ["Email", me.email || "—"],
              ["JSHSHIR", me.pinfl_masked ?? "—"],
              ["Oxirgi kirish", formatDateTime(me.last_login)],
              ["Hisob yaratilgan", formatDate(me.created_at)],
              ["Ruxsatlar", me.role === "SUPER_ADMIN" ? "To'liq" : `${me.permissions.length} ta`],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4 border-b border-border/70 py-3 last:border-b-0">
                <dt className="text-muted-foreground">{k}</dt>
                <dd className="text-right font-medium tabular-nums">{v}</dd>
              </div>
            ))}
          </dl>
          <Button
            variant="outline"
            className="text-destructive"
            onClick={() =>
              logout.mutate(undefined, {
                onSettled: () => {
                  toast.success("Tizimdan chiqdingiz");
                  router.replace("/login");
                },
              })
            }
          >
            <LogOutIcon /> Tizimdan chiqish
          </Button>
        </GlassCard>

        <GlassCard className="flex flex-col gap-6">
          <section className="flex flex-col gap-3">
            <h2 className="text-lg font-bold">Mavzu</h2>
            <div className="grid grid-cols-3 gap-3" role="radiogroup" aria-label="Mavzu">
              {THEMES.map(({ value, label, icon: Icon }) => {
                const active = mounted && theme === value;
                return (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={(e) => {
                      const r = e.currentTarget.getBoundingClientRect();
                      switchTheme(value, { x: r.left + r.width / 2, y: r.top + r.height / 2 });
                    }}
                    className={cn(
                      "relative flex flex-col items-center gap-2 rounded-2xl border p-4 text-sm font-semibold transition",
                      active ? "border-transparent text-white" : "border-glass-border hover:bg-muted",
                    )}
                  >
                    {active && (
                      <motion.span
                        layoutId="theme-active"
                        transition={spring.sidebar}
                        className="absolute inset-0 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-600"
                        aria-hidden
                      />
                    )}
                    <Icon className="relative size-5" aria-hidden />
                    <span className="relative">{label}</span>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="flex flex-col gap-3">
            <h2 className="text-lg font-bold">Animatsiyalar</h2>
            <label className="flex items-center justify-between gap-4 rounded-2xl bg-muted/60 px-4 py-3.5">
              <span className="flex flex-col gap-0.5">
                <span className="text-sm font-semibold">Harakatni kamaytirish</span>
                <span className="text-xs text-muted-foreground">
                  Animatsiyalar minimal bo&apos;ladi. Operatsion tizimdagi &quot;reduced motion&quot; sozlamasi ham hisobga olinadi.
                </span>
              </span>
              <Switch checked={userReduced} onCheckedChange={setUserReduced} />
            </label>
          </section>

          <section className="flex flex-col gap-2 rounded-2xl border border-cyan-500/25 bg-cyan-500/[0.06] p-4 text-sm">
            <h2 className="font-bold">Xavfsizlik</h2>
            <p className="text-muted-foreground">
              Sessiya tokenlari brauzer skriptlari o&apos;qiy olmaydigan httpOnly cookie&apos;larda saqlanadi. Har bir
              boshqaruv amali audit jurnaliga yoziladi.
            </p>
          </section>
        </GlassCard>
      </motion.div>
    </PageTransition>
  );
}
