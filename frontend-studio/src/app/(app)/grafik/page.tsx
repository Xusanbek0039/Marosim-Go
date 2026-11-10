"use client";

import { BanIcon, CalendarCheckIcon, CheckIcon, ChevronLeftIcon, ChevronRightIcon, CoffeeIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageTitle } from "@/components/shell";
import { Button, Card, cn, EmptyState, ErrorState, Field, Input, Modal, Select, Skeleton } from "@/components/ui";
import { formatEventDate } from "@/lib/format";
import { type DayStatus, useMyStudios, useSetDay, useSetOffWeekdays, useStudioSchedule } from "@/lib/studio";
import type { MyStudioMembership } from "@/lib/types";

const WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];
const WEEKDAY_NAMES = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"];
const MONTHS = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"];

const pad = (n: number) => String(n).padStart(2, "0");
const isoDate = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
/** Monday = 0 … Sunday = 6 (backend convention). */
const weekday = (d: Date) => (d.getDay() + 6) % 7;

type Kind = "past" | "ceremony" | "busy" | "off" | "free";
const TONE: Record<Kind, string> = {
  past: "text-muted-foreground/50",
  ceremony: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  busy: "bg-red-500/15 text-red-700 dark:text-red-300",
  off: "bg-slate-500/15 text-slate-600 dark:text-slate-300",
  free: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
};

function StudioCalendar({ membership }: { membership: MyStudioMembership }) {
  const { studio, can_manage } = membership;
  const [cursor, setCursor] = useState(() => ({ y: new Date().getFullYear(), m: new Date().getMonth() }));
  const [picked, setPicked] = useState<string | null>(null);
  const first = new Date(cursor.y, cursor.m, 1);
  const last = new Date(cursor.y, cursor.m + 1, 0);
  const schedule = useStudioSchedule(studio.id, isoDate(first), isoDate(last));
  const setOff = useSetOffWeekdays(studio.id);
  const s = schedule.data;
  const today = isoDate(new Date());
  const cells = [...Array<null>(weekday(first)).fill(null), ...Array.from({ length: last.getDate() }, (_, i) => i + 1)];

  const kindOf = (d: Date): Kind => {
    const iso = isoDate(d);
    if (iso < today) return "past";
    const marked = s?.days[iso];
    if (marked === "OFF") return "off";
    if (marked === "BUSY") return "busy";
    if (s?.busy[iso]) return "ceremony";
    if (s?.off_weekdays.includes(weekday(d))) return "off";
    return "free";
  };
  const counts = { free: 0, ceremony: 0, busy: 0, off: 0 };
  for (let d = 1; d <= last.getDate(); d++) {
    const k = kindOf(new Date(cursor.y, cursor.m, d));
    if (k !== "past") counts[k] += 1;
  }

  const shift = (n: number) =>
    setCursor(({ y, m }) => {
      const d = new Date(y, m + n, 1);
      return { y: d.getFullYear(), m: d.getMonth() };
    });
  const toggleWeekday = (w: number) => {
    if (!s) return;
    const next = s.off_weekdays.includes(w) ? s.off_weekdays.filter((x) => x !== w) : [...s.off_weekdays, w];
    setOff.mutate(next, { onError: (e) => toast.error(e.message) });
  };

  return (
    <Card className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-bold">{studio.name}</h2>
        <div className="flex items-center gap-1">
          <button type="button" aria-label="Oldingi oy" onClick={() => shift(-1)} className="glass inline-flex size-9 items-center justify-center rounded-xl hover:bg-muted">
            <ChevronLeftIcon className="size-4" />
          </button>
          <p className="min-w-36 text-center font-bold tabular-nums">{MONTHS[cursor.m]} {cursor.y}</p>
          <button type="button" aria-label="Keyingi oy" onClick={() => shift(1)} className="glass inline-flex size-9 items-center justify-center rounded-xl hover:bg-muted">
            <ChevronRightIcon className="size-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {(
          [
            ["free", "Bo'sh kunlar", CheckIcon],
            ["ceremony", "Ish kunlari (marosim)", CalendarCheckIcon],
            ["busy", "Band", BanIcon],
            ["off", "Dam olish", CoffeeIcon],
          ] as const
        ).map(([k, label, Icon]) => (
          <div key={k} className={cn("flex items-center gap-2 rounded-2xl px-3 py-2.5", TONE[k])}>
            <Icon className="size-4 shrink-0" aria-hidden />
            <span className="text-xs font-semibold">{label}</span>
            <span className="ml-auto text-lg font-extrabold tabular-nums">{counts[k]}</span>
          </div>
        ))}
      </div>

      {schedule.isPending ? (
        <Skeleton className="h-72 rounded-2xl" />
      ) : schedule.error ? (
        <ErrorState error={schedule.error} onRetry={() => schedule.refetch()} />
      ) : (
        <div className={cn("grid grid-cols-7 gap-1.5 text-center transition-opacity", schedule.isFetching && "opacity-60")}>
          {WEEKDAYS.map((w, i) => (
            <span key={w} className={cn("pb-1 text-[11px] font-bold uppercase", s?.off_weekdays.includes(i) ? "text-slate-500" : i >= 5 ? "text-accent" : "text-muted-foreground")}>
              {w}
            </span>
          ))}
          {cells.map((d, i) => {
            if (d === null) return <span key={`x${i}`} />;
            const date = new Date(cursor.y, cursor.m, d);
            const iso = isoDate(date);
            const kind = kindOf(date);
            const n = s?.busy[iso] ?? 0;
            const label = { past: "", ceremony: `${n} ta marosim`, busy: "band", off: "dam olish", free: "bo'sh" }[kind];
            return (
              <button
                key={iso}
                type="button"
                disabled={!can_manage || kind === "past"}
                onClick={() => setPicked(iso)}
                title={s?.notes[iso]}
                className={cn(
                  "relative flex aspect-square flex-col items-center justify-center rounded-xl text-sm font-bold transition enabled:hover:ring-2 enabled:hover:ring-cyan-500/50 sm:aspect-[1.4]",
                  TONE[kind],
                  iso === today && "ring-2 ring-cyan-500",
                )}
              >
                {d}
                {label && <span className="text-[10px] leading-tight font-semibold">{label}</span>}
                {kind !== "ceremony" && n > 0 && kind !== "past" && <span className="text-[9px] font-semibold opacity-80">{n} marosim</span>}
                {s?.notes[iso] && <span className="absolute top-1 right-1 size-1.5 rounded-full bg-current" aria-hidden />}
              </button>
            );
          })}
        </div>
      )}

      <div className="flex flex-col gap-2">
        <p className="text-sm font-semibold">Haftalik dam olish kunlari</p>
        <div className="flex flex-wrap gap-1.5">
          {WEEKDAY_NAMES.map((name, w) => {
            const on = s?.off_weekdays.includes(w) ?? false;
            return (
              <button
                key={name}
                type="button"
                disabled={!can_manage || !s || setOff.isPending}
                aria-pressed={on}
                onClick={() => toggleWeekday(w)}
                className={cn(
                  "rounded-xl border px-3 py-1.5 text-sm font-semibold transition disabled:opacity-60",
                  on ? "border-slate-500 bg-slate-500/15" : "border-border hover:bg-muted",
                )}
              >
                {name}
              </button>
            );
          })}
        </div>
        <p className="text-xs text-muted-foreground">
          Mijozlar studiya profilida shu grafikni ko&apos;radi (izohlaringiz ko&apos;rinmaydi). Marosim qo&apos;shilgan kunlar avtomatik &quot;ish kuni&quot; bo&apos;ladi.
        </p>
      </div>

      <Modal open={Boolean(picked)} onClose={() => setPicked(null)} title={picked ? formatEventDate(picked) : ""}>
        {picked && s && (
          <DayForm
            studioId={studio.id}
            date={picked}
            current={s.days[picked] ?? null}
            note={s.notes[picked] ?? ""}
            ceremonies={s.busy[picked] ?? 0}
            onDone={() => setPicked(null)}
          />
        )}
      </Modal>
    </Card>
  );
}

function DayForm({
  studioId,
  date,
  current,
  note: initialNote,
  ceremonies,
  onDone,
}: {
  studioId: string;
  date: string;
  current: DayStatus | null;
  note: string;
  ceremonies: number;
  onDone: () => void;
}) {
  const setDay = useSetDay(studioId);
  const [status, setStatus] = useState<DayStatus | "">(current ?? "");
  const [note, setNote] = useState(initialNote);
  return (
    <div className="flex flex-col gap-4">
      {ceremonies > 0 && <p className="rounded-xl bg-amber-500/10 px-3 py-2 text-sm">Bu kunda {ceremonies} ta marosim bor — mijozlarga &quot;band&quot; ko&apos;rinadi.</p>}
      <Field label="Kun holati" htmlFor="day-status">
        <Select id="day-status" value={status} onChange={(e) => setStatus(e.target.value as DayStatus | "")}>
          <option value="">Bo&apos;sh (belgisiz)</option>
          <option value="BUSY">Band</option>
          <option value="OFF">Dam olish</option>
        </Select>
      </Field>
      <Field label="Ichki izoh (faqat sizga ko'rinadi)" htmlFor="day-note">
        <Input id="day-note" maxLength={200} value={note} onChange={(e) => setNote(e.target.value)} disabled={!status} placeholder="Masalan: Xorazmda to'y" />
      </Field>
      <Button
        loading={setDay.isPending}
        onClick={() =>
          setDay.mutate(
            { date, status: status || null, note: status ? note : "" },
            { onSuccess: () => (toast.success("Grafik yangilandi"), onDone()), onError: (e) => toast.error(e.message) },
          )
        }
      >
        Saqlash
      </Button>
    </div>
  );
}

export default function SchedulePage() {
  const studios = useMyStudios();
  return (
    <>
      <PageTitle title="Grafik" subtitle="Ish kunlari, band va dam olish kunlari — mijozlar bo'sh kunlaringizni ko'radi" />
      {studios.isPending ? (
        <Skeleton className="h-96 rounded-3xl" />
      ) : studios.error ? (
        <Card>
          <ErrorState error={studios.error} onRetry={() => studios.refetch()} />
        </Card>
      ) : studios.data.length === 0 ? (
        <Card>
          <EmptyState title="Studiya topilmadi" description="Hisobingiz hali studiyaga biriktirilmagan." />
        </Card>
      ) : (
        studios.data.map((m) => <StudioCalendar key={m.studio.id} membership={m} />)
      )}
    </>
  );
}
