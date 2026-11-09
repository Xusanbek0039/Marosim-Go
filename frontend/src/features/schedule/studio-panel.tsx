"use client";

import { CalendarDaysIcon, ImagePlusIcon, Loader2Icon, XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import type { Studio } from "@/lib/api/types";
import { cn } from "@/lib/utils";

import { isoDate, useDeleteStudioImage, useStudioCalendar, useUploadStudioImage } from "./api";
import { MonthGrid, MonthNav, useMonth } from "./month-grid";

const MAX_IMAGES = 20;
const MAX_BYTES = 5 * 1024 * 1024;
const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Qoralama",
  UPLOADING: "Yuklanmoqda",
  PROCESSING: "Qayta ishlanmoqda",
  READY: "Tayyor",
  ARCHIVED: "Arxiv",
};
const errorText = (e: unknown, fallback: string) => (e instanceof ApiError ? (e.fieldErrors.image ?? e.message) : fallback);

/** Studio's schedule in the panel: ceremonies per day of the month (the same days customers see as busy). */
export function StudioSchedule({ studioId }: { studioId: string }) {
  const month = useMonth();
  const { data, error, isFetching, refetch } = useStudioCalendar(studioId, month.from, month.to);
  const [day, setDay] = useState<string | null>(null);
  const byDate = new Map<string, NonNullable<typeof data>>();
  for (const c of data ?? []) byDate.set(c.event_date, [...(byDate.get(c.event_date) ?? []), c]);
  const today = isoDate(new Date());

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h4 className="flex items-center gap-1.5 text-sm font-bold">
          <CalendarDaysIcon className="size-4" aria-hidden /> Grafik (marosimlar)
        </h4>
        <MonthNav month={month} />
      </div>
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : !data ? (
        <Skeleton className="h-56 rounded-2xl" />
      ) : (
        <MonthGrid
          month={month}
          selected={day}
          onSelect={setDay}
          dim={isFetching}
          render={(iso) => {
            const n = byDate.get(iso)?.length ?? 0;
            return {
              tone: iso < today ? "text-muted-foreground/50" : n ? "bg-amber-500/15 text-amber-700 dark:text-amber-300" : "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300",
              caption: n ? `${n} ta` : undefined,
            };
          }}
        />
      )}
      {day && (
        <ul className="flex flex-col gap-1.5 rounded-2xl border border-glass-border p-3 text-sm">
          <li className="font-bold tabular-nums">{day}</li>
          {(byDate.get(day) ?? []).length === 0 ? (
            <li className="text-muted-foreground">Bu kunda marosim yo&apos;q — bo&apos;sh.</li>
          ) : (
            byDate.get(day)!.map((c) => (
              <li key={c.id} className="flex items-center justify-between gap-2 rounded-xl bg-muted/50 px-3 py-2">
                <span className="truncate font-semibold">{c.title}</span>
                <span className="text-xs text-muted-foreground">{STATUS_LABEL[c.status] ?? c.status}</span>
              </li>
            ))
          )}
        </ul>
      )}
    </section>
  );
}

/** Portfolio (ishlari) shown on the public studio profile. */
export function StudioPortfolio({ studio, editable }: { studio: Studio; editable: boolean }) {
  const upload = useUploadStudioImage(studio.id);
  const remove = useDeleteStudioImage(studio.id);
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const images = studio.images ?? [];
  const left = MAX_IMAGES - images.length;

  const add = async (files: FileList | null) => {
    if (!files?.length) return;
    const list = Array.from(files).filter((f) => f.size <= MAX_BYTES).slice(0, left);
    if (list.length < files.length) toast.error("Ba'zi rasmlar 5 MB dan katta yoki limitdan oshdi");
    setBusy(true);
    let done = 0;
    for (const file of list) {
      try {
        await upload.mutateAsync(file);
        done += 1;
      } catch (e) {
        toast.error(`${file.name}: ${errorText(e, "yuklanmadi")}`);
      }
    }
    setBusy(false);
    if (done) toast.success(`${done} ta rasm yuklandi`);
  };

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-bold">
          Portfolio <span className="font-medium text-muted-foreground tabular-nums">{images.length}/{MAX_IMAGES}</span>
        </h4>
        {editable && left > 0 && (
          <>
            <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={(e) => (add(e.target.files), (e.target.value = ""))} />
            <Button size="sm" variant="outline" onClick={() => input.current?.click()} disabled={busy}>
              {busy ? <Loader2Icon className="animate-spin" /> : <ImagePlusIcon />} Rasm qo&apos;shish
            </Button>
          </>
        )}
      </div>
      {images.length === 0 ? (
        <p className="rounded-2xl bg-muted/50 p-4 text-center text-sm text-muted-foreground">Ishlaridan namunalar yo&apos;q. Mijozlar studiya profilida shu rasmlarni ko&apos;radi.</p>
      ) : (
        <ul className="grid grid-cols-3 gap-2">
          <AnimatePresence initial={false}>
            {images.map((img) => (
              <motion.li key={img.id} layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} className="group relative aspect-square overflow-hidden rounded-xl">
                {/* eslint-disable-next-line @next/next/no-img-element -- backend media */}
                <img src={img.image} alt="" className="size-full object-cover" />
                {editable && (
                  <button
                    type="button"
                    aria-label="Rasmni o'chirish"
                    onClick={() => remove.mutate(img.id, { onError: (e) => toast.error(errorText(e, "O'chirilmadi")) })}
                    className={cn(
                      "absolute top-1.5 right-1.5 inline-flex size-7 items-center justify-center rounded-full bg-slate-950/70 text-white opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100",
                    )}
                  >
                    <XIcon className="size-4" />
                  </button>
                )}
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </section>
  );
}
