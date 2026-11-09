"use client";

import { CheckIcon, FileImageIcon, FileVideoIcon, Trash2Icon, XIcon } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState, ErrorState, GlassCard, PageHeader, Pagination, RowsSkeleton } from "@/components/common";
import { ListToolbar } from "@/components/common/list-toolbar";
import { RequirePermission } from "@/components/layout/require-permission";
import { MotionDialog } from "@/components/motion/motion-dialog";
import { PageTransition } from "@/components/motion/page-transition";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCan } from "@/features/auth/hooks";
import { type DeletionRequest, type DeletionStatus, deletionRequestsResource, STATUS, useDeletionDecision } from "@/features/requests/api";
import { useListState } from "@/features/use-list-state";
import { ApiError } from "@/lib/api/client";
import { formatDate, formatDateTime, formatPhone } from "@/lib/format";
import { cn } from "@/lib/utils";

const FILTERS = [
  {
    key: "status",
    label: "Holat",
    options: (Object.keys(STATUS) as DeletionStatus[]).map((k) => ({ value: k, label: STATUS[k].label })),
  },
];
const ORDERING = [
  { value: "-created_at", label: "Eng yangilari" },
  { value: "created_at", label: "Eng eskilari" },
  { value: "-decided_at", label: "Yaqinda ko'rib chiqilgan" },
];

const errorText = (e: unknown, fallback: string) =>
  e instanceof ApiError ? (Object.values(e.fieldErrors)[0] as string | undefined) ?? e.message : fallback;

function formatBytes(n: number) {
  if (n >= 1024 ** 3) return `${(n / 1024 ** 3).toFixed(1)} GB`;
  if (n >= 1024 ** 2) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(n / 1024))} KB`;
}

function StatusBadge({ status }: { status: DeletionStatus }) {
  return <span className={cn("inline-flex h-6 items-center rounded-full px-2.5 text-xs font-bold", STATUS[status].className)}>{STATUS[status].label}</span>;
}

type Dialog = { kind: "approve" | "reject"; row: DeletionRequest } | null;

function DecisionDialog({ dialog, onClose }: { dialog: Dialog; onClose: () => void }) {
  const decide = useDeletionDecision();
  const [note, setNote] = useState("");
  const row = dialog?.row;
  const approve = dialog?.kind === "approve";
  const close = () => {
    setNote("");
    onClose();
  };
  const submit = () => {
    if (!dialog) return;
    decide.mutate(
      { id: dialog.row.id, action: dialog.kind, note },
      {
        onSuccess: () => {
          toast.success(approve ? "Fayl o'chirildi (Google Drive savatiga o'tdi)" : "So'rov rad etildi, fayl qoldi");
          close();
        },
        onError: (e) => toast.error(errorText(e, "Bajarilmadi")),
      },
    );
  };
  return (
    <MotionDialog
      open={Boolean(dialog)}
      onOpenChange={(o) => !o && close()}
      title={approve ? "Faylni o'chirishni tasdiqlash" : "So'rovni rad etish"}
      description={row ? `${row.studio.name} · ${row.ceremony.title}` : undefined}
      footer={
        <>
          <Button variant="outline" className="h-11 flex-1" onClick={close}>
            Yopish
          </Button>
          <Button className={cn("h-11 flex-1", approve && "bg-red-600 text-white hover:bg-red-700")} onClick={submit} disabled={decide.isPending}>
            {approve ? <Trash2Icon /> : <XIcon />} {approve ? "O'chirish" : "Rad etish"}
          </Button>
        </>
      }
    >
      {row && (
        <div className="flex flex-col gap-4">
          <div className="rounded-2xl bg-muted/60 p-3 text-sm">
            <p className="font-semibold">{row.media.original_name}</p>
            <p className="text-xs text-muted-foreground">
              {formatBytes(row.media.size_bytes)} · yuklangan: {formatDateTime(row.media.completed_at)}
            </p>
            <p className="mt-2">
              <span className="font-semibold">Sabab:</span> {row.reason}
            </p>
          </div>
          {approve && (
            <p className="text-xs text-muted-foreground">
              Fayl va uning logoli nusxasi Google Drive savatiga o&apos;tadi va mijoz galereyasidan darhol yo&apos;qoladi. Drive savatidan uni taxminan 30
              kun ichida qaytarish mumkin.
            </p>
          )}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="d-note">Izoh (ixtiyoriy)</Label>
            <Textarea id="d-note" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
        </div>
      )}
    </MotionDialog>
  );
}

function RequestsContent() {
  const can = useCan();
  const list = useListState({ ordering: "-created_at" });
  const { data, error, isPending, refetch } = deletionRequestsResource.useList(list.params);
  const [dialog, setDialog] = useState<Dialog>(null);
  const canDecide = can("requests.media_delete");

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="So'rovlar" crumb="Studiyalarning media o'chirish so'rovlari" />
      <ListToolbar
        search={list.search}
        onSearch={list.setSearch}
        placeholder="Fayl nomi, marosim, studiya yoki sabab"
        filters={FILTERS}
        values={list.filters}
        onFilter={list.setFilter}
        ordering={{ value: list.ordering, options: ORDERING, onChange: list.setOrdering }}
      />
      <GlassCard className="p-0 sm:p-0">
        {isPending ? (
          <div className="p-5">
            <RowsSkeleton />
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.results.length === 0 ? (
          <EmptyState
            title={list.hasQuery ? "Hech narsa topilmadi" : "So'rov yo'q"}
            description="Studiya tayyor faylni o'chirmoqchi bo'lsa, so'rov shu yerga tushadi."
          />
        ) : (
          <ul className="divide-y divide-border/70">
            {data.results.map((r) => {
              const Icon = r.media.kind === "VIDEO" ? FileVideoIcon : FileImageIcon;
              return (
                <motion.li key={r.id} layout className="flex flex-wrap items-center gap-x-5 gap-y-2 px-5 py-4">
                  <Icon className="size-5 shrink-0 text-muted-foreground" aria-hidden />
                  <div className="min-w-48 flex-1">
                    <p className="truncate font-semibold">{r.media.original_name}</p>
                    <p className="text-xs text-muted-foreground tabular-nums">
                      {formatBytes(r.media.size_bytes)} · {r.media.uploaded_by_name ?? "—"}
                    </p>
                  </div>
                  <div className="w-52 min-w-0">
                    <p className="truncate font-semibold">{r.studio.name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {r.ceremony.title} · {formatDate(r.ceremony.event_date)}
                    </p>
                  </div>
                  <div className="w-44 min-w-0 text-sm">
                    <p className="truncate font-semibold">{r.requested_by?.name ?? "—"}</p>
                    <p className="text-xs text-muted-foreground tabular-nums">{formatPhone(r.requested_by?.phone_number)}</p>
                  </div>
                  <div className="w-40 text-sm">
                    <StatusBadge status={r.status} />
                    <p className="mt-1 text-xs text-muted-foreground">{formatDateTime(r.created_at)}</p>
                  </div>
                  <div className="ml-auto flex gap-2">
                    {canDecide && r.status === "PENDING" && (
                      <>
                        <Button size="sm" variant="ghost" onClick={() => setDialog({ kind: "reject", row: r })}>
                          <XIcon /> Rad etish
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => setDialog({ kind: "approve", row: r })}>
                          <CheckIcon /> O&apos;chirishni tasdiqlash
                        </Button>
                      </>
                    )}
                  </div>
                  <p className="w-full text-xs text-muted-foreground">
                    <span className="font-semibold text-foreground/80">Sabab:</span> {r.reason}
                    {r.decided_by_name && ` · ${r.decided_by_name}, ${formatDateTime(r.decided_at)}`}
                    {r.decision_note && ` · Izoh: ${r.decision_note}`}
                  </p>
                </motion.li>
              );
            })}
          </ul>
        )}
      </GlassCard>
      {data && data.total_pages > 1 && (
        <Pagination page={data.page} totalPages={data.total_pages} count={data.count} pageSize={data.page_size} onPage={list.setPage} />
      )}
      <DecisionDialog dialog={dialog} onClose={() => setDialog(null)} />
    </div>
  );
}

export default function RequestsPage() {
  return (
    <RequirePermission requires="requests.view">
      <PageTransition>
        <RequestsContent />
      </PageTransition>
    </RequirePermission>
  );
}
