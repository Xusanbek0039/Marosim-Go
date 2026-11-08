"use client";

import { ChevronLeftIcon, ChevronRightIcon, CrownIcon, DownloadIcon, FilmIcon, ImageIcon, Loader2Icon, PlayIcon, XIcon } from "lucide-react";
import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { downloadUrl, streamUrl, thumbUrl, useCeremonyMedia } from "@/lib/sharing";
import type { MyMedia } from "@/lib/types";

import { Card, cn, EmptyState, ErrorState, Skeleton } from "./ui";
import { VideoPlayer } from "./video-player";

/** Browsers other than Safari cannot render HEIC: show Drive's (JPEG) preview instead of the original. */
const BROWSER_IMAGE = new Set(["image/jpeg", "image/png", "image/webp"]);

function duration(ms: number | null) {
  if (!ms) return "";
  const s = Math.round(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

function Thumb({ ceremonyId, media, className }: { ceremonyId: string; media: MyMedia; className?: string }) {
  const [failed, setFailed] = useState(false);
  // The first preview request is fetched from Google Drive (a few seconds): pulse until it arrives.
  const [loaded, setLoaded] = useState(false);
  const Icon = media.kind === "VIDEO" ? FilmIcon : ImageIcon;
  return failed ? (
    <span className={cn("flex items-center justify-center bg-gradient-to-br from-blue-600/25 to-cyan-500/25 text-cyan-700 dark:text-cyan-300", className)}>
      <Icon className="size-8" aria-hidden />
    </span>
  ) : (
    // eslint-disable-next-line @next/next/no-img-element -- authenticated same-origin media, not optimisable by next/image
    <img
      src={thumbUrl(ceremonyId, media.id)}
      alt=""
      loading="lazy"
      onLoad={() => setLoaded(true)}
      onError={() => setFailed(true)}
      className={cn("object-cover", !loaded && "animate-pulse bg-muted", className)}
    />
  );
}

function Viewer({
  ceremonyId,
  items,
  index,
  onIndex,
  onClose,
}: {
  ceremonyId: string;
  items: MyMedia[];
  index: number;
  onIndex: (i: number) => void;
  onClose: () => void;
}) {
  const media = items[index];
  const go = useCallback((d: number) => onIndex((index + d + items.length) % items.length), [index, items.length, onIndex]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") go(1);
      if (e.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, onClose]);

  const blockSave = media.can_download ? undefined : (e: React.MouseEvent) => e.preventDefault();
  // Bytes come from Google Drive through the server: show a spinner until the current item is ready.
  const [readyId, setReadyId] = useState<string | null>(null);
  const ready = readyId === media.id;

  return (
    <motion.div
      className="fixed inset-0 z-50 flex flex-col bg-slate-950/92 backdrop-blur-md"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      role="dialog"
      aria-modal="true"
      aria-label="Ko'rish"
    >
      <div className="flex items-center justify-between gap-3 p-3 text-white">
        <span className="text-sm tabular-nums opacity-80">
          {index + 1} / {items.length}
        </span>
        <div className="flex items-center gap-1">
          {media.can_download && (
            <a href={downloadUrl(ceremonyId, media.id)} className="inline-flex h-10 items-center gap-2 rounded-xl px-3 text-sm font-semibold hover:bg-white/10" download>
              <DownloadIcon className="size-4" /> Yuklab olish
            </a>
          )}
          <button type="button" onClick={onClose} aria-label="Yopish" className="inline-flex size-10 items-center justify-center rounded-xl hover:bg-white/10">
            <XIcon className="size-5" />
          </button>
        </div>
      </div>
      <div className="relative flex min-h-0 flex-1 items-center justify-center px-2 pb-6 sm:px-16" onContextMenu={blockSave}>
        {!ready && !(media.kind === "VIDEO" && media.processing) && <Loader2Icon className="absolute size-10 animate-spin text-white/60" aria-label="Yuklanmoqda" />}
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={media.id}
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.97 }}
            transition={{ duration: 0.18 }}
            className="flex size-full items-center justify-center"
          >
            {media.kind === "VIDEO" && media.processing ? (
              <div className="flex max-w-sm flex-col items-center gap-3 rounded-2xl bg-white/5 p-8 text-center text-white">
                <Loader2Icon className="size-10 animate-spin text-cyan-300" aria-hidden />
                <p className="font-semibold">Video tayyorlanmoqda{media.progress != null && <span className="tabular-nums"> — {media.progress}%</span>}</p>
                {media.progress != null && (
                  <div className="h-1.5 w-56 overflow-hidden rounded-full bg-white/10">
                    <div className="h-full rounded-full bg-cyan-300 transition-[width] duration-700" style={{ width: `${Math.max(3, media.progress)}%` }} />
                  </div>
                )}
                <p className="text-sm text-white/70">
                  {media.progress == null ? "Navbatda turibdi, tez orada boshlanadi." : "MarosimGo logosi qo'shilmoqda."} Sahifa o&apos;zi yangilanadi.
                </p>
              </div>
            ) : media.kind === "VIDEO" ? (
              <VideoPlayer
                key={media.id}
                src={streamUrl(ceremonyId, media.id)}
                poster={thumbUrl(ceremonyId, media.id, 960)}
                allowDownload={media.can_download}
                onReady={() => setReadyId(media.id)}
              />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element -- authenticated same-origin media
              <img
                src={BROWSER_IMAGE.has(media.mime_type) || media.watermarked ? streamUrl(ceremonyId, media.id) : thumbUrl(ceremonyId, media.id, 960)}
                alt=""
                draggable={media.can_download}
                onContextMenu={blockSave}
                onLoad={() => setReadyId(media.id)}
                className={cn("max-h-full max-w-full rounded-2xl object-contain transition-opacity", ready ? "opacity-100" : "opacity-0")}
              />
            )}
          </motion.div>
        </AnimatePresence>
        {items.length > 1 && (
          <>
            <button type="button" onClick={() => go(-1)} aria-label="Oldingi" className="absolute top-1/2 left-2 inline-flex size-11 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20">
              <ChevronLeftIcon className="size-5" />
            </button>
            <button type="button" onClick={() => go(1)} aria-label="Keyingi" className="absolute top-1/2 right-2 inline-flex size-11 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20">
              <ChevronRightIcon className="size-5" />
            </button>
          </>
        )}
      </div>
    </motion.div>
  );
}

export function Gallery({ ceremonyId, isOwner }: { ceremonyId: string; isOwner: boolean }) {
  const { data, error, isPending, refetch } = useCeremonyMedia(ceremonyId);
  const watermarked = (data ?? []).some((m) => m.watermarked);
  const [open, setOpen] = useState<number | null>(null);
  const items = data ?? [];
  // Videos first (the main product), then photos; the viewer pages through both in this order.
  const ordered = [...items.filter((m) => m.kind === "VIDEO"), ...items.filter((m) => m.kind === "PHOTO")];
  const videos = ordered.filter((m) => m.kind === "VIDEO");
  const photos = ordered.filter((m) => m.kind === "PHOTO");

  return (
    <Card className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold">Video va rasmlar</h2>
          <p className="text-sm text-muted-foreground">
            {isOwner ? "Faqat siz va siz ruxsat bergan odamlar ko'radi." : "Sizga ko'rish uchun ruxsat berilgan. Yuklab olish mumkin emas."}
          </p>
        </div>
        {items.length > 0 && (
          <span className="text-sm text-muted-foreground tabular-nums">
            {videos.length} video · {photos.length} rasm
          </span>
        )}
      </div>

      {isOwner && watermarked && (
        <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-amber-400/40 bg-amber-500/[0.08] p-3.5">
          <CrownIcon className="size-5 shrink-0 text-amber-500" aria-hidden />
          <p className="min-w-0 flex-1 text-sm">
            Video va rasmlar <b>MarosimGo logosi</b> bilan ko&apos;rsatilmoqda. Obuna bilan logosiz ko&apos;rasiz, yuklab olasiz va ko&apos;proq odamga ruxsat berasiz.
          </p>
          <Link href="/obuna" className="inline-flex h-9 items-center rounded-xl px-3 text-[13px] font-semibold brand-gradient text-white">
            Obuna olish
          </Link>
        </div>
      )}

      {isPending ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="aspect-video rounded-2xl" />
          ))}
        </div>
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : items.length === 0 ? (
        <EmptyState title="Hali fayl yo'q" description="Studiya montaj qilingan video va rasmlarni yuklagach, ular shu yerda ko'rinadi." />
      ) : (
        <>
          {videos.length > 0 && (
            <ul className="grid gap-3 sm:grid-cols-2">
              {videos.map((m) => (
                <li key={m.id}>
                  <button type="button" onClick={() => setOpen(ordered.indexOf(m))} className="group relative block aspect-video w-full overflow-hidden rounded-2xl">
                    <Thumb ceremonyId={ceremonyId} media={m} className="size-full transition duration-500 group-hover:scale-105" />
                    <span className="absolute inset-0 bg-gradient-to-t from-slate-950/60 to-transparent" />
                    <span className="absolute top-1/2 left-1/2 flex size-14 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-blue-700 shadow-xl transition group-hover:scale-110">
                      <PlayIcon className="ml-0.5 size-6 fill-current" />
                    </span>
                    {m.processing && (
                      <span className="absolute top-2 left-2 flex items-center gap-1 rounded-full bg-slate-950/70 px-2 py-0.5 text-[11px] font-semibold text-white">
                        <Loader2Icon className="size-3 animate-spin" /> Tayyorlanmoqda{m.progress != null && <span className="tabular-nums"> {m.progress}%</span>}
                      </span>
                    )}
                    {m.duration_ms && <span className="absolute right-3 bottom-2 text-xs font-bold text-white tabular-nums">{duration(m.duration_ms)}</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {photos.length > 0 && (
            <ul className="grid grid-cols-3 gap-1.5 sm:grid-cols-4 sm:gap-2">
              {photos.map((m) => (
                <li key={m.id}>
                  <button type="button" onClick={() => setOpen(ordered.indexOf(m))} className="group block aspect-square w-full overflow-hidden rounded-xl" aria-label="Rasmni ochish">
                    <Thumb ceremonyId={ceremonyId} media={m} className="size-full transition duration-500 group-hover:scale-105" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {/* Portal: the Card's transform / backdrop-filter would otherwise trap this fixed overlay inside the card. */}
      {typeof document !== "undefined" &&
        createPortal(
          <AnimatePresence>
            {open !== null && ordered[open] && (
              <Viewer ceremonyId={ceremonyId} items={ordered} index={open} onIndex={setOpen} onClose={() => setOpen(null)} />
            )}
          </AnimatePresence>,
          document.body,
        )}
    </Card>
  );
}
