"use client";

import { CheckCircle2Icon, CloudUploadIcon, FileImageIcon, FileVideoIcon, Loader2Icon, XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { ACCEPTED_TYPES, mimeOf, uploadFile, UploadAborted, useCancelUpload, useCeremonyMedia, useRefreshMedia, type MediaStatus } from "@/lib/media";
import type { Ceremony } from "@/lib/types";

import { Badge, Button, Card, cn, EmptyState, ErrorState, Skeleton } from "./ui";

const PARALLEL = 2;

const STATUS: Record<MediaStatus, { label: string; tone: "neutral" | "brand" | "success" | "warning" | "danger" }> = {
  UPLOADING: { label: "Yuklanmoqda", tone: "brand" },
  READY: { label: "Tayyor", tone: "success" },
  FAILED: { label: "Xato", tone: "danger" },
  CANCELLED: { label: "Bekor qilingan", tone: "neutral" },
  EXPIRED: { label: "Muddati o'tgan", tone: "warning" },
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

  const pump = useCallback(() => {
    while (running.current < PARALLEL && queue.current.length) {
      const job = queue.current.shift()!;
      if (job.abort.signal.aborted) continue;
      running.current += 1;
      patch(job.id, { state: "uploading" });
      uploadFile(
        ceremonyId,
        job.file,
        job.mime,
        (sent, mediaId) => patch(job.id, { sent, mediaId, ...(sent >= job.file.size ? { state: "verifying" as const } : {}) }),
        job.abort.signal,
      )
        .then(() => patch(job.id, { state: "done", sent: job.file.size }))
        .catch((err) => {
          if (err instanceof UploadAborted) return patch(job.id, { state: "cancelled" });
          const message = err instanceof ApiError ? err.message : "Yuklashda xato. Internetni tekshirib, qayta urinib ko'ring.";
          patch(job.id, { state: "error", error: message });
        })
        .finally(() => {
          running.current -= 1;
          refresh();
          pump();
        });
    }
  }, [ceremonyId, patch, refresh]);

  const add = (files: FileList | File[]) => {
    const fresh: Job[] = [];
    for (const file of Array.from(files)) {
      const mime = mimeOf(file);
      if (!mime) {
        toast.error(`${file.name}: bu fayl turi qo'llab-quvvatlanmaydi`);
        continue;
      }
      fresh.push({ id: crypto.randomUUID(), file, mime, sent: 0, state: "queued", abort: new AbortController() });
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

export function MediaCard({ ceremony }: { ceremony: Ceremony }) {
  const { data, error, isPending, refetch } = useCeremonyMedia(ceremony.id);
  const { jobs, add, cancel, clearFinished } = useUploadQueue(ceremony.id);
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const archived = ceremony.status === "ARCHIVED";
  const rows = data?.results ?? [];
  const ready = rows.filter((m) => m.status === "READY");
  const totals = { photos: ready.filter((m) => m.kind === "PHOTO").length, videos: ready.filter((m) => m.kind === "VIDEO").length };
  const finished = jobs.some((j) => j.state === "done" || j.state === "error" || j.state === "cancelled");

  return (
    <Card className="flex flex-col gap-4">
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
            <li key={m.id} className="flex items-center gap-3 border-t border-border/70 py-2.5 text-sm first:border-t-0">
              {m.kind === "VIDEO" ? <FileVideoIcon className="size-5 text-muted-foreground" aria-hidden /> : <FileImageIcon className="size-5 text-muted-foreground" aria-hidden />}
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold">{m.original_name}</p>
                <p className="text-xs text-muted-foreground tabular-nums">
                  {formatBytes(m.size_bytes)} · {formatDateTime(m.completed_at ?? m.created_at)}
                  {m.uploaded_by_name ? ` · ${m.uploaded_by_name}` : ""}
                </p>
              </div>
              <Badge tone={STATUS[m.status].tone}>{STATUS[m.status].label}</Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
