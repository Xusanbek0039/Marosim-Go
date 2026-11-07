"use client";

import { CalendarClockIcon, ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import { useState } from "react";

import type { VenueHall } from "@/lib/types";

import { cn } from "./ui";

const WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];
const MONTHS = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"];

/** Status palette the Phase C calendar will use (kept here so the legend matches the future data). */
export const SLOT_STATUS = [
  { key: "AVAILABLE", label: "Bo'sh", className: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300" },
  { key: "HELD", label: "Vaqtincha band", className: "bg-amber-500/15 text-amber-700 dark:text-amber-300" },
  { key: "BOOKED", label: "Band", className: "bg-blue-600/15 text-blue-700 dark:text-blue-300" },
  { key: "BLOCKED", label: "Yopilgan", className: "bg-slate-500/20 text-slate-700 dark:text-slate-300" },
  { key: "CLOSED", label: "Dam olish", className: "bg-red-500/12 text-red-700 dark:text-red-300" },
] as const;

function monthCells(year: number, month: number) {
  const first = new Date(year, month, 1);
  const lead = (first.getDay() + 6) % 7; // Monday-first
  const days = new Date(year, month + 1, 0).getDate();
  return [...Array<null>(lead).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)];
}

/**
 * Month grid per hall. Phase B has no availability data yet, so cells carry dates only and the
 * card says so plainly. Phase C plugs `/venue-owner/venues/{id}/calendar/` into the same grid.
 */
export function CalendarPreview({ halls }: { halls: VenueHall[] }) {
  const today = new Date();
  const [cursor, setCursor] = useState({ y: today.getFullYear(), m: today.getMonth() });
  const active = halls.filter((h) => h.is_active);
  const [hallId, setHallId] = useState(active[0]?.id ?? "");
  const cells = monthCells(cursor.y, cursor.m);
  const shift = (d: number) =>
    setCursor(({ y, m }) => {
      const n = new Date(y, m + d, 1);
      return { y: n.getFullYear(), m: n.getMonth() };
    });
  const isToday = (d: number) => d === today.getDate() && cursor.m === today.getMonth() && cursor.y === today.getFullYear();

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          <button type="button" aria-label="Oldingi oy" onClick={() => shift(-1)} className="glass inline-flex size-9 items-center justify-center rounded-xl hover:bg-muted">
            <ChevronLeftIcon className="size-4" />
          </button>
          <p className="min-w-36 text-center text-base font-bold tabular-nums">
            {MONTHS[cursor.m]} {cursor.y}
          </p>
          <button type="button" aria-label="Keyingi oy" onClick={() => shift(1)} className="glass inline-flex size-9 items-center justify-center rounded-xl hover:bg-muted">
            <ChevronRightIcon className="size-4" />
          </button>
        </div>
        {active.length > 1 && (
          <div className="glass flex flex-wrap gap-1 rounded-xl p-1" role="group" aria-label="Zal">
            {active.map((h) => (
              <button
                key={h.id}
                type="button"
                aria-pressed={hallId === h.id}
                onClick={() => setHallId(h.id)}
                className={cn("rounded-lg px-3 py-1.5 text-xs font-semibold", hallId === h.id ? "brand-gradient text-white" : "text-muted-foreground hover:text-foreground")}
              >
                {h.name}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="relative">
        <div className="grid grid-cols-7 gap-1.5 text-center" aria-hidden>
          {WEEKDAYS.map((w, i) => (
            <span key={w} className={cn("pb-1 text-[11px] font-bold uppercase", i >= 5 ? "text-accent" : "text-muted-foreground")}>
              {w}
            </span>
          ))}
          {cells.map((d, i) =>
            d === null ? (
              <span key={`e${i}`} />
            ) : (
              <span
                key={d}
                className={cn(
                  "flex aspect-square flex-col items-start rounded-xl border border-glass-border bg-muted/40 p-1.5 text-xs font-semibold tabular-nums sm:aspect-[4/3] sm:text-sm",
                  isToday(d) && "ring-2 ring-accent",
                )}
              >
                {d}
              </span>
            ),
          )}
        </div>
        <div className="absolute inset-0 flex items-center justify-center rounded-2xl bg-background/55 p-4 backdrop-blur-[2px]">
          <div className="glass-strong flex max-w-sm flex-col items-center gap-2 rounded-3xl p-5 text-center">
            <span className="flex size-12 items-center justify-center rounded-2xl brand-gradient text-white">
              <CalendarClockIcon className="size-6" aria-hidden />
            </span>
            <p className="font-bold">Bandlik jadvali keyingi bosqichda ulanadi</p>
            <p className="text-sm text-muted-foreground">
              Phase C: har bir zal uchun bo&apos;sh / band vaqtlar, ish vaqti, dam olish kunlari va bir kunda bir nechta marosim.
            </p>
          </div>
        </div>
      </div>

      <ul className="flex flex-wrap gap-2" aria-label="Holatlar">
        {SLOT_STATUS.map((s) => (
          <li key={s.key} className={cn("rounded-full px-2.5 py-1 text-xs font-bold", s.className)}>
            {s.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
