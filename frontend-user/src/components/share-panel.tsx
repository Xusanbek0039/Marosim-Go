"use client";

import { ClockIcon, HourglassIcon, SendIcon, ShieldCheckIcon, UserXIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  DURATION_LABEL,
  DURATIONS,
  MAX_VIEWERS,
  timeLeft,
  useMembers,
  useRevokeInvitation,
  useRevokeViewer,
  useSentInvitations,
  useShare,
} from "@/lib/sharing";
import type { AccessDuration } from "@/lib/types";

import { PhoneInput } from "./phone-input";
import { Badge, Button, Card, cn, Field, Input, Skeleton } from "./ui";

const errorText = (err: unknown, fallback: string) => {
  if (err instanceof ApiError) {
    const fields = err.fieldErrors;
    return fields.identifier ?? fields.non_field_errors ?? fields.access_duration ?? err.message;
  }
  return fallback;
};

/** Re-render once a minute so "qoldi" countdowns stay honest. */
function useNow() {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(t);
  }, []);
  return now;
}

function ShareForm({ ceremonyId, slotsLeft, limit }: { ceremonyId: string; slotsLeft: number; limit: number }) {
  const share = useShare(ceremonyId);
  const [type, setType] = useState<"PHONE" | "PINFL">("PHONE");
  const [value, setValue] = useState("");
  const [duration, setDuration] = useState<AccessDuration>("1W");
  const [error, setError] = useState<string | null>(null);
  const full = slotsLeft <= 0;

  return (
    <form
      noValidate
      className="flex flex-col gap-4 rounded-2xl border border-glass-border bg-muted/40 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        const identifier = type === "PINFL" ? value.replace(/\D/g, "") : value.trim();
        if (type === "PINFL" && identifier.length !== 14) return setError("JSHSHIR 14 ta raqamdan iborat.");
        if (type === "PHONE" && !/^\+998\d{9}$/.test(identifier)) return setError("Raqam +998 dan keyin 9 ta raqam bo'lishi kerak.");
        share.mutate(
          { identifier_type: type, identifier, access_duration: duration },
          {
            onSuccess: () => {
              toast.success("Taklif yuborildi. U qabul qilgach galereyani ko'radi.");
              setValue("");
            },
            onError: (err) => setError(errorText(err, "Yuborib bo'lmadi")),
          },
        );
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-bold">Ko&apos;rishga ruxsat berish</p>
        <Badge tone={full ? "danger" : "brand"}>
          {limit - slotsLeft}/{limit}
        </Badge>
      </div>

      <div className="glass flex gap-1 self-start rounded-xl p-1" role="group" aria-label="Kim orqali">
        {(["PHONE", "PINFL"] as const).map((t) => (
          <button
            key={t}
            type="button"
            aria-pressed={type === t}
            onClick={() => {
              setType(t);
              setValue("");
              setError(null);
            }}
            className={cn("rounded-lg px-3 py-1.5 text-xs font-semibold", type === t ? "brand-gradient text-white" : "text-muted-foreground hover:text-foreground")}
          >
            {t === "PHONE" ? "Telefon raqam" : "JSHSHIR"}
          </button>
        ))}
      </div>

      <Field label={type === "PHONE" ? "Telefon raqam" : "JSHSHIR (14 raqam)"} htmlFor="share_identifier">
        {type === "PHONE" ? (
          <PhoneInput id="share_identifier" autoComplete="off" value={value} onChange={setValue} disabled={full} />
        ) : (
          <div className="relative">
            <ShieldCheckIcon className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="share_identifier"
              type="text"
              inputMode="numeric"
              autoComplete="off"
              maxLength={14}
              placeholder="12345678901234"
              className="pl-10 tabular-nums"
              value={value}
              disabled={full}
              onChange={(e) => setValue(e.target.value.replace(/\D/g, ""))}
            />
          </div>
        )}
      </Field>

      <fieldset className="flex flex-col gap-1.5">
        <legend className="mb-1.5 text-[13px] font-semibold text-foreground/85">Qancha muddatga</legend>
        <div className="grid grid-cols-4 gap-1.5">
          {DURATIONS.map((d) => (
            <button
              key={d.value}
              type="button"
              aria-pressed={duration === d.value}
              onClick={() => setDuration(d.value)}
              className={cn(
                "relative rounded-xl border px-2 py-2.5 text-sm font-semibold transition",
                duration === d.value ? "border-transparent text-white" : "border-glass-border text-muted-foreground hover:text-foreground",
              )}
            >
              {duration === d.value && <motion.span layoutId="duration-pill" className="absolute inset-0 rounded-xl brand-gradient" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
              <span className="relative">{d.label}</span>
            </button>
          ))}
        </div>
      </fieldset>

      {error && (
        <p role="alert" className="text-sm font-medium text-danger">
          {error}
        </p>
      )}
      <Button type="submit" loading={share.isPending} disabled={full}>
        <SendIcon /> Taklif yuborish
      </Button>
      <p className="text-xs text-muted-foreground">
        {full
          ? `Siz ${limit} kishiga ruxsat bergansiz. Avvalgilaridan birini bekor qiling yoki obuna orqali limitni oshiring.`
          : "Odam taklifni o'z hisobidan qabul qilgandan keyin galereyani ko'radi. Muddat qabul qilingan paytdan hisoblanadi. Ko'ruvchi faylni yuklab ololmaydi."}
      </p>
    </form>
  );
}

export function SharePanel({ ceremonyId }: { ceremonyId: string }) {
  const now = useNow();
  const members = useMembers(ceremonyId, true);
  const sent = useSentInvitations(ceremonyId, true);
  const revokeViewer = useRevokeViewer(ceremonyId);
  const revokeInvitation = useRevokeInvitation(ceremonyId);

  const myViewers = (members.data?.viewers ?? []).filter((v) => v.granted_by_me);
  const otherViewers = (members.data?.viewers ?? []).filter((v) => !v.granted_by_me);
  const myPending = (sent.data ?? []).filter(
    (i) => i.is_mine && i.requested_role === "VIEWER" && i.status === "PENDING" && new Date(i.expires_at).getTime() > now,
  );
  const limit = members.data?.viewer_limit ?? MAX_VIEWERS;
  const slotsLeft = limit - myViewers.length - myPending.length;

  return (
    <Card className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-bold">Kimlar ko&apos;ra oladi</h2>
        <p className="text-sm text-muted-foreground">Yaqinlaringizga vaqtinchalik ruxsat bering. Ko&apos;pi bilan {MAX_VIEWERS} kishi.</p>
      </div>

      <ShareForm ceremonyId={ceremonyId} slotsLeft={slotsLeft} limit={limit} />

      {members.isPending || sent.isPending ? (
        <Skeleton className="h-20" />
      ) : (
        <ul className="flex flex-col">
          <AnimatePresence initial={false}>
            {myViewers.map((v) => (
              <motion.li key={v.id} layout initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: 20 }} className="flex items-center gap-3 border-t border-border/70 py-3 first:border-t-0">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-300">
                  <HourglassIcon className="size-4" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold">{v.full_name || "Ko'ruvchi"}</p>
                  <p className="text-xs text-muted-foreground tabular-nums">
                    {timeLeft(v.expires_at, now)} qoldi{v.expires_at ? ` · ${formatDateTime(v.expires_at)} gacha` : ""}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label="Ruxsatni bekor qilish"
                  loading={revokeViewer.isPending && revokeViewer.variables === v.id}
                  onClick={() =>
                    revokeViewer.mutate(v.id, {
                      onSuccess: () => toast.success("Ruxsat bekor qilindi"),
                      onError: (e) => toast.error(errorText(e, "Bajarilmadi")),
                    })
                  }
                >
                  <UserXIcon />
                </Button>
              </motion.li>
            ))}
            {myPending.map((i) => (
              <motion.li key={i.id} layout initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: 20 }} className="flex items-center gap-3 border-t border-border/70 py-3 first:border-t-0">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-amber-500/15 text-amber-700 dark:text-amber-300">
                  <ClockIcon className="size-4" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold tabular-nums">{i.recipient_hint}</p>
                  <p className="text-xs text-muted-foreground">
                    Javob kutilmoqda · {i.access_duration ? DURATION_LABEL[i.access_duration] : ""}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  loading={revokeInvitation.isPending && revokeInvitation.variables === i.id}
                  onClick={() =>
                    revokeInvitation.mutate(i.id, {
                      onSuccess: () => toast.success("Taklif bekor qilindi"),
                      onError: (e) => toast.error(errorText(e, "Bajarilmadi")),
                    })
                  }
                >
                  Bekor qilish
                </Button>
              </motion.li>
            ))}
          </AnimatePresence>
          {otherViewers.length > 0 && (
            <li className="border-t border-border/70 pt-3 text-xs text-muted-foreground">
              Boshqa ega ruxsat bergan: {otherViewers.map((v) => `${v.full_name || "ko'ruvchi"} (${timeLeft(v.expires_at, now)})`).join(", ")}
            </li>
          )}
        </ul>
      )}
    </Card>
  );
}
