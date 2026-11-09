"use client";

import { CalendarDaysIcon, CheckIcon, InboxIcon, LockIcon, PhoneIcon, XIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import type { VenueBooking } from "@/lib/api/types";
import { formatPhone } from "@/lib/format";
import { cn } from "@/lib/utils";

import { BOOKING_STATUS, hhmm, isoDate, useBookingAction, useCreateEntry, useVenueCalendar, useVenueRequests } from "./api";
import { MonthGrid, MonthNav, useMonth } from "./month-grid";

const fail = (e: unknown) => toast.error(e instanceof ApiError ? e.message : "Amal bajarilmadi");
const OCCUPYING = new Set(["CONFIRMED", "BLOCKED"]);

function StatusPill({ status }: { status: VenueBooking["status"] }) {
  return <span className={cn("inline-flex h-5 items-center rounded-full px-2 text-[11px] font-bold", BOOKING_STATUS[status].className)}>{BOOKING_STATUS[status].label}</span>;
}

function Who({ b }: { b: VenueBooking }) {
  const name = b.requester?.full_name || b.contact_name || (b.status === "BLOCKED" ? "To'yxona yopgan" : "—");
  const phone = b.contact_phone || b.requester?.phone_number;
  return (
    <span className="min-w-0 truncate text-xs text-muted-foreground">
      {name}
      {phone && (
        <>
          {" · "}
          <PhoneIcon className="inline size-3" aria-hidden /> <span className="tabular-nums">{formatPhone(phone)}</span>
        </>
      )}
    </span>
  );
}

/** Panel view of one venue's schedule: pending requests + month calendar with per-day details. */
export function VenueSchedule({ venueId, canManage }: { venueId: string; canManage: boolean }) {
  const month = useMonth();
  const calendar = useVenueCalendar(venueId, month.from, month.to);
  const requests = useVenueRequests(venueId);
  const act = useBookingAction(venueId);
  const create = useCreateEntry(venueId);
  const [day, setDay] = useState<string | null>(null);

  const run = (id: string, action: "confirm" | "reject" | "cancel") =>
    act.mutate(
      { id, action },
      { onSuccess: () => toast.success(action === "confirm" ? "Tasdiqlandi" : action === "reject" ? "Rad etildi" : "Bekor qilindi"), onError: fail },
    );

  const data = calendar.data;
  const activeHalls = data?.halls.filter((h) => h.is_active) ?? [];
  const sessionsTotal = activeHalls.reduce((n, h) => n + h.sessions.filter((s) => s.is_active).length, 0);
  const byDate = new Map<string, VenueBooking[]>();
  for (const b of data?.bookings ?? []) byDate.set(b.date, [...(byDate.get(b.date) ?? []), b]);
  const today = isoDate(new Date());

  return (
    <section className="flex flex-col gap-4">
      <h4 className="flex items-center gap-1.5 text-sm font-bold">
        <CalendarDaysIcon className="size-4" aria-hidden /> Grafik (jadval)
      </h4>

      {/* request queue */}
      <div className="flex flex-col gap-2 rounded-2xl border border-glass-border bg-muted/30 p-3">
        <p className="flex items-center gap-1.5 text-xs font-bold text-muted-foreground uppercase">
          <InboxIcon className="size-3.5" aria-hidden /> Kutilayotgan so&apos;rovlar {requests.data ? `(${requests.data.length})` : ""}
        </p>
        {requests.isPending ? (
          <Skeleton className="h-12 rounded-xl" />
        ) : requests.error ? (
          <ErrorState error={requests.error} onRetry={() => requests.refetch()} />
        ) : requests.data.length === 0 ? (
          <p className="text-sm text-muted-foreground">So&apos;rov yo&apos;q.</p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {requests.data.map((b) => (
              <li key={b.id} className="flex flex-wrap items-center gap-2 rounded-xl bg-background/60 px-3 py-2 text-sm">
                <div className="flex min-w-0 flex-1 flex-col">
                  <span className="font-semibold tabular-nums">
                    {b.date} · {b.session.name} {hhmm(b.session.starts_at)} · {b.hall.name}
                  </span>
                  <Who b={b} />
                </div>
                {canManage && (
                  <div className="flex gap-1">
                    <Button size="sm" variant="outline" disabled={act.isPending} onClick={() => run(b.id, "reject")} aria-label="Rad etish">
                      <XIcon />
                    </Button>
                    <Button size="sm" disabled={act.isPending} onClick={() => run(b.id, "confirm")}>
                      <CheckIcon /> Tasdiqlash
                    </Button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* month calendar */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">Kun ustiga bosing — smenalar va bronlar</span>
        <MonthNav month={month} />
      </div>
      {calendar.error ? (
        <ErrorState error={calendar.error} onRetry={() => calendar.refetch()} />
      ) : !data ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : (
        <MonthGrid
          month={month}
          selected={day}
          onSelect={setDay}
          dim={calendar.isFetching}
          render={(iso) => {
            const rows = byDate.get(iso) ?? [];
            const taken = rows.filter((b) => OCCUPYING.has(b.status)).length;
            const asked = rows.filter((b) => b.status === "REQUESTED").length;
            const past = iso < today;
            const tone = past
              ? "text-muted-foreground/50"
              : sessionsTotal && taken >= sessionsTotal
                ? "bg-slate-500/20 text-muted-foreground"
                : taken
                  ? "bg-amber-500/15 text-amber-700 dark:text-amber-300"
                  : "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300";
            return { tone, caption: taken ? `${taken} band` : asked ? `${asked} so'rov` : undefined };
          }}
        />
      )}
      <div className="flex flex-wrap gap-3 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1"><i className="size-2.5 rounded bg-emerald-500/40" /> Bo&apos;sh</span>
        <span className="flex items-center gap-1"><i className="size-2.5 rounded bg-amber-500/40" /> Qisman band</span>
        <span className="flex items-center gap-1"><i className="size-2.5 rounded bg-slate-500/40" /> To&apos;liq band</span>
      </div>

      {day && data && (
        <div className="flex flex-col gap-3 rounded-2xl border border-glass-border p-3">
          <p className="text-sm font-bold tabular-nums">{day}</p>
          {activeHalls.map((hall) => (
            <div key={hall.id} className="flex flex-col gap-1.5">
              <p className="text-xs font-bold text-muted-foreground">{hall.name}</p>
              {hall.sessions
                .filter((s) => s.is_active)
                .map((s) => {
                  const rows = (byDate.get(day) ?? []).filter((b) => b.session.id === s.id);
                  const holder = rows.find((b) => OCCUPYING.has(b.status));
                  const pending = rows.filter((b) => b.status === "REQUESTED");
                  return (
                    <div key={s.id} className="flex flex-col gap-1 rounded-xl bg-muted/50 px-3 py-2 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold">
                          {s.name} <span className="font-normal text-muted-foreground tabular-nums">{hhmm(s.starts_at)}–{hhmm(s.ends_at)}</span>
                        </span>
                        {holder ? (
                          <span className="flex items-center gap-1.5">
                            <StatusPill status={holder.status} />
                            {canManage && (
                              <Button size="sm" variant="ghost" disabled={act.isPending} onClick={() => run(holder.id, "cancel")}>
                                Bekor qilish
                              </Button>
                            )}
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5">
                            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-300">Bo&apos;sh</span>
                            {canManage && day >= today && (
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={create.isPending}
                                onClick={() =>
                                  create.mutate(
                                    { session: s.id, date: day, status: "BLOCKED", venue_note: "Admin panel orqali yopildi" },
                                    { onSuccess: () => toast.success("Smena yopildi"), onError: fail },
                                  )
                                }
                              >
                                <LockIcon /> Yopish
                              </Button>
                            )}
                          </span>
                        )}
                      </div>
                      {holder && <Who b={holder} />}
                      {pending.map((b) => (
                        <div key={b.id} className="flex items-center justify-between gap-2">
                          <span className="flex min-w-0 items-center gap-1.5">
                            <StatusPill status={b.status} />
                            <Who b={b} />
                          </span>
                          {canManage && !holder && (
                            <Button size="sm" variant="ghost" disabled={act.isPending} onClick={() => run(b.id, "confirm")}>
                              <CheckIcon /> Tasdiqlash
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  );
                })}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
