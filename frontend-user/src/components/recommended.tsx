"use client";

import { ChevronRightIcon } from "lucide-react";
import Link from "next/link";

import { usePublicStudios } from "@/lib/studios";
import { useVenueCatalog } from "@/lib/venues";

import { StudioAdCard, VenueAdCard } from "./ad-cards";

function Strip({ title, href, children }: { title: string; href: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2" aria-label={title}>
      <div className="flex items-center justify-between px-1">
        <h2 className="text-base font-bold">{title}</h2>
        <Link href={href} className="flex items-center gap-0.5 text-sm font-semibold text-brand dark:text-cyan-300">
          Barchasi <ChevronRightIcon className="size-4" />
        </Link>
      </div>
      <ul className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-2 sm:mx-0 sm:px-0">{children}</ul>
    </section>
  );
}

/** Home-page "ads": best rated venues and studios. Hidden while loading or when there are none. */
export function Recommended() {
  const venues = useVenueCatalog();
  const studios = usePublicStudios("");
  return (
    <>
      {venues.data && venues.data.length > 0 && (
        <Strip title="Tavsiya etilgan to'yxonalar" href="/toyxonalar">
          {venues.data.slice(0, 8).map((v, i) => (
            <li key={v.id} className="w-64 shrink-0 snap-start">
              <VenueAdCard venue={v} top={i === 0 && v.stats.rating_count > 0} />
            </li>
          ))}
        </Strip>
      )}
      {studios.data && studios.data.length > 0 && (
        <Strip title="Tavsiya etilgan studiyalar" href="/studiyalar">
          {studios.data.slice(0, 8).map((s, i) => (
            <li key={s.id} className="w-72 shrink-0 snap-start">
              <StudioAdCard studio={s} top={i === 0 && s.stats.rating_count > 0} />
            </li>
          ))}
        </Strip>
      )}
    </>
  );
}
