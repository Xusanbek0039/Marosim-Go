"use client";

import { EyeIcon, EyeOffIcon, Loader2Icon } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { RoleBadge, StatusBadge, UserAvatar } from "@/components/common";
import { PaidBadge } from "@/components/paid-badge";
import { MotionDrawer } from "@/components/motion/motion-dialog";
import { Button } from "@/components/ui/button";
import { useCan, useMe } from "@/features/auth/hooks";
import { adminsResource, usersResource, useRevealPinfl, useVerifyPhone } from "@/features/resources";
import { ApiError } from "@/lib/api/client";
import type { Admin, ManagedUser } from "@/lib/api/types";
import { formatDate, formatDateTime, formatPhone } from "@/lib/format";

import { AccountFeatures, AccountFolders } from "./account-panels";
import type { PersonKind } from "./person-form-dialog";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border/70 py-3 text-sm last:border-b-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{children}</span>
    </div>
  );
}

const REVEAL_SECONDS = 20;

function PhoneVerifiedBadge({ verified }: { verified: boolean }) {
  return (
    <span
      className={
        verified
          ? "rounded-full bg-emerald-500/14 px-2 py-0.5 text-[11px] font-bold text-emerald-700 dark:text-emerald-300"
          : "rounded-full bg-amber-500/14 px-2 py-0.5 text-[11px] font-bold text-amber-700 dark:text-amber-300"
      }
    >
      {verified ? "Tasdiqlangan" : "Tasdiqlanmagan"}
    </span>
  );
}

export function PersonDrawer({
  kind,
  person: initialPerson,
  open,
  onOpenChange,
  onEdit,
  onToggleActive,
}: {
  kind: PersonKind;
  person: ManagedUser | Admin | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEdit?: () => void;
  onToggleActive?: () => void;
}) {
  const can = useCan();
  const { data: me } = useMe();
  const resource = kind === "admin" ? "admins" : "users";
  const detail = (kind === "admin" ? adminsResource : usersResource).useDetail(open ? initialPerson?.id ?? null : null);
  const person = (detail.data ?? initialPerson) as ManagedUser | Admin | null;
  const verifyPhone = useVerifyPhone(resource);
  const canVerify = me?.role === "SUPER_ADMIN" || (kind !== "admin" && can("users.update"));
  const reveal = useRevealPinfl(kind === "admin" ? "admins" : "users");
  const [revealed, setRevealed] = useState<{ id: string; value: string } | null>(null);
  const plain = open && person && revealed?.id === person.id ? revealed.value : null;
  const setPlain = (value: string | null) => setRevealed(value && person ? { id: person.id, value } : null);
  const canReveal = kind === "admin" ? me?.role === "SUPER_ADMIN" : can("users.view_pinfl");

  // Full PINFL stays on screen briefly and is wiped when the drawer closes.
  useEffect(() => {
    if (!revealed) return;
    const id = setTimeout(() => setRevealed(null), REVEAL_SECONDS * 1000);
    return () => clearTimeout(id);
  }, [revealed]);

  if (!person) return null;

  return (
    <MotionDrawer
      open={open}
      onOpenChange={(next) => {
        if (!next) setRevealed(null);
        onOpenChange(next);
      }}
      title="Profil tafsiloti"
      footer={
        <>
          {onToggleActive && (
            <Button
              variant="outline"
              className={person.is_active ? "h-11 flex-1 text-warning" : "h-11 flex-1 text-success"}
              onClick={onToggleActive}
            >
              {person.is_active ? "Nofaol qilish" : "Faollashtirish"}
            </Button>
          )}
          {onEdit && (
            <Button className="h-11 flex-1" onClick={onEdit}>
              Tahrirlash
            </Button>
          )}
        </>
      }
    >
      <div className="flex flex-col items-center gap-3 pt-2 text-center">
        <motion.div initial={{ scale: 0.85, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: 0.12 }}>
          <UserAvatar
            id={person.id}
            first={person.first_name}
            last={person.last_name}
            src={person.profile_picture}
            className="size-24 text-2xl ring-4 ring-cyan-400/40 ring-offset-4 ring-offset-transparent"
          />
        </motion.div>
        <h3 className="text-xl font-extrabold">{person.full_name} <PaidBadge verified={person.is_verified} /></h3>
        <div className="flex items-center gap-3">
          <RoleBadge role={person.role} />
          <StatusBadge active={person.is_active} />
        </div>
      </div>

      <div className="rounded-2xl border border-glass-border bg-muted/40 px-4">
        <Row label="Telefon">
          <span className="inline-flex flex-wrap justify-end gap-2 tabular-nums">
            {formatPhone(person.phone_number)}
            {person.phone_number && <PhoneVerifiedBadge verified={person.is_phone_verified} />}
          </span>
        </Row>
        {!person.is_phone_verified && (
          <div className="border-b border-border/70 py-3">
            {canVerify ? (
              <Button
                className="w-full"
                disabled={!person.phone_number || verifyPhone.isPending}
                onClick={() => verifyPhone.mutate(person.id, {
                  onSuccess: () => toast.success("Telefon raqami tasdiqlandi"),
                  onError: (e) => toast.error(e instanceof ApiError ? e.message : "Tasdiqlab bo'lmadi"),
                })}
              >
                {verifyPhone.isPending ? "Tasdiqlanmoqda..." : "Telefon raqamini tasdiqlash"}
              </Button>
            ) : (
              <p className="text-sm text-muted-foreground">
                Telefonni tasdiqlash uchun foydalanuvchini tahrirlash ruxsati kerak.
              </p>
            )}
            {!person.phone_number && (
              <p className="mt-2 text-sm text-muted-foreground">Avval tahrirlash orqali telefon raqamini kiriting.</p>
            )}
          </div>
        )}
        <Row label="Email">{person.email || "—"}</Row>
        <Row label="JSHSHIR">
          <span className="inline-flex items-center gap-2 tabular-nums tracking-wider">
            {plain ?? person.pinfl_masked ?? "—"}
            {canReveal && person.pinfl_masked && (
              <button
                type="button"
                className="inline-flex size-7 items-center justify-center rounded-lg text-brand hover:bg-muted dark:text-cyan-300"
                aria-label={plain ? "JSHSHIRni yashirish" : "To'liq JSHSHIRni ko'rsatish"}
                disabled={reveal.isPending}
                onClick={() => {
                  if (plain) return setPlain(null);
                  reveal.mutate(person.id, {
                    onSuccess: (d) => setPlain(d.pinfl),
                    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Ko'rsatib bo'lmadi"),
                  });
                }}
              >
                {reveal.isPending ? (
                  <Loader2Icon className="size-4 animate-spin" />
                ) : plain ? (
                  <EyeOffIcon className="size-4" />
                ) : (
                  <EyeIcon className="size-4" />
                )}
              </button>
            )}
          </span>
        </Row>
        <Row label="Manzil">{person.address || "—"}</Row>
        <Row label="Oxirgi kirish">{formatDateTime(person.last_login)}</Row>
        <Row label="Ro'yxatdan o'tgan">{formatDate(person.created_at)}</Row>
      </div>

      {"permissions" in person && (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-bold">Ruxsatlar</p>
          <div className="flex flex-wrap gap-1.5">
            {person.permissions.length === 0 && <span className="text-sm text-muted-foreground">Ruxsat berilmagan</span>}
            {person.permissions.map((p) => (
              <span key={p} className="rounded-full bg-blue-500/12 px-2.5 py-1 text-xs font-semibold text-blue-700 dark:text-blue-300">
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {kind !== "admin" && (
        <>
          <AccountFeatures userId={person.id} />
          {person.role === "USER" && <AccountFolders userId={person.id} />}
        </>
      )}

      {canReveal && (
        <p className="text-xs leading-relaxed text-muted-foreground">
          To&apos;liq JSHSHIR {REVEAL_SECONDS} soniya ko&apos;rinadi. Har bir ko&apos;rish audit jurnaliga yoziladi.
        </p>
      )}
    </MotionDrawer>
  );
}
