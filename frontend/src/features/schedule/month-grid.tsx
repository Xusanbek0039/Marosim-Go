"use client";

import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { isoDate, MONTHS, WEEKDAYS } from "./api";

export function useMonth() {
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return { y: now.getFullYear(), m: now.getMonth() };
  });
  const first = new Date(cursor.y, cursor.m, 1);
  const last = new Date(cursor.y, cursor.m + 1, 0);
  const shift = (d: number) =>
    setCursor(({ y, m }) => {
      const n = new Date(y, m + d, 1);
      return { y: n.getFullYear(), m: n.getMonth() };
    });
  return { ...cursor, from: isoDate(first), to: isoDate(last), first, last, shift };
}

export type Month = ReturnType<typeof useMonth>;

export function MonthNav({ month }: { month: Month }) {
  return (
    <div className="flex items-center gap-1">
      <Button variant="ghost" size="icon-sm" aria-label="Oldingi oy" onClick={() => month.shift(-1)}>
        <ChevronLeftIcon />
      </Button>
      <span className="min-w-32 text-center text-sm font-bold tabular-nums">
        {MONTHS[month.m]} {month.y}
      </span>
      <Button variant="ghost" size="icon-sm" aria-label="Keyingi oy" onClick={() => month.shift(1)}>
        <ChevronRightIcon />
      </Button>
    </div>
  );
}

/** 7-column month grid; ``render`` decides the tone and the small caption of each day. */
export function MonthGrid({
  month,
  selected,
  onSelect,
  render,
  dim,
}: {
  month: Month;
  selected: string | null;
  onSelect: (iso: string) => void;
  render: (iso: string) => { tone: string; caption?: string };
  dim?: boolean;
}) {
  const lead = (month.first.getDay() + 6) % 7;
  const cells = [...Array<null>(lead).fill(null), ...Array.from({ length: month.last.getDate() }, (_, i) => i + 1)];
  return (
    <div className={cn("grid grid-cols-7 gap-1 text-center transition-opacity", dim && "opacity-60")}>
      {WEEKDAYS.map((w) => (
        <span key={w} className="pb-1 text-[10px] font-bold text-muted-foreground uppercase">
          {w}
        </span>
      ))}
      {cells.map((d, i) => {
        if (d === null) return <span key={`x${i}`} />;
        const iso = isoDate(new Date(month.y, month.m, d));
        const { tone, caption } = render(iso);
        return (
          <button
            key={iso}
            type="button"
            onClick={() => onSelect(iso)}
            className={cn("flex aspect-square flex-col items-center justify-center rounded-lg text-xs font-bold transition", tone, selected === iso && "ring-2 ring-brand")}
          >
            {d}
            {caption && <span className="text-[9px] leading-tight font-semibold">{caption}</span>}
          </button>
        );
      })}
    </div>
  );
}
