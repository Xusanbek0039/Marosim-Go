"use client";

import { HeartIcon, MessageSquareIcon, StarIcon, Trash2Icon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { type ReviewKind, type Stats, useDeleteReview, useReviews, useSaveReview, useToggleLike } from "@/lib/reviews";

import { Button, Card, cn, ErrorState, Skeleton, Textarea } from "./ui";

/** Read-only star row; half stars are rounded to the nearest whole star. */
export function Stars({ value, className }: { value: number | null; className?: string }) {
  const filled = Math.round(value ?? 0);
  return (
    <span className={cn("inline-flex items-center gap-0.5", className)} aria-label={value ? `${value} / 5` : "Baho yo'q"}>
      {[1, 2, 3, 4, 5].map((i) => (
        <StarIcon key={i} className={cn("size-3.5", i <= filled ? "fill-amber-400 text-amber-400" : "text-muted-foreground/40")} aria-hidden />
      ))}
    </span>
  );
}

/** Compact "★ 4.6 (12) · ♥ 30" line for cards. */
export function StatsLine({ stats, className, light }: { stats?: Stats; className?: string; light?: boolean }) {
  if (!stats) return null;
  return (
    <span className={cn("inline-flex items-center gap-2.5 text-xs font-semibold", light ? "text-white" : "text-foreground/85", className)}>
      <span className="inline-flex items-center gap-1">
        <StarIcon className="size-3.5 fill-amber-400 text-amber-400" aria-hidden />
        {stats.rating_avg ? stats.rating_avg.toFixed(1) : "—"}
        <span className={light ? "text-white/75" : "text-muted-foreground"}>({stats.rating_count})</span>
      </span>
      <span className="inline-flex items-center gap-1">
        <HeartIcon className="size-3.5 fill-rose-500 text-rose-500" aria-hidden />
        {stats.like_count}
      </span>
    </span>
  );
}

function StarPicker({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [hover, setHover] = useState(0);
  const shown = hover || value;
  return (
    <div className="flex items-center gap-1" role="radiogroup" aria-label="Baho" onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map((i) => (
        <button
          key={i}
          type="button"
          role="radio"
          aria-checked={value === i}
          aria-label={`${i} yulduz`}
          onMouseEnter={() => setHover(i)}
          onClick={() => onChange(i)}
          className="rounded-md p-0.5 transition hover:scale-110"
        >
          <StarIcon className={cn("size-7", i <= shown ? "fill-amber-400 text-amber-400" : "text-muted-foreground/40")} />
        </button>
      ))}
    </div>
  );
}

const errorText = (e: unknown) => (e instanceof ApiError ? (e.fieldErrors.rating ?? e.fieldErrors.text ?? e.message) : "Saqlanmadi");

/** Rating summary, like button, "my review" form and the public review list of one business. */
export function ReviewsSection({ kind, id, name }: { kind: ReviewKind; id: string; name: string }) {
  const { data, error, isPending, refetch } = useReviews(kind, id);
  const save = useSaveReview(kind, id);
  const remove = useDeleteReview(kind, id);
  const like = useToggleLike(kind, id);
  const [draft, setDraft] = useState<{ rating: number; text: string } | null>(null);

  if (isPending) return <Skeleton className="h-48 rounded-3xl" />;
  if (error)
    return (
      <Card>
        <ErrorState error={error} onRetry={() => refetch()} />
      </Card>
    );

  const { summary, results } = data;
  const mine = summary.my_review;
  const form = draft ?? { rating: mine?.rating ?? 0, text: mine?.text ?? "" };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.rating) return toast.error("Yulduzcha bilan baho bering");
    save.mutate(form, {
      onSuccess: () => (setDraft(null), toast.success(mine ? "Sharhingiz yangilandi" : "Rahmat! Sharhingiz qo'shildi")),
      onError: (err) => toast.error(errorText(err)),
    });
  };

  return (
    <Card className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-center rounded-2xl bg-amber-500/10 px-4 py-2">
            <span className="text-3xl font-extrabold tabular-nums">{summary.rating_avg ? summary.rating_avg.toFixed(1) : "—"}</span>
            <Stars value={summary.rating_avg} />
          </div>
          <div>
            <h2 className="text-lg font-bold">Baholar va izohlar</h2>
            <p className="text-sm text-muted-foreground">
              {summary.rating_count} ta baho · {summary.like_count} ta yoqtirish
            </p>
          </div>
        </div>
        <Button
          variant={summary.liked ? "danger" : "outline"}
          onClick={() => like.mutate(!summary.liked, { onError: (err) => toast.error(errorText(err)) })}
          loading={like.isPending}
          aria-pressed={summary.liked}
        >
          <HeartIcon className={cn(summary.liked && "fill-current")} />
          {summary.liked ? "Yoqdi" : "Yoqtirish"}
        </Button>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-3 rounded-2xl border border-border p-4">
        <p className="text-sm font-semibold">{mine ? "Sizning bahoyingiz" : `${name} haqida fikringiz`}</p>
        <StarPicker value={form.rating} onChange={(rating) => setDraft({ ...form, rating })} />
        <Textarea
          value={form.text}
          maxLength={1000}
          rows={3}
          placeholder="Xizmat, sifat, narx haqida yozing (ixtiyoriy)"
          onChange={(e) => setDraft({ ...form, text: e.target.value })}
          aria-label="Izoh"
        />
        <div className="flex flex-wrap justify-end gap-2">
          {mine && (
            <Button
              type="button"
              variant="ghost"
              loading={remove.isPending}
              onClick={() =>
                remove.mutate(undefined, {
                  onSuccess: () => (setDraft(null), toast.success("Sharh o'chirildi")),
                  onError: (err) => toast.error(errorText(err)),
                })
              }
            >
              <Trash2Icon /> O&apos;chirish
            </Button>
          )}
          <Button type="submit" loading={save.isPending} disabled={!draft && Boolean(mine)}>
            {mine ? "Yangilash" : "Yuborish"}
          </Button>
        </div>
      </form>

      {results.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <MessageSquareIcon className="size-4" aria-hidden /> Hali izoh yo&apos;q — birinchi bo&apos;ling!
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          <AnimatePresence initial={false}>
            {results.map((r) => (
              <motion.li key={r.id} layout initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="rounded-2xl bg-muted/50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-semibold">{r.author_name}</p>
                  <span className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Stars value={r.rating} /> {formatDateTime(r.created_at)}
                  </span>
                </div>
                {r.text && <p className="mt-1.5 text-sm whitespace-pre-line text-foreground/85">{r.text}</p>}
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </Card>
  );
}
