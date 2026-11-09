"use client";

import { CheckCircle2Icon, CloudUploadIcon, FileImageIcon, FileVideoIcon, Loader2Icon, Trash2Icon, Undo2Icon, XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  ACCEPTED_TYPES,
  mimeOf,
  uploadFile,
  UploadAborted,
  useCancelUpload,
  useCeremonyMedia,
  useDismissUpload,
  useRefreshMedia,
  useRequestDeletion,
  useWithdrawDeletion,
  type MediaStatus,
  type StudioMedia,
} from "@/lib/media";
import type { Ceremony } from "@/lib/types";

import { Badge, Button, Card, cn, EmptyState, ErrorState, Field, Modal, Skeleton, Textarea } from "./ui";

const PARALLEL = 2;
// crypto.randomUUID needs a secure context (HTTPS/localhost) and breaks over plain-HTTP LAN IPs.
let jobSeq = 0;

const STATUS: Record<MediaStatus, { label: string; tone: "neutral" | "brand" | "success" | "warning" | "danger" }> = {
  UPLOADING: { label: "Yuklanmoqda", tone: "brand" },
  READY: { label: "Tayyor", tone: "success" },
  FAILED: { label: "Xato", tone: "danger" },
  CANCELLED: { label: "Bekor qilingan", tone: "neutral" },
  EXPIRED: { label: "Muddati o'tgan", tone: "warning" },
  DELETED: { label: "O'chirilgan", tone: "neutral" },
};

export function formatBytes(n: number) {
  if (n >= 1024 ** 3) return `${(n / 1024 ** 3).toFixed(1)} GB`;
  if (n >= 1024 ** 2) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(n / 1024))} KB`;
}

interface Job {
  id: string; // local id
  file: File;
  mime: string;
  sent: number;
  mediaId?: string;
  state: "queued" | "uploading" | "verifying" | "done" | "error" | "cancelled";
  error?: string;
  abort: AbortController;
}

function useUploadQueue(ceremonyId: string) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const running = useRef(0);
  const queue = useRef<Job[]>([]);
  const refresh = useRefreshMedia(ceremonyId);
  const cancelOnServer = useCancelUpload(ceremonyId);

  const patch = useCallback((id: string, next: Partial<Job>) => setJobs((all) => all.map((j) => (j.id === id ? { ...j, ...next } : j))), []);

  const runJob = async (job: Job) => {
    patch(job.id, { state: "uploading" });
    try {
      await uploadFile(
        ceremonyId,
        job.file,
        job.mime,
        (sent, mediaId) => patch(job.id, { sent, mediaId, ...(sent >= job.file.size ? { state: "verifying" as const } : {}) }),
        job.abort.signal,
      );
      patch(job.id, { state: "done", sent: job.file.size });
    } catch (err) {
      if (err instanceof UploadAborted) patch(job.id, { state: "cancelled" });
      else patch(job.id, { state: "error", error: err instanceof ApiError ? err.message : "Yuklashda xato. Internetni tekshirib, qayta urinib ko'ring." });
    } finally {
      refresh();
    }
  };

  /** Up to PARALLEL workers drain the shared queue; each exits when the queue is empty. */
  const worker = async () => {
    running.current += 1;
    try {
      for (let job = queue.current.shift(); job; job = queue.current.shift()) {
        if (!job.abort.signal.aborted) await runJob(job);
      }
    } finally {
      running.current -= 1;
    }
  };
  const pump = () => {
    while (running.current < PARALLEL && queue.current.length) void worker();
  };

  const add = (files: FileList | File[]) => {
    const fresh: Job[] = [];
    for (const file of Array.from(files)) {
      const mime = mimeOf(file);
      if (!mime) {
        toast.error(`${file.name}: bu fayl turi qo'llab-quvvatlanmaydi`);
        continue;
      }
      fresh.push({ id: `job-${++jobSeq}`, file, mime, sent: 0, state: "queued", abort: new AbortController() });
    }
    if (!fresh.length) return;
    queue.current.push(...fresh);
    setJobs((all) => [...fresh, ...all]);
    pump();
  };

  const cancel = (job: Job) => {
    job.abort.abort();
    patch(job.id, { state: "cancelled" });
    if (job.mediaId) cancelOnServer.mutate(job.mediaId);
  };

  const clearFinished = () => setJobs((all) => all.filter((j) => j.state === "queued" || j.state === "uploading" || j.state === "verifying"));

  return { jobs, add, cancel, clearFinished };
}

function JobRow({ job, onCancel }: { job: Job; onCancel: () => void }) {
  const pct = Math.min(100, Math.round((job.sent / job.file.size) * 100));
  const active = job.state === "queued" || job.state === "uploading" || job.state === "verifying";
  const Icon = ACCEPTED_TYPES[job.mime] === "VIDEO" ? FileVideoIcon : FileImageIcon;
  return (
    <motion.li layout initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex items-center gap-3 py-2.5">
      <Icon className="size-5 shrink-0 text-muted-foreground" aria-hidden />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2 text-sm">
          <span className="truncate font-semibold">{job.file.name}</span>
          <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
            {job.state === "verifying" ? "Tekshirilmoqda…" : job.state === "done" ? formatBytes(job.file.size) : `${pct}% · ${formatBytes(job.file.size)}`}
          </span>
        </div>
        <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={job.file.name}>
          <motion.div
            className={cn("h-full rounded-full", job.state === "error" ? "bg-danger" : job.state === "cancelled" ? "bg-slate-400" : "brand-gradient")}
            animate={{ width: `${job.state === "done" ? 100 : pct}%` }}
            transition={{ ease: "easeOut", duration: 0.3 }}
          />
        </div>
        {job.error && <p className="mt-1 text-xs text-danger">{job.error}</p>}
      </div>
      {job.state === "done" ? (
        <CheckCircle2Icon className="size-5 text-success" aria-label="Yuklandi" />
      ) : job.state === "verifying" ? (
        <Loader2Icon className="size-5 animate-spin text-muted-foreground" aria-label="Tekshirilmoqda" />
      ) : active ? (
        <Button size="sm" variant="ghost" aria-label="Bekor qilish" onClick={onCancel}>
          <XIcon />
        </Button>
      ) : (
        <Badge tone={job.state === "error" ? "danger" : "neutral"}>{job.state === "error" ? "Xato" : "Bekor"}</Badge>
      )}
    </motion.li>
  );
}

const errorText = (err: unknown) => (err instanceof ApiError ? err.message : "Amalni bajarib bo'lmadi. Qayta urinib ko'ring.");

function DeleteRequestModal({ ceremonyId, media, onClose }: { ceremonyId: string; media: StudioMedia | null; onClose: () => void }) {
  const [reason, setReason] = useState("");
  const request = useRequestDeletion(ceremonyId);
  const close = () => {
    setReason("");
    onClose();
  };
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!media || !reason.trim()) return;
    request.mutate(
      { mediaId: media.id, reason: reason.trim() },
      {
        onSuccess: () => {
          toast.success("So'rov administratorga yuborildi. Tasdiqlangach fayl o'chiriladi.");
          close();
        },
        onError: (err) => toast.error(errorText(err)),
      },
    );
  };
  return (
    <Modal open={Boolean(media)} onClose={close} title="Faylni o'chirishni so'rash">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">
          <span className="font-semibold text-foreground">{media?.original_name}</span> mijozga allaqachon ko&apos;rinmoqda. Uni o&apos;chirish
          uchun administrator tasdig&apos;i kerak. Tasdiqlangach fayl Google Drive savatiga o&apos;tadi.
        </p>
        <Field label="Sabab" htmlFor="delete-reason" hint="Administrator shu sababni ko'radi.">
          <Textarea
            id="delete-reason"
            value={reason}
            maxLength={500}
            required
            autoFocus
            placeholder="Masalan: boshqa marosimning videosi yuklanib qolgan"
            onChange={(e) => setReason(e.target.value)}
          />
        </Field>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={close}>
            Bekor qilish
          </Button>
          <Button type="submit" variant="danger" loading={request.isPending} disabled={!reason.trim()}>
            So&apos;rov yuborish
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function MediaRow({ ceremonyId, media, onAskDelete }: { ceremonyId: string; media: StudioMedia; onAskDelete: () => void }) {
  const dismiss = useDismissUpload(ceremonyId);
  const withdraw = useWithdrawDeletion(ceremonyId);
  const pending = media.deletion_request;
  const remove = () => {
    if (!window.confirm(`"${media.original_name}" ro'yxatdan o'chirilsinmi? Yuklash tugallanmagan, fayl mijozga ko'rinmaydi.`)) return;
    dismiss.mutate(media.id, { onSuccess: () => toast.success("O'chirildi"), onError: (err) => toast.error(errorText(err)) });
  };
  const undo = () =>
    withdraw.mutate(media.id, { onSuccess: () => toast.success("So'rov qaytarib olindi"), onError: (err) => toast.error(errorText(err)) });
  return (
    <li className="flex items-center gap-3 border-t border-border/70 py-2.5 text-sm first:border-t-0">
      {media.kind === "VIDEO" ? <FileVideoIcon className="size-5 text-muted-foreground" aria-hidden /> : <FileImageIcon className="size-5 text-muted-foreground" aria-hidden />}
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold">{media.original_name}</p>
        <p className="text-xs text-muted-foreground tabular-nums">
          {formatBytes(media.size_bytes)} · {formatDateTime(media.completed_at ?? media.created_at)}
          {media.uploaded_by_name ? ` · ${media.uploaded_by_name}` : ""}
        </p>
        {pending && <p className="mt-0.5 truncate text-xs text-amber-700 dark:text-amber-300">O&apos;chirish sababi: {pending.reason}</p>}
      </div>
      {pending ? <Badge tone="warning">O&apos;chirish so&apos;ralgan</Badge> : <Badge tone={STATUS[media.status].tone}>{STATUS[media.status].label}</Badge>}
      {media.status !== "READY" ? (
        <Button size="sm" variant="ghost" aria-label="O'chirish" title="O'chirish" loading={dismiss.isPending} onClick={remove}>
          {!dismiss.isPending && <Trash2Icon />}
        </Button>
      ) : pending ? (
        <Button size="sm" variant="ghost" aria-label="So'rovni qaytarib olish" title="So'rovni qaytarib olish" loading={withdraw.isPending} onClick={undo}>
          {!withdraw.isPending && <Undo2Icon />}
        </Button>
      ) : (
        <Button size="sm" variant="ghost" aria-label="O'chirishni so'rash" title="O'chirishni so'rash" onClick={onAskDelete}>
          <Trash2Icon />
        </Button>
      )}
    </li>
  );
}

export function MediaCard({ ceremony }: { ceremony: Ceremony }) {
  const { data, error, isPending, refetch } = useCeremonyMedia(ceremony.id);
  const { jobs, add, cancel, clearFinished } = useUploadQueue(ceremony.id);
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [toDelete, setToDelete] = useState<StudioMedia | null>(null);
  const archived = ceremony.status === "ARCHIVED";
  const rows = data?.results ?? [];
  const ready = rows.filter((m) => m.status === "READY");
  const totals = { photos: ready.filter((m) => m.kind === "PHOTO").length, videos: ready.filter((m) => m.kind === "VIDEO").length };
  const finished = jobs.some((j) => j.state === "done" || j.state === "error" || j.state === "cancelled");

  // Arriving from the list's "Video yuklash" button (#media): bring the upload area into view.
  useEffect(() => {
    if (window.location.hash === "#media") document.getElementById("media")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  return (
    <Card id="media" className="flex scroll-mt-24 flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold">Video va rasmlar</h2>
          <p className="text-sm text-muted-foreground">
            {totals.videos} video · {totals.photos} rasm. Fayllar to&apos;g&apos;ridan-to&apos;g&apos;ri Google Drive&apos;ga, mijoz papkasiga yuklanadi.
          </p>
        </div>
      </div>

      {archived ? (
        <p className="rounded-2xl bg-muted/60 p-4 text-sm text-muted-foreground">Arxivlangan marosimga fayl yuklab bo&apos;lmaydi.</p>
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            add(e.dataTransfer.files);
          }}
          className={cn(
            "flex flex-col items-center gap-3 rounded-3xl border-2 border-dashed px-6 py-8 text-center transition",
            dragging ? "border-accent bg-cyan-500/10" : "border-glass-border bg-muted/30",
          )}
        >
          <motion.span
            animate={dragging ? { y: -4, scale: 1.08 } : { y: 0, scale: 1 }}
            className="flex size-14 items-center justify-center rounded-3xl brand-gradient text-white shadow-[0_12px_30px_-14px_rgb(37_99_235/0.9)]"
          >
            <CloudUploadIcon className="size-7" aria-hidden />
          </motion.span>
          <div>
            <p className="font-bold">Montaj qilingan video va rasmlarni shu yerga tashlang</p>
            <p className="text-xs text-muted-foreground">MP4, MOV, MKV, WEBM — 20 GB gacha · JPG, PNG, WEBP, HEIC — 50 MB gacha</p>
          </div>
          <input
            ref={input}
            type="file"
            multiple
            accept={[...Object.keys(ACCEPTED_TYPES), ".heic", ".heif", ".mkv", ".mov", ".m4v"].join(",")}
            className="hidden"
            onChange={(e) => {
              if (e.target.files) add(e.target.files);
              e.target.value = "";
            }}
          />
          <Button onClick={() => input.current?.click()}>Fayl tanlash</Button>
        </div>
      )}

      {jobs.length > 0 && (
        <div className="rounded-2xl border border-glass-border bg-muted/30 px-4">
          <ul className="divide-y divide-border/70">
            <AnimatePresence initial={false}>
              {jobs.map((job) => (
                <JobRow key={job.id} job={job} onCancel={() => cancel(job)} />
              ))}
            </AnimatePresence>
          </ul>
          {finished && (
            <button type="button" onClick={clearFinished} className="w-full py-2 text-xs font-semibold text-muted-foreground hover:text-foreground">
              Tugaganlarini tozalash
            </button>
          )}
        </div>
      )}

      {isPending ? (
        <Skeleton className="h-20" />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState title="Hali fayl yuklanmagan" description="Yuklangan fayllar mijozning shaxsiy galereyasida ko'rinadi." />
      ) : (
        <ul className="flex flex-col">
          {rows.map((m) => (
            <MediaRow key={m.id} ceremonyId={ceremony.id} media={m} onAskDelete={() => setToDelete(m)} />
          ))}
        </ul>
      )}
      <DeleteRequestModal ceremonyId={ceremony.id} media={toDelete} onClose={() => setToDelete(null)} />
    </Card>
  );
}
