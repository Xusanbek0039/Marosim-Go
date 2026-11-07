"use client";

import { MapPinIcon, MoreHorizontalIcon, PencilIcon, PlusIcon, PowerIcon, Trash2Icon, VideoIcon } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { toast } from "sonner";

import { CardsSkeleton, EmptyState, ErrorState, GlassCard, PageHeader, Pagination, StatusBadge, UserAvatar } from "@/components/common";
import { ListToolbar } from "@/components/common/list-toolbar";
import { RequirePermission } from "@/components/layout/require-permission";
import { ConfirmDialog } from "@/components/motion/confirm-dialog";
import { MotionDrawer } from "@/components/motion/motion-dialog";
import { PageTransition } from "@/components/motion/page-transition";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useCan } from "@/features/auth/hooks";
import { studiosResource } from "@/features/resources";
import { StudioFormDialog } from "@/features/studios/studio-form-dialog";
import { STATUS_FILTER, useListState } from "@/features/use-list-state";
import { ApiError } from "@/lib/api/client";
import type { Studio } from "@/lib/api/types";
import { avatarGradient, formatDate, formatPhone } from "@/lib/format";
import { cn } from "@/lib/utils";
import { listContainer, stagger } from "@/motion/tokens";

const ORDERING = [
  { value: "-created_at", label: "Eng yangilari" },
  { value: "name", label: "Nomi (A–Z)" },
  { value: "-updated_at", label: "Oxirgi o'zgarish" },
];

function Cover({ studio, className }: { studio: Studio; className?: string }) {
  return (
    <div className={cn("relative overflow-hidden bg-gradient-to-br", avatarGradient(studio.id), className)}>
      {studio.profile_picture ? (
        // eslint-disable-next-line @next/next/no-img-element -- backend media, already re-encoded server-side
        <img src={studio.profile_picture} alt="" className="size-full object-cover" />
      ) : (
        <div className="flex size-full items-center justify-center text-white/85">
          <VideoIcon className="size-9" aria-hidden />
        </div>
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/40 to-transparent" aria-hidden />
    </div>
  );
}

type Confirm = { type: "delete" | "toggle"; studio: Studio } | null;

function StudiosContent() {
  const can = useCan();
  const list = useListState({ ordering: "-created_at", pageSize: 12 });
  const { data, error, isPending, refetch } = studiosResource.useList(list.params);
  const update = studiosResource.useUpdate();
  const remove = studiosResource.useDelete();

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Studio | null>(null);
  const [viewing, setViewing] = useState<Studio | null>(null);
  const [confirm, setConfirm] = useState<Confirm>(null);

  const openEdit = (studio: Studio) => {
    setViewing(null);
    setEditing(studio);
    setFormOpen(true);
  };

  const runConfirm = () => {
    if (!confirm) return;
    const { studio, type } = confirm;
    const onError = (e: Error) => toast.error(e instanceof ApiError ? e.message : "Amal bajarilmadi");
    const close = () => {
      setConfirm(null);
      setViewing(null);
    };
    if (type === "delete") remove.mutate(studio.id, { onSuccess: () => (toast.success("Studiya o'chirildi"), close()), onError });
    else
      update.mutate(
        { id: studio.id, values: { is_active: !studio.is_active } },
        { onSuccess: (s) => (toast.success(s.is_active ? "Faollashtirildi" : "Nofaol qilindi"), close()), onError },
      );
  };

  return (
    <>
      <PageHeader
        title="Studiyalar"
        crumb="Boshqaruv / Studiyalar"
        actions={
          can("studios.create") && (
            <Button
              onClick={() => {
                setEditing(null);
                setFormOpen(true);
              }}
            >
              <PlusIcon /> Studiya qo&apos;shish
            </Button>
          )
        }
      />

      <GlassCard className="p-4 sm:p-5">
        <ListToolbar
          search={list.search}
          onSearch={list.setSearch}
          placeholder="Studiya nomi, manzil yoki mas'ul shaxs"
          filters={[STATUS_FILTER]}
          values={list.filters}
          onFilter={list.setFilter}
          ordering={{ value: list.ordering, options: ORDERING, onChange: list.setOrdering }}
        />
      </GlassCard>

      {isPending ? (
        <CardsSkeleton />
      ) : error ? (
        <GlassCard>
          <ErrorState error={error} onRetry={() => refetch()} />
        </GlassCard>
      ) : data.results.length === 0 ? (
        <GlassCard>
          <EmptyState
            title={list.hasQuery ? "Hech narsa topilmadi" : "Hali studiyalar yo'q"}
            description={
              list.hasQuery ? "Qidiruvni o'zgartirib ko'ring." : "Avval 'Studiya' rolidagi foydalanuvchi yarating, so'ng studiya qo'shing."
            }
          />
        </GlassCard>
      ) : (
        <motion.section
          key={JSON.stringify(list.params)}
          variants={listContainer(stagger.cards)}
          initial="initial"
          animate="animate"
          className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-5"
        >
          {data.results.map((studio) => (
            <GlassCard key={studio.id} interactive className="flex flex-col overflow-hidden p-0 sm:p-0">
              <button type="button" onClick={() => setViewing(studio)} className="text-left" aria-label={`${studio.name}: batafsil`}>
                <Cover studio={studio} className="h-28" />
              </button>
              <div className="flex flex-col gap-3 p-5">
                <div className="flex items-start justify-between gap-2">
                  <button type="button" onClick={() => setViewing(studio)} className="min-w-0 text-left">
                    <h3 className="truncate font-bold">{studio.name}</h3>
                    <p className="mt-0.5 flex items-center gap-1 truncate text-xs text-muted-foreground">
                      <MapPinIcon className="size-3.5 shrink-0" aria-hidden />
                      {studio.address}
                    </p>
                  </button>
                  {(can("studios.update") || can("studios.delete")) && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon-sm" aria-label={`${studio.name}: amallar`}>
                          <MoreHorizontalIcon />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48">
                        {can("studios.update") && (
                          <>
                            <DropdownMenuItem onSelect={() => openEdit(studio)}>
                              <PencilIcon /> Tahrirlash
                            </DropdownMenuItem>
                            <DropdownMenuItem onSelect={() => setConfirm({ type: "toggle", studio })}>
                              <PowerIcon /> {studio.is_active ? "Nofaol qilish" : "Faollashtirish"}
                            </DropdownMenuItem>
                          </>
                        )}
                        {can("studios.delete") && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem variant="destructive" onSelect={() => setConfirm({ type: "delete", studio })}>
                              <Trash2Icon /> O&apos;chirish
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
                <div className="flex items-center gap-2.5 rounded-2xl bg-muted/60 p-2.5">
                  <UserAvatar
                    id={studio.responsible_user.id}
                    first={studio.responsible_user.first_name}
                    last={studio.responsible_user.last_name}
                    src={studio.responsible_user.profile_picture}
                    className="size-8 text-xs"
                  />
                  <div className="flex min-w-0 flex-col">
                    <span className="truncate text-[13px] font-semibold">{studio.responsible_user.full_name}</span>
                    <span className="text-[11px] text-muted-foreground">Mas&apos;ul shaxs</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <StatusBadge active={studio.is_active} />
                  <span className="text-xs text-muted-foreground tabular-nums">{formatDate(studio.created_at)}</span>
                </div>
              </div>
            </GlassCard>
          ))}
        </motion.section>
      )}

      {data && data.count > 0 && (
        <Pagination page={data.page} totalPages={data.total_pages} count={data.count} pageSize={data.page_size} onPage={list.setPage} />
      )}

      <StudioFormDialog open={formOpen} onOpenChange={setFormOpen} studio={editing} />

      <MotionDrawer
        open={Boolean(viewing)}
        onOpenChange={(o) => !o && setViewing(null)}
        title="Studiya tafsiloti"
        footer={
          viewing && can("studios.update") ? (
            <>
              <Button variant="outline" className="h-11 flex-1" onClick={() => setConfirm({ type: "toggle", studio: viewing })}>
                {viewing.is_active ? "Nofaol qilish" : "Faollashtirish"}
              </Button>
              <Button className="h-11 flex-1" onClick={() => openEdit(viewing)}>
                Tahrirlash
              </Button>
            </>
          ) : undefined
        }
      >
        {viewing && (
          <>
            <Cover studio={viewing} className="h-40 rounded-3xl" />
            <div className="flex flex-col gap-1">
              <h3 className="text-xl font-extrabold">{viewing.name}</h3>
              <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <MapPinIcon className="size-4" aria-hidden /> {viewing.address}
              </p>
            </div>
            <div className="rounded-2xl border border-glass-border bg-muted/40 px-4">
              {[
                ["Holat", <StatusBadge key="s" active={viewing.is_active} />],
                ["Mas'ul shaxs", viewing.responsible_user.full_name],
                ["Mas'ul telefon", formatPhone(viewing.responsible_user.phone_number)],
                ["Mas'ul JSHSHIR", viewing.responsible_user.pinfl_masked ?? "—"],
                ["Yaratilgan", formatDate(viewing.created_at)],
                ["Yangilangan", formatDate(viewing.updated_at)],
              ].map(([label, value]) => (
                <div
                  key={String(label)}
                  className="flex items-center justify-between gap-4 border-b border-border/70 py-3 text-sm last:border-b-0"
                >
                  <span className="text-muted-foreground">{label}</span>
                  <span className="text-right font-medium tabular-nums">{value}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </MotionDrawer>

      <ConfirmDialog
        open={Boolean(confirm)}
        onOpenChange={(o) => !o && setConfirm(null)}
        pending={update.isPending || remove.isPending}
        onConfirm={runConfirm}
        tone={confirm?.type === "delete" ? "danger" : "warning"}
        title={
          confirm?.type === "delete"
            ? "Studiyani o'chirasizmi?"
            : confirm?.studio.is_active
              ? "Studiyani nofaol qilasizmi?"
              : "Faollashtirasizmi?"
        }
        confirmLabel={confirm?.type === "delete" ? "O'chirish" : confirm?.studio.is_active ? "Nofaol qilish" : "Faollashtirish"}
        description={
          <>
            <b className="text-foreground">{confirm?.studio.name}</b>{" "}
            {confirm?.type === "delete"
              ? "ro'yxatdan yashiriladi. Ma'lumotlar audit uchun saqlanadi."
              : confirm?.studio.is_active
                ? "nofaol holatga o'tadi. Keyin qayta faollashtirish mumkin."
                : "yana faol bo'ladi."}
          </>
        }
      />
    </>
  );
}

export default function StudiosPage() {
  return (
    <RequirePermission requires="studios.view">
      <PageTransition>
        <StudiosContent />
      </PageTransition>
    </RequirePermission>
  );
}
