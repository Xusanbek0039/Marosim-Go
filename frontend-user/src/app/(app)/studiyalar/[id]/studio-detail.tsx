"use client";

import { PaidBadge } from "@/components/paid-badge";

import { ArrowLeftIcon, BadgeCheckIcon, CameraIcon, ChevronLeftIcon, ChevronRightIcon, ClapperboardIcon, MapPinIcon, MessageCircleIcon, PhoneIcon } from "lucide-react";
import Link from "next/link";
import { Suspense, useState } from "react";

import { PhotoGrid } from "@/components/photo-grid";
import { EngagedPhotoGrid, ReelsStrip } from "@/components/reels";
import { ReviewsSection, StatsLine } from "@/components/reviews";
import { Card, cn, ErrorState, Skeleton } from "@/components/ui";
import { formatPhone } from "@/lib/format";
import { usePathId } from "@/lib/path-id";
import { studioCover, usePublicStudio, useStudioSchedule } from "@/lib/studios";
import { isoDate, todayIso } from "@/lib/venues";

const WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];
const MONTHS = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"];

export function StudioView() {
  return (
    <Suspense fallback={<Skeleton className="h-64 rounded-3xl" />}>
      <StudioDetail />
    </Suspense>
  );
}

function StudioDetail() {
  const id = usePathId();
  const { data: studio, error, isPending, refetch } = usePublicStudio(id);

  if (isPending) return <Skeleton className="h-64 rounded-3xl" />;
  if (error)
    return (
      <Card>
        <ErrorState error={error} onRetry={() => refetch()} />
      </Card>
    );

  const cover = studioCover(studio);
  return (
    <>
      <Link href="/studiyalar" className="flex items-center gap-1.5 px-1 text-sm font-semibold text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-4" /> Studiyalar
      </Link>

      <Card className="flex flex-col gap-4 overflow-hidden p-0 sm:p-0">
        <div className="relative h-56 bg-muted sm:h-72">
          {cover ? (
            // eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side
            <img src={cover} alt="" className="size-full object-cover" />
          ) : (
            <span className="flex size-full items-center justify-center bg-gradient-to-br from-fuchsia-600/25 to-cyan-500/25 text-cyan-600">
              <CameraIcon className="size-12" aria-hidden />
            </span>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950/70 to-transparent" aria-hidden />
          <div className="absolute inset-x-5 bottom-4 flex flex-wrap items-end justify-between gap-2">
            <h1 className="text-2xl font-extrabold tracking-tight text-white drop-shadow sm:text-3xl">{studio.name} <PaidBadge verified={studio.is_verified} /></h1>
            <StatsLine stats={studio.stats} light className="rounded-full bg-slate-950/45 px-3 py-1.5 backdrop-blur" />
          </div>
        </div>
        <div className="flex flex-col gap-3 px-5 pb-5 sm:px-6 sm:pb-6">
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <MapPinIcon className="size-4 shrink-0" aria-hidden /> {studio.address}
            </span>
            {studio.phone_number && (
              <a href={`tel:${studio.phone_number}`} className="flex items-center gap-1 font-semibold text-brand dark:text-cyan-300">
                <PhoneIcon className="size-4" aria-hidden /> {formatPhone(studio.phone_number)}
              </a>
            )}
          </div>
          {studio.description && <p className="text-sm whitespace-pre-line text-foreground/85">{studio.description}</p>}
          {studio.chat_enabled ? (
            <Link
              href={`/xabarlar?studio=${studio.id}`}
              className="brand-gradient inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl px-5 text-sm font-bold text-white shadow-[0_10px_24px_-12px_rgb(37_99_235/0.85)] transition hover:brightness-110 sm:w-max"
            >
              <MessageCircleIcon className="size-4" aria-hidden /> Studiyaga yozish
            </Link>
          ) : (
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <BadgeCheckIcon className="size-4" aria-hidden /> Chat faqat galichkali studiyalarda mavjud — hozircha telefon orqali bog&apos;laning.
            </p>
          )}
        </div>
      </Card>

      {studio.reels.length > 0 && (
        <Card className="flex flex-col gap-3">
          <h2 className="flex items-center gap-2 text-lg font-bold">
            <ClapperboardIcon className="size-5 text-accent" aria-hidden /> Reels
          </h2>
          <ReelsStrip studioId={studio.id} items={studio.reels} studioName={studio.name} />
        </Card>
      )}

      {studio.images.length > 0 && (
        <Card className="flex flex-col gap-3">
          <h2 className="text-lg font-bold">Ishlaridan namunalar</h2>
          {studio.is_verified ? (
            <EngagedPhotoGrid studioId={studio.id} items={studio.images} studioName={studio.name} />
          ) : (
            <PhotoGrid images={studio.images} title={studio.name} />
          )}
        </Card>
      )}

      <BusyCalendar id={studio.id} />

      <ReviewsSection kind="studio" id={studio.id} name={studio.name} />
    </>
  );
}

/** Month view of the studio's schedule: how many ceremonies it already has each day. */
function BusyCalendar({ id }: { id: string }) {
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return { y: now.getFullYear(), m: now.getMonth() };
  });
  const first = new Date(cursor.y, cursor.m, 1);
  const last = new Date(cursor.y, cursor.m + 1, 0);
  const schedule = useStudioSchedule(id, isoDate(first), isoDate(last));
  const busy = schedule.data?.busy ?? {};
  const marked = schedule.data?.days ?? {};
  const offWeekdays = schedule.data?.off_weekdays ?? [];
  const lead = (first.getDay() + 6) % 7;
  const cells = [...Array<null>(lead).fill(null), ...Array.from({ length: last.getDate() }, (_, i) => i + 1)];
  const today = todayIso();
  const shift = (d: number) =>
    setCursor(({ y, m }) => {
      const n = new Date(y, m + d, 1);
      return { y: n.getFullYear(), m: n.getMonth() };
    });

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-bold">Studiya grafigi</h2>
        <div className="flex items-center gap-1">
          <button type="button" aria-label="Oldingi oy" onClick={() => shift(-1)} className="glass inline-flex size-9 items-center justify-center rounded-xl hover:bg-muted">
            <ChevronLeftIcon className="size-4" />
          </button>
          <p className="min-w-36 text-center font-bold tabular-nums">
            {MONTHS[cursor.m]} {cursor.y}
          </p>
          <button type="button" aria-label="Keyingi oy" onClick={() => shift(1)} className="glass inline-flex size-9 items-center justify-center rounded-xl hover:bg-muted">
            <ChevronRightIcon className="size-4" />
          </button>
        </div>
      </div>
      {schedule.error ? (
        <ErrorState error={schedule.error} onRetry={() => schedule.refetch()} />
      ) : (
        <div className={cn("grid grid-cols-7 gap-1.5 text-center transition-opacity", schedule.isFetching && "opacity-60")}>
          {WEEKDAYS.map((w, i) => (
            <span key={w} className={cn("pb-1 text-[11px] font-bold uppercase", i >= 5 ? "text-accent" : "text-muted-foreground")}>
              {w}
            </span>
          ))}
          {cells.map((d, i) => {
            if (d === null) return <span key={`x${i}`} />;
            const iso = isoDate(new Date(cursor.y, cursor.m, d));
            const n = busy[iso] ?? 0;
            const past = iso < today;
            const off = marked[iso] === "OFF" || (!marked[iso] && !n && offWeekdays.includes(i % 7)); // grid column = weekday (Monday first)
            const state = past ? "past" : off ? "off" : marked[iso] === "BUSY" || n ? "busy" : "free";
            return (
              <span
                key={iso}
                className={cn(
                  "flex aspect-square flex-col items-center justify-center rounded-xl text-sm font-bold sm:aspect-[1.4]",
                  {
                    past: "text-muted-foreground/50",
                    off: "bg-slate-500/15 text-slate-600 dark:text-slate-300",
                    busy: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
                    free: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
                  }[state],
                )}
              >
                {d}
                {!past && (
                  <span className="text-[10px] font-semibold">
                    {state === "off" ? "dam olish" : state === "busy" ? (n ? `${n} ta band` : "band") : "bo'sh"}
                  </span>
                )}
              </span>
            );
          })}
        </div>
      )}
      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5"><i className="size-3 rounded bg-emerald-500/40" /> Bo&apos;sh</span>
        <span className="flex items-center gap-1.5"><i className="size-3 rounded bg-amber-500/40" /> Band (ish kuni)</span>
        <span className="flex items-center gap-1.5"><i className="size-3 rounded bg-slate-500/40" /> Dam olish</span>
      </div>
    </Card>
  );
}
