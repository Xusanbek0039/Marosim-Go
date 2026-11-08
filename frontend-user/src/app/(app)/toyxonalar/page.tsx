"use client";

import { BuildingIcon, ChevronRightIcon, MapPinIcon, PhoneIcon, SearchIcon, UsersIcon } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { useDeferredValue, useState } from "react";

import { type BookingTarget, BookingModal } from "@/components/booking-modal";
import { PageTitle } from "@/components/shell";
import { Card, cn, EmptyState, ErrorState, Field, Input, Select, Skeleton } from "@/components/ui";
import { formatEventDate, formatMoney, formatPhone } from "@/lib/format";
import { hhmm, type Region, REGION_LABELS, type SearchResult, todayIso, useVenueSearch } from "@/lib/venues";

export default function VenueSearchPage() {
  const [date, setDate] = useState(todayIso());
  const [region, setRegion] = useState<Region | "">("");
  const [guests, setGuests] = useState("");
  const [q, setQ] = useState("");
  const deferredQ = useDeferredValue(q.trim());
  const deferredGuests = useDeferredValue(guests);
  const [target, setTarget] = useState<BookingTarget | null>(null);

  const search = useVenueSearch({ date, region, guests: deferredGuests ? Number(deferredGuests) : "", q: deferredQ });

  return (
    <>
      <PageTitle title="To'yxonalar" subtitle="Sanani tanlang — o'sha kuni bo'sh smenasi bor to'yxonalar chiqadi" />

      <Card className="grid gap-3 sm:grid-cols-[1.1fr_1fr_0.7fr_1.2fr]">
        <Field label="Marosim sanasi" htmlFor="s-date">
          <Input id="s-date" type="date" min={todayIso()} value={date} onChange={(e) => setDate(e.target.value)} required />
        </Field>
        <Field label="Hudud" htmlFor="s-region">
          <Select id="s-region" value={region} onChange={(e) => setRegion(e.target.value as Region | "")}>
            <option value="">Barcha hududlar</option>
            {Object.entries(REGION_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Mehmonlar" htmlFor="s-guests">
          <Input id="s-guests" type="number" inputMode="numeric" min={1} placeholder="300" value={guests} onChange={(e) => setGuests(e.target.value)} />
        </Field>
        <Field label="Qidiruv" htmlFor="s-q">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <Input id="s-q" className="pl-9" placeholder="Nomi yoki manzili" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
        </Field>
      </Card>

      {!date ? (
        <Card>
          <EmptyState title="Sanani tanlang" description="Masalan, to'yingiz 20-noyabr bo'lsa — shu sanani tanlang." />
        </Card>
      ) : search.isPending ? (
        <div className="grid gap-4">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-48 rounded-3xl" />
          ))}
        </div>
      ) : search.error ? (
        <Card>
          <ErrorState error={search.error} onRetry={() => search.refetch()} />
        </Card>
      ) : search.data.length === 0 ? (
        <Card>
          <EmptyState
            title={`${formatEventDate(date)} kuni bo'sh joy topilmadi`}
            description="Boshqa sana, hudud yoki mehmonlar sonini sinab ko'ring."
          />
        </Card>
      ) : (
        <>
          <p className="px-1 text-sm text-muted-foreground">
            <b className="text-foreground">{formatEventDate(date)}</b> kuni {search.data.length} ta to&apos;yxonada bo&apos;sh smena bor
          </p>
          <motion.ul
            className={cn("flex flex-col gap-4 transition-opacity", search.isPlaceholderData && "opacity-60")}
            initial="initial"
            animate="animate"
            variants={{ animate: { transition: { staggerChildren: 0.05 } } }}
          >
            {search.data.map((row) => (
              <motion.li key={row.venue.id} variants={{ initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 } }}>
                <ResultCard row={row} date={date} onPick={setTarget} />
              </motion.li>
            ))}
          </motion.ul>
        </>
      )}

      <BookingModal target={target} onClose={() => setTarget(null)} />
    </>
  );
}

function ResultCard({ row, date, onPick }: { row: SearchResult; date: string; onPick: (t: BookingTarget) => void }) {
  const { venue } = row;
  const cover = venue.cover_image ?? venue.images[0]?.image ?? null;
  return (
    <div className="glass flex flex-col overflow-hidden rounded-3xl sm:flex-row">
      <Link href={`/toyxonalar/${venue.id}?date=${date}`} className="relative block h-44 shrink-0 bg-muted sm:h-auto sm:w-64">
        {cover ? (
          // eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side
          <img src={cover} alt="" className="size-full object-cover" />
        ) : (
          <span className="flex size-full items-center justify-center bg-gradient-to-br from-blue-600/20 to-cyan-500/20 text-cyan-600">
            <BuildingIcon className="size-10" aria-hidden />
          </span>
        )}
        <span className="absolute top-3 left-3 rounded-full bg-emerald-600 px-2.5 py-1 text-xs font-bold text-white shadow">
          {row.free_slots} ta bo&apos;sh smena
        </span>
      </Link>
      <div className="flex min-w-0 flex-1 flex-col gap-3 p-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <Link href={`/toyxonalar/${venue.id}?date=${date}`} className="text-lg font-bold hover:underline">
              {venue.name}
            </Link>
            <p className="flex items-center gap-1 text-sm text-muted-foreground">
              <MapPinIcon className="size-3.5 shrink-0" aria-hidden />
              <span className="truncate">
                {REGION_LABELS[venue.region]}
                {venue.district && `, ${venue.district}`} · {venue.address}
              </span>
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">narxi</p>
            <p className="font-bold">{formatMoney(venue.base_price)} dan</p>
          </div>
        </div>

        <ul className="flex flex-col gap-2.5">
          {row.halls.map((hall) => (
            <li key={hall.id} className="flex flex-col gap-1.5">
              <p className="flex items-center gap-2 text-sm font-semibold">
                {hall.name}
                <span className="flex items-center gap-1 text-xs font-normal text-muted-foreground">
                  <UsersIcon className="size-3.5" aria-hidden /> {hall.capacity} kishi · {formatMoney(hall.price)}
                </span>
              </p>
              <div className="flex flex-wrap gap-1.5">
                {hall.slots.map((slot) =>
                  slot.is_free ? (
                    <button
                      key={slot.id}
                      type="button"
                      onClick={() =>
                        onPick({
                          venueName: venue.name,
                          address: venue.address,
                          hallName: hall.name,
                          capacity: hall.capacity,
                          price: hall.price,
                          session: slot,
                          date,
                        })
                      }
                      className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-500/20 dark:text-emerald-300"
                    >
                      {slot.name} {hhmm(slot.starts_at)}–{hhmm(slot.ends_at)} · Band qilish
                    </button>
                  ) : (
                    <span key={slot.id} className="rounded-xl bg-muted px-3 py-1.5 text-xs font-semibold text-muted-foreground line-through">
                      {slot.name} {hhmm(slot.starts_at)}–{hhmm(slot.ends_at)}
                    </span>
                  ),
                )}
              </div>
            </li>
          ))}
        </ul>

        <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-1 text-sm">
          {venue.phone_number ? (
            <a href={`tel:${venue.phone_number}`} className="flex items-center gap-1.5 font-semibold text-brand dark:text-cyan-300">
              <PhoneIcon className="size-4" aria-hidden /> {formatPhone(venue.phone_number)}
            </a>
          ) : (
            <span />
          )}
          <Link href={`/toyxonalar/${venue.id}?date=${date}`} className="flex items-center gap-1 font-semibold text-brand dark:text-cyan-300">
            Batafsil va kalendar <ChevronRightIcon className="size-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
