"use client";

import { PaidBadge } from "@/components/paid-badge";

import { BuildingIcon, CameraIcon, ChevronRightIcon, MapPinIcon, UsersIcon } from "lucide-react";
import Link from "next/link";

import { formatMoney } from "@/lib/format";
import { type PublicStudio, studioCover } from "@/lib/studios";
import { type PublicVenue, REGION_LABELS } from "@/lib/venues";

import { StatsLine } from "./reviews";

/** Ad-style card: the studio's best shot as a hero, rating and likes on top of it. */
export function StudioAdCard({ studio, top }: { studio: PublicStudio; top?: boolean }) {
  const cover = studioCover(studio);
  const thumbs = studio.images.slice(1, 4);
  return (
    <Link href={`/studiyalar/${studio.id}`} className="glass group flex h-full flex-col overflow-hidden rounded-3xl transition hover:-translate-y-0.5 hover:border-cyan-400/40">
      <div className="relative h-48 overflow-hidden bg-muted">
        {cover ? (
          // eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side
          <img src={cover} alt="" className="size-full object-cover transition duration-500 group-hover:scale-105" />
        ) : (
          <span className="flex size-full items-center justify-center bg-gradient-to-br from-fuchsia-600/25 to-cyan-500/25 text-cyan-600">
            <CameraIcon className="size-10" aria-hidden />
          </span>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/75 via-slate-950/10 to-transparent" aria-hidden />
        {top && <span className="absolute top-3 left-3 rounded-full bg-amber-500 px-2.5 py-1 text-xs font-bold text-white shadow">★ Eng yaxshi</span>}
        <div className="absolute inset-x-4 bottom-3 flex items-end justify-between gap-2">
          <p className="truncate text-lg font-extrabold text-white drop-shadow">{studio.name} <PaidBadge verified={studio.is_verified} /></p>
          <StatsLine stats={studio.stats} light className="shrink-0 rounded-full bg-slate-950/45 px-2.5 py-1 backdrop-blur" />
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <p className="flex items-center gap-1 text-sm text-muted-foreground">
          <MapPinIcon className="size-3.5 shrink-0" aria-hidden />
          <span className="truncate">{studio.address}</span>
        </p>
        {studio.description && <p className="line-clamp-2 text-sm text-foreground/80">{studio.description}</p>}
        {thumbs.length > 0 && (
          <div className="grid grid-cols-3 gap-1.5">
            {thumbs.map((img) => (
              // eslint-disable-next-line @next/next/no-img-element -- proxied media
              <img key={img.id} src={img.image} alt="" className="aspect-[4/3] w-full rounded-lg object-cover" />
            ))}
          </div>
        )}
        <span className="mt-auto flex items-center gap-1 text-sm font-semibold text-brand dark:text-cyan-300">
          Ishlari va bo&apos;sh kunlari <ChevronRightIcon className="size-4 transition group-hover:translate-x-0.5" />
        </span>
      </div>
    </Link>
  );
}


/** Ad-style venue card for the catalog strip: cover hero, rating / likes, capacity and price. */
export function VenueAdCard({ venue, top }: { venue: PublicVenue; top?: boolean }) {
  const cover = venue.cover_image ?? venue.images[0]?.image ?? null;
  return (
    <Link href={`/toyxonalar/${venue.id}`} className="glass group flex h-full flex-col overflow-hidden rounded-3xl transition hover:-translate-y-0.5 hover:border-cyan-400/40">
      <div className="relative h-40 overflow-hidden bg-muted">
        {cover ? (
          // eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side
          <img src={cover} alt="" className="size-full object-cover transition duration-500 group-hover:scale-105" />
        ) : (
          <span className="flex size-full items-center justify-center bg-gradient-to-br from-blue-600/20 to-cyan-500/20 text-cyan-600">
            <BuildingIcon className="size-10" aria-hidden />
          </span>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/75 via-slate-950/10 to-transparent" aria-hidden />
        {top && <span className="absolute top-3 left-3 rounded-full bg-amber-500 px-2.5 py-1 text-xs font-bold text-white shadow">★ Eng yaxshi</span>}
        <div className="absolute inset-x-4 bottom-3 flex items-end justify-between gap-2">
          <p className="truncate text-base font-extrabold text-white drop-shadow">{venue.name} <PaidBadge verified={venue.is_verified} /></p>
          <StatsLine stats={venue.stats} light className="shrink-0 rounded-full bg-slate-950/45 px-2.5 py-1 backdrop-blur" />
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4 text-sm">
        <p className="flex items-center gap-1 text-muted-foreground">
          <MapPinIcon className="size-3.5 shrink-0" aria-hidden />
          <span className="truncate">
            {REGION_LABELS[venue.region]}
            {venue.district && `, ${venue.district}`}
          </span>
        </p>
        <p className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1 text-muted-foreground">
            <UsersIcon className="size-3.5" aria-hidden /> {venue.capacity_max} kishigacha
          </span>
          <b>{formatMoney(venue.base_price)} dan</b>
        </p>
        <span className="mt-auto flex items-center gap-1 pt-1 font-semibold text-brand dark:text-cyan-300">
          Grafik va izohlar <ChevronRightIcon className="size-4 transition group-hover:translate-x-0.5" />
        </span>
      </div>
    </Link>
  );
}
