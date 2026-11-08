"use client";

import { ArrowLeftIcon, ChevronLeftIcon, ChevronRightIcon, MapPinIcon, PhoneIcon, UsersIcon } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { type BookingTarget, BookingModal } from "@/components/booking-modal";
import { Card, cn, ErrorState, Skeleton } from "@/components/ui";
import { formatEventDate, formatMoney, formatPhone } from "@/lib/format";
import { hhmm, isoDate, REGION_LABELS, todayIso, useAvailability, usePublicVenue } from "@/lib/venues";

const WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];
const MONTHS = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"];

export default function VenuePage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 rounded-3xl" />}>
      <VenueDetail />
    </Suspense>
  );
}

function VenueDetail() {
  const { id } = useParams<{ id: string }>();
  const initialDate = useSearchParams().get("date") || todayIso();
  const { data, error, isPending, refetch } = usePublicVenue(id);
  const [selected, setSelected] = useState(initialDate);
  const [cursor, setCursor] = useState(() => {
    const [y, m] = initialDate.split("-").map(Number);
    return { y, m: m - 1 };
  });
  const [hallId, setHallId] = useState<string | null>(null);
  const [target, setTarget] = useState<BookingTarget | null>(null);

  const first = new Date(cursor.y, cursor.m, 1);
  const last = new Date(cursor.y, cursor.m + 1, 0);
  const availability = useAvailability(id, isoDate(first), isoDate(last));

  if (isPending) return <Skeleton className="h-64 rounded-3xl" />;
  if (error)
    return (
      <Card>
        <ErrorState error={error} onRetry={() => refetch()} />
      </Card>
    );

  const { venue, halls } = data;
  const hall = halls.find((h) => h.id === hallId) ?? halls[0];
  const freeByDate = (hall && availability.data?.free[hall.id]) || {};
  const sessionCount = hall?.sessions.length ?? 0;
  const lead = (first.getDay() + 6) % 7;
  const cells = [...Array<null>(lead).fill(null), ...Array.from({ length: last.getDate() }, (_, i) => i + 1)];
  const today = todayIso();
  const shift = (d: number) =>
    setCursor(({ y, m }) => {
      const n = new Date(y, m + d, 1);
      return { y: n.getFullYear(), m: n.getMonth() };
    });
  const cover = venue.cover_image ?? venue.images[0]?.image;
  const freeToday = new Set(freeByDate[selected] ?? []);

  return (
    <>
      <Link href="/toyxonalar" className="flex items-center gap-1.5 px-1 text-sm font-semibold text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-4" /> To&apos;yxonalar
      </Link>

      <Card className="flex flex-col gap-4 overflow-hidden p-0 sm:p-0">
        {cover && (
          // eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side
          <img src={cover} alt="" className="h-56 w-full object-cover sm:h-72" />
        )}
        <div className="flex flex-col gap-3 px-5 pb-5 sm:px-6 sm:pb-6">
          <h1 className="text-2xl font-extrabold tracking-tight">{venue.name}</h1>
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <MapPinIcon className="size-4 shrink-0" aria-hidden />
            {REGION_LABELS[venue.region]}
            {venue.district && `, ${venue.district}`} · {venue.address}
          </p>
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
            <span>
              Sig&apos;im: <b>{venue.capacity_min ? `${venue.capacity_min}–` : ""}{venue.capacity_max} kishi</b>
            </span>
            <span>
              Narx: <b>{formatMoney(venue.base_price)} dan</b>
            </span>
            {venue.phone_number && (
              <a href={`tel:${venue.phone_number}`} className="flex items-center gap-1 font-semibold text-brand dark:text-cyan-300">
                <PhoneIcon className="size-4" aria-hidden /> {formatPhone(venue.phone_number)}
              </a>
            )}
          </div>
          {venue.description && <p className="text-sm whitespace-pre-line text-foreground/85">{venue.description}</p>}
          {venue.images.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {venue.images.map((img) => (
                // eslint-disable-next-line @next/next/no-img-element -- proxied media
                <img key={img.id} src={img.image} alt="" className="h-24 w-36 shrink-0 rounded-xl object-cover" />
              ))}
            </div>
          )}
        </div>
      </Card>

      <Card className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold">Bo&apos;sh kunlar</h2>
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

        {halls.length > 1 && (
          <div className="glass flex flex-wrap gap-1 self-start rounded-xl p-1" role="group" aria-label="Zal">
            {halls.map((h) => (
              <button
                key={h.id}
                type="button"
                aria-pressed={hall?.id === h.id}
                onClick={() => setHallId(h.id)}
                className={cn("rounded-lg px-3 py-1.5 text-xs font-semibold", hall?.id === h.id ? "brand-gradient text-white" : "text-muted-foreground hover:text-foreground")}
              >
                {h.name} · {h.capacity}
              </button>
            ))}
          </div>
        )}

        <div className={cn("grid grid-cols-7 gap-1.5 text-center transition-opacity", availability.isFetching && "opacity-60")}>
          {WEEKDAYS.map((w, i) => (
            <span key={w} className={cn("pb-1 text-[11px] font-bold uppercase", i >= 5 ? "text-accent" : "text-muted-foreground")}>
              {w}
            </span>
          ))}
          {cells.map((d, i) => {
            if (d === null) return <span key={`x${i}`} />;
            const iso = isoDate(new Date(cursor.y, cursor.m, d));
            const free = freeByDate[iso]?.length ?? 0;
            const past = iso < today;
            const tone = past
              ? "text-muted-foreground/50"
              : free === 0
                ? "bg-slate-500/15 text-muted-foreground"
                : free === sessionCount
                  ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                  : "bg-amber-500/15 text-amber-700 dark:text-amber-300";
            return (
              <button
                key={iso}
                type="button"
                disabled={past}
                onClick={() => setSelected(iso)}
                className={cn(
                  "flex aspect-square flex-col items-center justify-center rounded-xl text-sm font-bold transition sm:aspect-[1.4]",
                  tone,
                  selected === iso && "ring-2 ring-brand",
                )}
              >
                {d}
                {!past && <span className="text-[10px] font-semibold">{free ? `${free} bo'sh` : "band"}</span>}
              </button>
            );
          })}
        </div>
        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5"><i className="size-3 rounded bg-emerald-500/40" /> Hammasi bo&apos;sh</span>
          <span className="flex items-center gap-1.5"><i className="size-3 rounded bg-amber-500/40" /> Qisman bo&apos;sh</span>
          <span className="flex items-center gap-1.5"><i className="size-3 rounded bg-slate-500/30" /> Band</span>
        </div>

        {hall && (
          <div className="flex flex-col gap-2 rounded-2xl border border-border p-4">
            <p className="font-bold">
              {formatEventDate(selected)} · {hall.name}
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                <UsersIcon className="inline size-3.5" aria-hidden /> {hall.capacity} kishi · {formatMoney(hall.price)}
              </span>
            </p>
            <div className="flex flex-wrap gap-2">
              {hall.sessions.map((s) =>
                freeToday.has(s.id) ? (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() =>
                      setTarget({
                        venueName: venue.name,
                        address: venue.address,
                        hallName: hall.name,
                        capacity: hall.capacity,
                        price: hall.price,
                        session: s,
                        date: selected,
                      })
                    }
                    className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-500/20 dark:text-emerald-300"
                  >
                    {s.name} {hhmm(s.starts_at)}–{hhmm(s.ends_at)} · Band qilish
                  </button>
                ) : (
                  <span key={s.id} className="rounded-xl bg-muted px-3 py-2 text-sm font-semibold text-muted-foreground line-through">
                    {s.name} {hhmm(s.starts_at)}–{hhmm(s.ends_at)}
                  </span>
                ),
              )}
            </div>
          </div>
        )}
      </Card>

      <BookingModal
        target={target}
        onClose={() => {
          setTarget(null);
          availability.refetch();
        }}
      />
    </>
  );
}
