"use client";

import {
  ClapperboardIcon,
  ImageIcon,
  ImagePlusIcon,
  LockIcon,
  MessageCircleIcon,
  PencilIcon,
  PlayIcon,
  ThumbsDownIcon,
  ThumbsUpIcon,
  Trash2Icon,
  UploadIcon,
  XIcon,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { BadgeUpsell } from "@/components/badge-upsell";
import { PaidBadge } from "@/components/paid-badge";
import { PageTitle } from "@/components/shell";
import { Button, Card, cn, EmptyState, ErrorState, Field, Modal, Skeleton, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  MAX_PORTFOLIO_IMAGES,
  MAX_PORTFOLIO_REELS,
  type PortfolioItem,
  REEL_LIMITS,
  useDeleteComment,
  useDeletePortfolio,
  useItemComments,
  useMyStudios,
  usePortfolio,
  useUpdateCaption,
  useUploadPortfolio,
  useUploadReel,
} from "@/lib/studio";
import type { MyStudioMembership } from "@/lib/types";

const MAX_BYTES = 5 * 1024 * 1024;
const errorText = (e: unknown, fallback: string) => {
  if (!(e instanceof ApiError)) return fallback;
  if (e.code === "badge_required") return "Bu imkoniyat uchun galichka kerak.";
  const f = e.fieldErrors;
  return f.video ?? f.poster ?? f.image ?? f.caption ?? e.message;
};
const clock = (sec: number) => `${Math.floor(sec / 60)}:${String(Math.round(sec % 60)).padStart(2, "0")}`;

type Tab = "reels" | "photos";

function StudioPortfolio({ membership }: { membership: MyStudioMembership }) {
  const { studio, can_manage } = membership;
  const verified = studio.is_verified;
  const { data, error, isPending, refetch } = usePortfolio(studio.id);
  const [tab, setTab] = useState<Tab>("reels");
  const [open, setOpen] = useState<PortfolioItem | null>(null);
  const [uploading, setUploading] = useState(false);

  const reels = data?.filter((i) => i.kind === "VIDEO") ?? [];
  const photos = data?.filter((i) => i.kind === "IMAGE") ?? [];
  const totals = (data ?? []).reduce(
    (t, i) => ({ like: t.like + i.engagement.like_count, comment: t.comment + i.engagement.comment_count }),
    { like: 0, comment: 0 },
  );

  return (
    <Card className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-1.5 text-lg font-bold">
            {studio.name} <PaidBadge verified={verified} />
          </h2>
          <p className="text-sm text-muted-foreground">
            {reels.length} ta reels · {photos.length} ta rasm
            {verified && (
              <>
                {" "}· <ThumbsUpIcon className="inline size-3.5" aria-hidden /> {totals.like} · <MessageCircleIcon className="inline size-3.5" aria-hidden /> {totals.comment}
              </>
            )}
          </p>
        </div>
        <div className="glass flex rounded-2xl p-1" role="tablist" aria-label="Portfolio turi">
          {(
            [
              ["reels", "Reels", ClapperboardIcon],
              ["photos", "Rasmlar", ImageIcon],
            ] as const
          ).map(([key, label, Icon]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={cn(
                "flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold transition",
                tab === key ? "brand-gradient text-white" : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="size-4" aria-hidden /> {label}
            </button>
          ))}
        </div>
      </div>

      {!verified && <BadgeUpsell />}

      {isPending ? (
        <Skeleton className="h-60 rounded-2xl" />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : tab === "reels" ? (
        <ReelsGrid
          items={reels}
          canUpload={can_manage && verified && reels.length < MAX_PORTFOLIO_REELS}
          locked={!verified}
          onOpen={setOpen}
          onUpload={() => setUploading(true)}
        />
      ) : (
        <PhotosGrid studioId={studio.id} items={photos} canManage={can_manage} verified={verified} onOpen={setOpen} />
      )}

      <Modal open={uploading} onClose={() => setUploading(false)} title="Reels yuklash">
        <ReelUploadForm studioId={studio.id} onDone={() => setUploading(false)} />
      </Modal>
      <Modal open={Boolean(open)} onClose={() => setOpen(null)} title={open?.kind === "VIDEO" ? "Reels" : "Rasm"}>
        {open && <ItemDetail studioId={studio.id} item={open} canManage={can_manage} verified={verified} onClose={() => setOpen(null)} />}
      </Modal>
    </Card>
  );
}

function Stats({ item, light }: { item: PortfolioItem; light?: boolean }) {
  const e = item.engagement;
  return (
    <span className={cn("flex items-center gap-2.5 text-xs font-bold", light ? "text-white" : "text-muted-foreground")}>
      <span className="flex items-center gap-1"><ThumbsUpIcon className="size-3.5" aria-hidden /> {e.like_count}</span>
      <span className="flex items-center gap-1"><ThumbsDownIcon className="size-3.5" aria-hidden /> {e.dislike_count}</span>
      <span className="flex items-center gap-1"><MessageCircleIcon className="size-3.5" aria-hidden /> {e.comment_count}</span>
    </span>
  );
}

function ReelsGrid({
  items,
  canUpload,
  locked,
  onOpen,
  onUpload,
}: {
  items: PortfolioItem[];
  canUpload: boolean;
  locked: boolean;
  onOpen: (i: PortfolioItem) => void;
  onUpload: () => void;
}) {
  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {canUpload && (
        <li>
          <button
            type="button"
            onClick={onUpload}
            className="flex aspect-[9/16] w-full flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-cyan-500/40 bg-cyan-500/5 text-sm font-semibold text-cyan-700 transition hover:bg-cyan-500/10 dark:text-cyan-300"
          >
            <UploadIcon className="size-7" aria-hidden />
            Reels qo&apos;shish
            <span className="px-3 text-center text-xs font-normal text-muted-foreground">9:16 · {REEL_LIMITS.maxSeconds} soniyagacha · 100 MB</span>
          </button>
        </li>
      )}
      {items.length === 0 && !canUpload && (
        <li className="col-span-full">
          <EmptyState
            title={locked ? "Reels galichka bilan ochiladi" : "Hali reels yo'q"}
            description={locked ? "Galichka olgach, vertikal videolaringizni joylay olasiz." : "Eng yaxshi kadrlaringizdan qisqa vertikal videolar qo'shing."}
          />
        </li>
      )}
      <AnimatePresence initial={false}>
        {items.map((item) => (
          <motion.li key={item.id} layout initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.94 }}>
            <button
              type="button"
              onClick={() => onOpen(item)}
              className="group relative block aspect-[9/16] w-full overflow-hidden rounded-2xl bg-slate-900 text-left"
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side */}
              <img src={item.image} alt="" className="size-full object-cover transition duration-500 group-hover:scale-105" />
              <span className="absolute inset-0 bg-gradient-to-t from-slate-950/85 via-transparent to-slate-950/30" aria-hidden />
              <span className="absolute top-2 left-2 flex items-center gap-1 rounded-full bg-slate-950/55 px-2 py-0.5 text-[11px] font-bold text-white backdrop-blur">
                <PlayIcon className="size-3 fill-current" aria-hidden /> {clock(item.duration)}
              </span>
              {locked && (
                <span className="absolute top-2 right-2 rounded-full bg-amber-500/90 p-1 text-white" title="Galichka tugagan — mijozlarga ko'rinmaydi">
                  <LockIcon className="size-3.5" aria-hidden />
                </span>
              )}
              <span className="absolute inset-x-2.5 bottom-2.5 flex flex-col gap-1.5">
                {item.caption && <span className="line-clamp-2 text-xs font-semibold text-white">{item.caption}</span>}
                <Stats item={item} light />
              </span>
            </button>
          </motion.li>
        ))}
      </AnimatePresence>
    </ul>
  );
}

function PhotosGrid({
  studioId,
  items,
  canManage,
  verified,
  onOpen,
}: {
  studioId: string;
  items: PortfolioItem[];
  canManage: boolean;
  verified: boolean;
  onOpen: (i: PortfolioItem) => void;
}) {
  const upload = useUploadPortfolio(studioId);
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const left = MAX_PORTFOLIO_IMAGES - items.length;

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
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          {items.length}/{MAX_PORTFOLIO_IMAGES} rasm · mijozlar studiya profilida ko&apos;radi
        </p>
        {canManage && left > 0 && (
          <>
            <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={(e) => (add(e.target.files), (e.target.value = ""))} />
            <Button onClick={() => input.current?.click()} loading={busy}>
              <ImagePlusIcon /> Rasm qo&apos;shish
            </Button>
          </>
        )}
      </div>
      {items.length === 0 ? (
        <EmptyState title="Rasmlar yo'q" description="Eng yaxshi ishlaringizdan suratlar qo'shing — ular reklama kartangizda chiqadi." />
      ) : (
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <AnimatePresence initial={false}>
            {items.map((img) => (
              <motion.li key={img.id} layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
                <button type="button" onClick={() => onOpen(img)} className="group relative block aspect-square w-full overflow-hidden rounded-xl">
                  {/* eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side */}
                  <img src={img.image} alt="" className="size-full object-cover transition group-hover:scale-105" />
                  {verified && (
                    <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950/75 to-transparent px-2 pt-6 pb-1.5">
                      <Stats item={img} light />
                    </span>
                  )}
                </button>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </div>
  );
}

/** Reads the picked video in the browser: shape / length checks before uploading, plus a poster frame. */
async function inspectVideo(file: File): Promise<{ url: string; duration: number; poster: Blob | null; error?: string }> {
  const url = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.preload = "auto";
  video.muted = true;
  video.playsInline = true;
  video.src = url;
  try {
    await new Promise<void>((resolve, reject) => {
      video.onloadedmetadata = () => resolve();
      video.onerror = () => reject(new Error("bad"));
    });
  } catch {
    return { url, duration: 0, poster: null, error: "Bu faylni video sifatida ochib bo'lmadi." };
  }
  const { videoWidth: w, videoHeight: h, duration } = video;
  if (!w || h < w * REEL_LIMITS.minRatio) return { url, duration, poster: null, error: "Video vertikal (9:16, Reels) formatda bo'lishi kerak." };
  if (duration < REEL_LIMITS.minSeconds || duration > REEL_LIMITS.maxSeconds)
    return { url, duration, poster: null, error: `Video ${REEL_LIMITS.minSeconds}–${REEL_LIMITS.maxSeconds} soniya bo'lishi kerak.` };
  video.currentTime = Math.min(1, duration / 2);
  await new Promise<void>((resolve) => {
    video.onseeked = () => resolve();
    setTimeout(resolve, 3000);
  });
  const canvas = document.createElement("canvas");
  const scale = Math.min(1, 1280 / h);
  canvas.width = Math.round(w * scale);
  canvas.height = Math.round(h * scale);
  canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
  const poster = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
  return { url, duration, poster };
}

function ReelUploadForm({ studioId, onDone }: { studioId: string; onDone: () => void }) {
  const upload = useUploadReel(studioId);
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<{ url: string; duration: number; poster: Blob | null } | null>(null);
  const [problem, setProblem] = useState("");
  const [caption, setCaption] = useState("");

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview.url);
  }, [preview]);

  const pick = async (f: File | undefined) => {
    if (!f) return;
    setProblem("");
    if (f.size > REEL_LIMITS.maxBytes) {
      setProblem("Video hajmi 100 MB dan oshmasligi kerak.");
      return;
    }
    const info = await inspectVideo(f);
    setPreview(info);
    if (info.error) {
      setProblem(info.error);
      setFile(null);
    } else setFile(f);
  };

  const submit = () => {
    if (!file || !preview) return;
    upload.mutate(
      { video: file, poster: preview.poster, caption: caption.trim() },
      {
        onSuccess: () => {
          toast.success("Reels joylandi");
          onDone();
        },
        onError: (e) => setProblem(errorText(e, "Video yuklanmadi")),
      },
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <input ref={input} type="file" accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.m4v,.webm" className="hidden" onChange={(e) => (pick(e.target.files?.[0]), (e.target.value = ""))} />
      <div className="flex gap-4">
        <button
          type="button"
          onClick={() => input.current?.click()}
          className="relative flex aspect-[9/16] w-36 shrink-0 items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed border-border bg-muted text-muted-foreground hover:border-cyan-500"
          aria-label="Video tanlash"
        >
          {preview && !problem ? (
            <video src={preview.url} className="size-full object-cover" autoPlay muted loop playsInline />
          ) : (
            <UploadIcon className="size-8" aria-hidden />
          )}
        </button>
        <div className="flex min-w-0 flex-col gap-2 text-sm">
          <p className="font-semibold">Talablar</p>
          <ul className="list-disc space-y-1 pl-4 text-muted-foreground">
            <li>Vertikal — 9:16 (telefon bilan tik holda)</li>
            <li>{REEL_LIMITS.minSeconds}–{REEL_LIMITS.maxSeconds} soniya</li>
            <li>MP4, MOV yoki WEBM, 100 MB gacha</li>
          </ul>
          {file && <p className="truncate font-medium">{file.name} · {clock(preview?.duration ?? 0)}</p>}
          <Button variant="outline" size="sm" onClick={() => input.current?.click()} className="w-max">
            {file ? "Boshqa video" : "Video tanlash"}
          </Button>
        </div>
      </div>
      {problem && <p className="rounded-xl bg-red-500/10 px-3 py-2 text-sm font-medium text-danger">{problem}</p>}
      <Field label="Tavsif (ixtiyoriy)" htmlFor="reel-caption">
        <Textarea id="reel-caption" maxLength={300} value={caption} onChange={(e) => setCaption(e.target.value)} placeholder="Masalan: Kelin salom, Samarqand 2026" />
      </Field>
      <Button size="lg" onClick={submit} disabled={!file} loading={upload.isPending}>
        <UploadIcon /> {upload.isPending ? "Yuklanmoqda…" : "Joylash"}
      </Button>
    </div>
  );
}

function ItemDetail({
  studioId,
  item,
  canManage,
  verified,
  onClose,
}: {
  studioId: string;
  item: PortfolioItem;
  canManage: boolean;
  verified: boolean;
  onClose: () => void;
}) {
  const remove = useDeletePortfolio(studioId);
  const updateCaption = useUpdateCaption(studioId);
  const comments = useItemComments(studioId, item.id);
  const deleteComment = useDeleteComment(studioId, item.id);
  const [editing, setEditing] = useState(false);
  const [caption, setCaption] = useState(item.caption);

  return (
    <div className="flex flex-col gap-4">
      <div className={cn("mx-auto overflow-hidden rounded-2xl bg-black", item.kind === "VIDEO" ? "aspect-[9/16] w-full max-w-[280px]" : "w-full")}>
        {item.kind === "VIDEO" && item.video ? (
          <video src={item.video} poster={item.image} className="size-full object-cover" autoPlay loop playsInline controls />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side
          <img src={item.image} alt="" className="max-h-[50dvh] w-full object-contain" />
        )}
      </div>

      {verified ? <Stats item={item} /> : <p className="text-xs text-muted-foreground">Like va izohlar galichka faol bo&apos;lganda ishlaydi.</p>}

      {editing ? (
        <div className="flex flex-col gap-2">
          <Textarea maxLength={300} value={caption} onChange={(e) => setCaption(e.target.value)} aria-label="Tavsif" />
          <div className="flex gap-2">
            <Button
              size="sm"
              loading={updateCaption.isPending}
              onClick={() =>
                updateCaption.mutate(
                  { id: item.id, caption },
                  { onSuccess: () => (setEditing(false), toast.success("Saqlandi")), onError: (e) => toast.error(errorText(e, "Saqlanmadi")) },
                )
              }
            >
              Saqlash
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Bekor qilish</Button>
          </div>
        </div>
      ) : (
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm whitespace-pre-line">{caption || <span className="text-muted-foreground">Tavsif yo&apos;q</span>}</p>
          {canManage && (
            <button type="button" onClick={() => setEditing(true)} className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted" aria-label="Tavsifni tahrirlash">
              <PencilIcon className="size-4" />
            </button>
          )}
        </div>
      )}

      {verified && (
        <section className="flex flex-col gap-2">
          <h3 className="text-sm font-bold">Izohlar</h3>
          {comments.isPending ? (
            <Skeleton className="h-16 rounded-xl" />
          ) : comments.error ? (
            <ErrorState error={comments.error} onRetry={() => comments.refetch()} />
          ) : comments.data.length === 0 ? (
            <p className="text-sm text-muted-foreground">Hali izoh yo&apos;q.</p>
          ) : (
            <ul className="flex max-h-64 flex-col gap-2 overflow-y-auto">
              {comments.data.map((c) => (
                <li key={c.id} className="flex items-start justify-between gap-2 rounded-xl bg-muted px-3 py-2 text-sm">
                  <div className="min-w-0">
                    <p className="font-semibold">{c.author_name} <span className="text-xs font-normal text-muted-foreground">{formatDateTime(c.created_at)}</span></p>
                    <p className="break-words whitespace-pre-line">{c.text}</p>
                  </div>
                  {canManage && (
                    <button
                      type="button"
                      aria-label="Izohni o'chirish"
                      onClick={() => deleteComment.mutate(c.id, { onError: (e) => toast.error(errorText(e, "O'chirilmadi")) })}
                      className="rounded-lg p-1 text-muted-foreground hover:bg-background hover:text-danger"
                    >
                      <XIcon className="size-4" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {canManage && (
        <Button
          variant="danger"
          loading={remove.isPending}
          onClick={() =>
            remove.mutate(item.id, {
              onSuccess: () => (toast.success("O'chirildi"), onClose()),
              onError: (e) => toast.error(errorText(e, "O'chirilmadi")),
            })
          }
        >
          <Trash2Icon /> {item.kind === "VIDEO" ? "Videoni" : "Rasmni"} o&apos;chirish
        </Button>
      )}
    </div>
  );
}

export default function PortfolioPage() {
  const studios = useMyStudios();
  return (
    <>
      <PageTitle title="Portfolio" subtitle="Reels va rasmlar — mijozlar ilovasida reklama sifatida ko'rinadi" />
      {studios.isPending ? (
        <Skeleton className="h-48 rounded-3xl" />
      ) : studios.error ? (
        <Card>
          <ErrorState error={studios.error} onRetry={() => studios.refetch()} />
        </Card>
      ) : studios.data.length === 0 ? (
        <Card>
          <EmptyState title="Studiya topilmadi" description="Hisobingiz hali studiyaga biriktirilmagan." />
        </Card>
      ) : (
        studios.data.map((m) => <StudioPortfolio key={m.studio.id} membership={m} />)
      )}
    </>
  );
}
