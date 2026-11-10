"use client";

import {
  ChevronDownIcon,
  ChevronUpIcon,
  MessageCircleIcon,
  PlayIcon,
  SendIcon,
  ThumbsDownIcon,
  ThumbsUpIcon,
  Trash2Icon,
  Volume2Icon,
  VolumeXIcon,
  XIcon,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { type PortfolioItem, useAddComment, useComments, useDeleteMyComment, useReact } from "@/lib/studios";

import { cn, Skeleton } from "./ui";

const clock = (sec: number) => `${Math.floor(sec / 60)}:${String(Math.round(sec % 60)).padStart(2, "0")}`;
const errorText = (e: unknown, fallback: string) =>
  e instanceof ApiError ? (e.code === "badge_required" ? "Bu studiyada hozir bu imkoniyat o'chiq." : (e.fieldErrors.text ?? e.message)) : fallback;
const compact = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(n >= 10_000 ? 0 : 1)}K` : String(n));

/** Row of 9:16 reel cards; a tap opens the full-screen viewer. */
export function ReelsStrip({ studioId, items, studioName }: { studioId: string; items: PortfolioItem[]; studioName: string }) {
  const [start, setStart] = useState<number | null>(null);
  if (items.length === 0) return null;
  return (
    <>
      <ul className="-mx-1 flex snap-x snap-mandatory gap-3 overflow-x-auto px-1 pb-2">
        {items.map((item, i) => (
          <li key={item.id} className="w-36 shrink-0 snap-start sm:w-44">
            <button
              type="button"
              onClick={() => setStart(i)}
              className="group relative block aspect-[9/16] w-full overflow-hidden rounded-2xl bg-slate-900 text-left shadow-lg"
              aria-label={`${i + 1}-reelsni ko'rish`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side */}
              <img src={item.image} alt="" className="size-full object-cover transition duration-500 group-hover:scale-105" />
              <span className="absolute inset-0 bg-gradient-to-t from-slate-950/85 via-transparent to-slate-950/20" aria-hidden />
              <span className="absolute top-2 left-2 flex items-center gap-1 rounded-full bg-slate-950/55 px-2 py-0.5 text-[11px] font-bold text-white backdrop-blur">
                <PlayIcon className="size-3 fill-current" aria-hidden /> {clock(item.duration)}
              </span>
              <span className="absolute inset-x-2.5 bottom-2.5 flex flex-col gap-1">
                {item.caption && <span className="line-clamp-2 text-xs font-semibold text-white">{item.caption}</span>}
                <span className="flex items-center gap-2 text-[11px] font-bold text-white">
                  <span className="flex items-center gap-0.5"><ThumbsUpIcon className="size-3" aria-hidden /> {compact(item.engagement.like_count)}</span>
                  <span className="flex items-center gap-0.5"><MessageCircleIcon className="size-3" aria-hidden /> {compact(item.engagement.comment_count)}</span>
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      {start !== null && <PortfolioViewer studioId={studioId} studioName={studioName} items={items} start={start} onClose={() => setStart(null)} />}
    </>
  );
}

/** Photo grid with likes / comments (used when the studio's galichka is active). */
export function EngagedPhotoGrid({ studioId, items, studioName }: { studioId: string; items: PortfolioItem[]; studioName: string }) {
  const [start, setStart] = useState<number | null>(null);
  if (items.length === 0) return null;
  return (
    <>
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {items.map((img, i) => (
          <li key={img.id} className={i === 0 ? "col-span-2 row-span-2" : undefined}>
            <button type="button" onClick={() => setStart(i)} className="group relative block size-full overflow-hidden rounded-2xl" aria-label={`${i + 1}-rasmni ochish`}>
              {/* eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side */}
              <img src={img.image} alt="" className="aspect-[4/3] size-full object-cover transition duration-500 group-hover:scale-105" />
              <span className="absolute right-2 bottom-2 flex items-center gap-2 rounded-full bg-slate-950/55 px-2 py-0.5 text-[11px] font-bold text-white backdrop-blur">
                <span className="flex items-center gap-0.5"><ThumbsUpIcon className="size-3" aria-hidden /> {compact(img.engagement.like_count)}</span>
                <span className="flex items-center gap-0.5"><MessageCircleIcon className="size-3" aria-hidden /> {compact(img.engagement.comment_count)}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      {start !== null && <PortfolioViewer studioId={studioId} studioName={studioName} items={items} start={start} onClose={() => setStart(null)} />}
    </>
  );
}

/**
 * Full-screen, vertically snapping viewer (Reels / Shorts style). The visible slide plays, the rest
 * pause; ↑/↓ or swipe moves between items, Esc closes. Counts come from the cached studio profile,
 * so the strip / grid update together with the viewer.
 */
export function PortfolioViewer({
  studioId,
  studioName,
  items,
  start,
  onClose,
}: {
  studioId: string;
  studioName: string;
  items: PortfolioItem[];
  start: number;
  onClose: () => void;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(start);
  const [muted, setMuted] = useState(true);
  const [commentsFor, setCommentsFor] = useState<string | null>(null);

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTo({ top: start * el.clientHeight });
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [start]);

  const go = (d: number) => {
    const el = scroller.current;
    if (!el) return;
    const next = Math.min(items.length - 1, Math.max(0, active + d));
    el.scrollTo({ top: next * el.clientHeight, behavior: "smooth" });
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest("input, textarea")) return;
      if (e.key === "Escape") {
        if (commentsFor) setCommentsFor(null);
        else onClose();
      } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        go(e.key === "ArrowDown" ? 1 : -1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const onScroll = () => {
    const el = scroller.current;
    if (!el) return;
    const i = Math.round(el.scrollTop / el.clientHeight);
    if (i !== active) setActive(i);
  };

  if (typeof document === "undefined") return null;
  return createPortal(
    <motion.div className="fixed inset-0 z-50 bg-black" initial={{ opacity: 0 }} animate={{ opacity: 1 }} role="dialog" aria-modal="true" aria-label={`${studioName} — portfolio`}>
      <div ref={scroller} onScroll={onScroll} className="h-dvh snap-y snap-mandatory overflow-y-scroll overscroll-contain [scrollbar-width:none]">
        {items.map((item, i) => (
          <Slide
            key={item.id}
            studioId={studioId}
            studioName={studioName}
            item={item}
            active={i === active}
            muted={muted}
            onToggleMute={() => setMuted((m) => !m)}
            onComments={() => setCommentsFor(item.id)}
          />
        ))}
      </div>

      <button type="button" onClick={onClose} aria-label="Yopish" className="absolute top-4 right-4 z-10 inline-flex size-11 items-center justify-center rounded-full bg-white/15 text-white backdrop-blur hover:bg-white/25">
        <XIcon className="size-5" />
      </button>
      {items.length > 1 && (
        <div className="absolute top-1/2 right-4 z-10 hidden -translate-y-1/2 flex-col gap-2 md:flex">
          <button type="button" disabled={active === 0} onClick={() => go(-1)} aria-label="Oldingi" className="inline-flex size-11 items-center justify-center rounded-full bg-white/15 text-white backdrop-blur hover:bg-white/25 disabled:opacity-30">
            <ChevronUpIcon className="size-5" />
          </button>
          <button type="button" disabled={active === items.length - 1} onClick={() => go(1)} aria-label="Keyingi" className="inline-flex size-11 items-center justify-center rounded-full bg-white/15 text-white backdrop-blur hover:bg-white/25 disabled:opacity-30">
            <ChevronDownIcon className="size-5" />
          </button>
        </div>
      )}

      <AnimatePresence>
        {commentsFor && <CommentsSheet key={commentsFor} studioId={studioId} itemId={commentsFor} onClose={() => setCommentsFor(null)} />}
      </AnimatePresence>
    </motion.div>,
    document.body,
  );
}

function Slide({
  studioId,
  studioName,
  item,
  active,
  muted,
  onToggleMute,
  onComments,
}: {
  studioId: string;
  studioName: string;
  item: PortfolioItem;
  active: boolean;
  muted: boolean;
  onToggleMute: () => void;
  onComments: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const [paused, setPaused] = useState(false);
  const [progress, setProgress] = useState(0);
  const react = useReact(studioId);
  const e = item.engagement;

  useEffect(() => {
    const el = video.current;
    if (!el) return;
    if (active) {
      el.currentTime = 0;
      void el.play().catch(() => setPaused(true));
    } else el.pause();
  }, [active]);

  const toggle = () => {
    const el = video.current;
    if (!el) return;
    if (el.paused) void el.play().then(() => setPaused(false)).catch(() => undefined);
    else {
      el.pause();
      setPaused(true);
    }
  };

  const vote = (value: "like" | "dislike") =>
    react.mutate(
      { itemId: item.id, value: e.my_reaction === value ? null : value },
      { onError: (err) => toast.error(errorText(err, "Saqlanmadi")) },
    );

  return (
    <section className="relative flex h-dvh snap-start snap-always items-center justify-center">
      <div className="relative h-full w-full max-w-[min(100vw,calc(100dvh*9/16))] overflow-hidden bg-slate-950 sm:rounded-none">
        {item.kind === "VIDEO" && item.video ? (
          <>
            <video
              ref={video}
              src={active ? item.video : undefined}
              poster={item.image}
              muted={muted}
              loop
              playsInline
              preload={active ? "auto" : "none"}
              controls={false}
              disablePictureInPicture
              controlsList="nodownload"
              onContextMenu={(ev) => ev.preventDefault()}
              onClick={toggle}
              onTimeUpdate={(ev) => setProgress(ev.currentTarget.duration ? ev.currentTarget.currentTime / ev.currentTarget.duration : 0)}
              className="size-full object-cover"
            />
            {paused && (
              <button type="button" onClick={toggle} aria-label="Ijro etish" className="absolute inset-0 m-auto flex size-20 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur">
                <PlayIcon className="ml-1 size-9 fill-current" />
              </button>
            )}
            <div className="absolute inset-x-0 bottom-0 h-1 bg-white/20">
              <div className="h-full bg-white transition-[width] duration-200" style={{ width: `${progress * 100}%` }} />
            </div>
            <button type="button" onClick={onToggleMute} aria-label={muted ? "Ovozni yoqish" : "Ovozni o'chirish"} className="absolute top-4 left-4 inline-flex size-10 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur">
              {muted ? <VolumeXIcon className="size-5" /> : <Volume2Icon className="size-5" />}
            </button>
          </>
        ) : (
          // eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side
          <img src={item.image} alt="" className="size-full object-contain" />
        )}

        <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent px-4 pt-24 pb-6 pr-20 text-white">
          <p className="font-bold">{studioName}</p>
          {item.caption && <p className="mt-1 line-clamp-3 text-sm whitespace-pre-line text-white/90">{item.caption}</p>}
        </div>

        <div className="absolute right-3 bottom-8 flex flex-col items-center gap-5 text-white">
          <Action label="Like" count={e.like_count} on={e.my_reaction === "like"} onClick={() => vote("like")} disabled={react.isPending}>
            <ThumbsUpIcon className={cn("size-7", e.my_reaction === "like" && "fill-current")} />
          </Action>
          <Action label="Dislike" count={e.dislike_count} on={e.my_reaction === "dislike"} onClick={() => vote("dislike")} disabled={react.isPending}>
            <ThumbsDownIcon className={cn("size-7", e.my_reaction === "dislike" && "fill-current")} />
          </Action>
          <Action label="Izohlar" count={e.comment_count} onClick={onComments}>
            <MessageCircleIcon className="size-7" />
          </Action>
        </div>
      </div>
    </section>
  );
}

function Action({
  label,
  count,
  on,
  onClick,
  disabled,
  children,
}: {
  label: string;
  count: number;
  on?: boolean;
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label} aria-pressed={on} className="flex flex-col items-center gap-1 drop-shadow-lg">
      <motion.span whileTap={{ scale: 0.8 }} className={cn("inline-flex size-12 items-center justify-center rounded-full bg-black/35 backdrop-blur transition", on && "text-cyan-300")}>
        {children}
      </motion.span>
      <span className="text-xs font-bold tabular-nums">{compact(count)}</span>
    </button>
  );
}

function CommentsSheet({ studioId, itemId, onClose }: { studioId: string; itemId: string; onClose: () => void }) {
  const comments = useComments(studioId, itemId);
  const add = useAddComment(studioId, itemId);
  const remove = useDeleteMyComment(studioId, itemId);
  const [text, setText] = useState("");

  const submit = () => {
    const body = text.trim();
    if (!body) return;
    add.mutate(body, { onSuccess: () => setText(""), onError: (e) => toast.error(errorText(e, "Izoh yuborilmadi")) });
  };

  return (
    <>
      <motion.div className="absolute inset-0 z-20 bg-black/40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
      <motion.div
        className="glass-strong absolute inset-x-0 bottom-0 z-30 mx-auto flex max-h-[70dvh] w-full max-w-lg flex-col rounded-t-3xl"
        initial={{ y: "100%" }}
        animate={{ y: 0, transition: { type: "spring", stiffness: 380, damping: 36 } }}
        exit={{ y: "100%", transition: { duration: 0.18 } }}
        role="dialog"
        aria-label="Izohlar"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <h2 className="font-bold">Izohlar {comments.data ? `(${comments.data.length})` : ""}</h2>
          <button type="button" onClick={onClose} aria-label="Yopish" className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted">
            <XIcon className="size-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-3">
          {comments.isPending ? (
            <Skeleton className="h-20 rounded-xl" />
          ) : comments.error ? (
            <p className="text-sm text-danger">{errorText(comments.error, "Izohlarni yuklab bo'lmadi")}</p>
          ) : comments.data.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Birinchi bo&apos;lib izoh qoldiring.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {comments.data.map((c) => (
                <li key={c.id} className="flex items-start justify-between gap-2">
                  <div className="min-w-0 text-sm">
                    <p className="font-semibold">
                      {c.author_name} <span className="text-xs font-normal text-muted-foreground">{formatDateTime(c.created_at)}</span>
                    </p>
                    <p className="break-words whitespace-pre-line">{c.text}</p>
                  </div>
                  {c.is_mine && (
                    <button type="button" aria-label="Izohni o'chirish" onClick={() => remove.mutate(c.id)} className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-danger">
                      <Trash2Icon className="size-4" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
        <form
          className="flex items-center gap-2 border-t border-border p-3"
          onSubmit={(ev) => {
            ev.preventDefault();
            submit();
          }}
        >
          <input
            value={text}
            maxLength={500}
            onChange={(ev) => setText(ev.target.value)}
            placeholder="Izoh yozing…"
            aria-label="Izoh"
            className="h-11 flex-1 rounded-xl border border-border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-cyan-500/40"
          />
          <button type="submit" disabled={!text.trim() || add.isPending} aria-label="Yuborish" className="brand-gradient inline-flex size-11 items-center justify-center rounded-xl text-white disabled:opacity-50">
            <SendIcon className="size-4" />
          </button>
        </form>
      </motion.div>
    </>
  );
}
