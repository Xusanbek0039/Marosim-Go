"use client";

import { BadgeCheckIcon, ClapperboardIcon, MessageCircleIcon, SparklesIcon, ThumbsUpIcon } from "lucide-react";
import Link from "next/link";

import { cn } from "./ui";

const PERKS = [
  { icon: ClapperboardIcon, text: "Reels formatidagi vertikal videolar" },
  { icon: ThumbsUpIcon, text: "Mijozlardan like, dislike va izohlar" },
  { icon: MessageCircleIcon, text: "Mijozlar studiyaga to'g'ridan-to'g'ri yozadi" },
  { icon: BadgeCheckIcon, text: "Katalogda ishonch belgisi — galichka" },
];

/** Shown where a galichka-only feature would be: explains what the badge unlocks and links to buying it. */
export function BadgeUpsell({ title, compact, className }: { title?: string; compact?: boolean; className?: string }) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-3xl border border-cyan-500/30 bg-gradient-to-br from-fuchsia-600/15 via-blue-600/10 to-cyan-500/20 p-5 sm:p-6",
        className,
      )}
    >
      <SparklesIcon className="pointer-events-none absolute -top-4 -right-4 size-28 text-cyan-500/10" aria-hidden />
      <div className="relative flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <span className="brand-gradient inline-flex size-11 shrink-0 items-center justify-center rounded-2xl text-white shadow-lg">
            <BadgeCheckIcon className="size-6" aria-hidden />
          </span>
          <div>
            <h3 className="text-lg font-extrabold tracking-tight">{title ?? "Galichka bilan ko'proq mijoz"}</h3>
            <p className="text-sm text-muted-foreground">
              Bu imkoniyatlar faqat galichkasi faol studiyalarda ishlaydi. Galichka oling — portfolio jonlanadi.
            </p>
          </div>
        </div>
        {!compact && (
          <ul className="grid gap-2 sm:grid-cols-2">
            {PERKS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-2 rounded-2xl bg-background/60 px-3 py-2 text-sm font-medium">
                <Icon className="size-4 shrink-0 text-cyan-600 dark:text-cyan-300" aria-hidden /> {text}
              </li>
            ))}
          </ul>
        )}
        <Link
          href="/galichka"
          className="brand-gradient inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl px-5 text-sm font-bold text-white shadow-[0_10px_24px_-12px_rgb(37_99_235/0.85)] transition hover:brightness-110 sm:w-max"
        >
          <BadgeCheckIcon className="size-4" aria-hidden /> Galichka sotib olish
        </Link>
      </div>
    </div>
  );
}
