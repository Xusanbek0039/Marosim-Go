"use client";

import { CastleIcon, EyeIcon, EyeOffIcon, StarIcon, Trash2Icon, VideoIcon } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState, ErrorState, GlassCard, PageHeader, Pagination, RowsSkeleton } from "@/components/common";
import { ListToolbar } from "@/components/common/list-toolbar";
import { RequirePermission } from "@/components/layout/require-permission";
import { ConfirmDialog } from "@/components/motion/confirm-dialog";
import { PageTransition } from "@/components/motion/page-transition";
import { Button } from "@/components/ui/button";
import { useCan } from "@/features/auth/hooks";
import { reviewsResource } from "@/features/schedule/api";
import { useListState } from "@/features/use-list-state";
import { ApiError } from "@/lib/api/client";
import type { AdminReview } from "@/lib/api/types";
import { formatDate, formatPhone } from "@/lib/format";
import { cn } from "@/lib/utils";
import { listContainer, stagger } from "@/motion/tokens";

const FILTERS = [
  { key: "kind", label: "Turi", options: [{ value: "venue", label: "To'yxona" }, { value: "studio", label: "Studiya" }] },
  { key: "is_hidden", label: "Ko'rinish", options: [{ value: "false", label: "Ko'rinadi" }, { value: "true", label: "Yashirilgan" }] },
  { key: "rating", label: "Baho", options: [5, 4, 3, 2, 1].map((n) => ({ value: String(n), label: `${n} ★` })) },
];
const ORDERING = [
  { value: "-created_at", label: "Eng yangilari" },
  { value: "rating", label: "Past baho avval" },
  { value: "-rating", label: "Yuqori baho avval" },
];

function Stars({ value }: { value: number }) {
  return (
    <span className="inline-flex gap-0.5" aria-label={`${value} / 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <StarIcon key={i} className={cn("size-3.5", i <= value ? "fill-amber-400 text-amber-400" : "text-muted-foreground/40")} aria-hidden />
      ))}
    </span>
  );
}

function ReviewsContent() {
  const can = useCan();
  const list = useListState({ ordering: "-created_at", pageSize: 20 });
  const { data, error, isPending, refetch } = reviewsResource.useList(list.params);
  const update = reviewsResource.useUpdate();
  const remove = reviewsResource.useDelete();
  const [deleting, setDeleting] = useState<AdminReview | null>(null);
  const moderate = can("reviews.moderate");
  const onError = (e: Error) => toast.error(e instanceof ApiError ? e.message : "Amal bajarilmadi");

  return (
    <>
      <PageHeader title="Sharhlar" crumb="Boshqaruv / Sharhlar" />
      <GlassCard className="p-4 sm:p-5">
        <ListToolbar
          search={list.search}
          onSearch={list.setSearch}
          placeholder="Matn, to'yxona / studiya yoki muallif"
          filters={FILTERS}
          values={list.filters}
          onFilter={list.setFilter}
          ordering={{ value: list.ordering, options: ORDERING, onChange: list.setOrdering }}
        />
      </GlassCard>

      {isPending ? (
        <GlassCard>
          <RowsSkeleton />
        </GlassCard>
      ) : error ? (
        <GlassCard>
          <ErrorState error={error} onRetry={() => refetch()} />
        </GlassCard>
      ) : data.results.length === 0 ? (
        <GlassCard>
          <EmptyState title={list.hasQuery ? "Hech narsa topilmadi" : "Hali sharhlar yo'q"} description="Mijozlar to'yxona va studiyalarga baho berganda shu yerda ko'rinadi." />
        </GlassCard>
      ) : (
        <motion.ul key={JSON.stringify(list.params)} variants={listContainer(stagger.cards)} initial="initial" animate="animate" className="flex flex-col gap-3">
          {data.results.map((r) => {
            const Icon = r.target.kind === "venue" ? CastleIcon : VideoIcon;
            return (
              <GlassCard key={r.id} className={cn("flex flex-col gap-2 p-4 sm:p-5", r.is_hidden && "opacity-60")}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="flex min-w-0 items-center gap-2 font-bold">
                    <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                    <span className="truncate">{r.target.name}</span>
                    <Stars value={r.rating} />
                    {r.is_hidden && <span className="rounded-full bg-red-500/14 px-2 text-[11px] font-bold text-red-700 dark:text-red-300">Yashirilgan</span>}
                  </span>
                  <span className="text-xs text-muted-foreground tabular-nums">{formatDate(r.created_at)}</span>
                </div>
                {r.text ? <p className="text-sm whitespace-pre-line">{r.text}</p> : <p className="text-sm text-muted-foreground italic">Izohsiz baho</p>}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground">
                    {r.author.full_name || "—"}
                    {r.author.phone_number && <span className="tabular-nums"> · {formatPhone(r.author.phone_number)}</span>}
                  </span>
                  {moderate && (
                    <div className="flex gap-1.5">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={update.isPending}
                        onClick={() =>
                          update.mutate(
                            { id: r.id, values: { is_hidden: !r.is_hidden } },
                            { onSuccess: (v) => toast.success(v.is_hidden ? "Sharh yashirildi" : "Sharh yana ko'rinadi"), onError },
                          )
                        }
                      >
                        {r.is_hidden ? <EyeIcon /> : <EyeOffIcon />} {r.is_hidden ? "Ko'rsatish" : "Yashirish"}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setDeleting(r)} aria-label="O'chirish">
                        <Trash2Icon />
                      </Button>
                    </div>
                  )}
                </div>
              </GlassCard>
            );
          })}
        </motion.ul>
      )}

      {data && data.count > 0 && (
        <Pagination page={data.page} totalPages={data.total_pages} count={data.count} pageSize={data.page_size} onPage={list.setPage} />
      )}

      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(o) => !o && setDeleting(null)}
        pending={remove.isPending}
        tone="danger"
        title="Sharhni o'chirasizmi?"
        confirmLabel="O'chirish"
        description="Sharh butunlay o'chiriladi va reytingdan chiqadi. Faqat yashirish uchun 'Yashirish' tugmasidan foydalaning."
        onConfirm={() =>
          deleting && remove.mutate(deleting.id, { onSuccess: () => (toast.success("Sharh o'chirildi"), setDeleting(null)), onError })
        }
      />
    </>
  );
}

export default function ReviewsPage() {
  return (
    <RequirePermission requires="reviews.view">
      <PageTransition>
        <ReviewsContent />
      </PageTransition>
    </RequirePermission>
  );
}
