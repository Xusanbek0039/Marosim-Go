"use client";

import { KeyRoundIcon, Loader2Icon, MoreHorizontalIcon, PencilIcon, PlusIcon, PowerIcon, Trash2Icon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { CardsSkeleton, EmptyState, ErrorState, GlassCard, PageHeader, Pagination, StatusBadge, UserAvatar } from "@/components/common";
import { ListToolbar } from "@/components/common/list-toolbar";
import { RequirePermission } from "@/components/layout/require-permission";
import { ConfirmDialog } from "@/components/motion/confirm-dialog";
import { MotionDialog } from "@/components/motion/motion-dialog";
import { PageTransition } from "@/components/motion/page-transition";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { PermissionsEditor } from "@/features/people/permissions-editor";
import { PersonDrawer } from "@/features/people/person-drawer";
import { PersonFormDialog } from "@/features/people/person-form-dialog";
import { adminsResource } from "@/features/resources";
import { STATUS_FILTER, useListState } from "@/features/use-list-state";
import { ApiError } from "@/lib/api/client";
import type { Admin, PermissionCode } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { listContainer, stagger } from "@/motion/tokens";

const ORDERING = [
  { value: "-created_at", label: "Eng yangilari" },
  { value: "first_name", label: "Ism (A–Z)" },
  { value: "-last_login", label: "Oxirgi kirish" },
];

function PermissionsDialog({ admin, onClose }: { admin: Admin | null; onClose: () => void }) {
  const update = adminsResource.useUpdate();
  const [value, setValue] = useState<PermissionCode[]>([]);

  useEffect(() => {
    if (admin) setValue(admin.permissions);
  }, [admin]);

  return (
    <MotionDialog
      open={Boolean(admin)}
      onOpenChange={(o) => !o && !update.isPending && onClose()}
      title="Ruxsatlarni tahrirlash"
      description={admin ? `${admin.full_name} qaysi bo'limlarda nima qila olishini belgilang.` : undefined}
      size="lg"
    >
      <PermissionsEditor value={value} onChange={setValue} />
      <div className="flex gap-3">
        <Button variant="outline" className="h-11 flex-1" onClick={onClose} disabled={update.isPending}>
          Bekor qilish
        </Button>
        <Button
          className="h-11 flex-1"
          disabled={update.isPending}
          onClick={() =>
            admin &&
            update.mutate(
              { id: admin.id, values: { permissions: value } },
              {
                onSuccess: () => {
                  toast.success("Ruxsatlar yangilandi");
                  onClose();
                },
                onError: (e) => toast.error(e instanceof ApiError ? e.message : "Saqlab bo'lmadi"),
              },
            )
          }
        >
          {update.isPending && <Loader2Icon className="animate-spin" />}
          Saqlash
        </Button>
      </div>
    </MotionDialog>
  );
}

type Confirm = { type: "delete" | "toggle"; admin: Admin } | null;

function AdminsContent() {
  const list = useListState({ ordering: "-created_at", pageSize: 12 });
  const { data, error, isPending, refetch } = adminsResource.useList(list.params);
  const update = adminsResource.useUpdate();
  const remove = adminsResource.useDelete();

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Admin | null>(null);
  const [viewing, setViewing] = useState<Admin | null>(null);
  const [perms, setPerms] = useState<Admin | null>(null);
  const [confirm, setConfirm] = useState<Confirm>(null);

  const openEdit = (admin: Admin) => {
    setViewing(null);
    setEditing(admin);
    setFormOpen(true);
  };

  const runConfirm = () => {
    if (!confirm) return;
    const { admin, type } = confirm;
    const onError = (e: Error) => toast.error(e instanceof ApiError ? e.message : "Amal bajarilmadi");
    const close = () => {
      setConfirm(null);
      setViewing(null);
    };
    if (type === "delete") {
      remove.mutate(admin.id, { onSuccess: () => (toast.success("Admin o'chirildi"), close()), onError });
    } else {
      update.mutate(
        { id: admin.id, values: { is_active: !admin.is_active } },
        { onSuccess: (u) => (toast.success(u.is_active ? "Faollashtirildi" : "Nofaol qilindi"), close()), onError },
      );
    }
  };

  return (
    <>
      <PageHeader
        title="Adminlar"
        crumb="Boshqaruv / Adminlar"
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <PlusIcon /> Admin qo&apos;shish
          </Button>
        }
      />

      <GlassCard className="p-4 sm:p-5">
        <ListToolbar
          search={list.search}
          onSearch={list.setSearch}
          placeholder="Ism yoki email bo'yicha qidirish"
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
            title={list.hasQuery ? "Hech narsa topilmadi" : "Hali adminlar yo'q"}
            description={list.hasQuery ? "Qidiruvni o'zgartirib ko'ring." : "Admin qo'shib, unga kerakli ruxsatlarni bering."}
          />
        </GlassCard>
      ) : (
        <motion.section
          key={JSON.stringify(list.params)}
          variants={listContainer(stagger.cards)}
          initial="initial"
          animate="animate"
          className="grid grid-cols-[repeat(auto-fill,minmax(270px,1fr))] gap-5"
        >
          <AnimatePresence>
            {data.results.map((admin) => (
              <GlassCard key={admin.id} interactive layout className="flex flex-col gap-4">
                <div className="flex items-start gap-3">
                  <button type="button" onClick={() => setViewing(admin)} className="flex min-w-0 flex-1 items-center gap-3 text-left">
                    <UserAvatar
                      id={admin.id}
                      first={admin.first_name}
                      last={admin.last_name}
                      src={admin.profile_picture}
                      rounded="2xl"
                      className="size-12"
                    />
                    <span className="flex min-w-0 flex-col">
                      <span className="truncate font-bold">{admin.full_name}</span>
                      <span className="truncate text-xs text-muted-foreground">{admin.email}</span>
                    </span>
                  </button>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon-sm" aria-label={`${admin.full_name}: amallar`}>
                        <MoreHorizontalIcon />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-52">
                      <DropdownMenuItem onSelect={() => setPerms(admin)}>
                        <KeyRoundIcon /> Ruxsatlar
                      </DropdownMenuItem>
                      <DropdownMenuItem onSelect={() => openEdit(admin)}>
                        <PencilIcon /> Tahrirlash
                      </DropdownMenuItem>
                      <DropdownMenuItem onSelect={() => setConfirm({ type: "toggle", admin })}>
                        <PowerIcon /> {admin.is_active ? "Nofaol qilish" : "Faollashtirish"}
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem variant="destructive" onSelect={() => setConfirm({ type: "delete", admin })}>
                        <Trash2Icon /> O&apos;chirish
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <div className="flex justify-between text-[13px]">
                  <span className="text-muted-foreground">Oxirgi kirish</span>
                  <span className="font-semibold tabular-nums">{formatDateTime(admin.last_login)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <StatusBadge active={admin.is_active} />
                  <button
                    type="button"
                    onClick={() => setPerms(admin)}
                    className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/12 px-3 py-1 text-xs font-bold text-blue-700 transition hover:bg-blue-500/20 dark:text-blue-300"
                  >
                    <KeyRoundIcon className="size-3.5" aria-hidden />
                    {admin.permissions.length} ta ruxsat
                  </button>
                </div>
              </GlassCard>
            ))}
          </AnimatePresence>
        </motion.section>
      )}

      {data && data.count > 0 && (
        <Pagination page={data.page} totalPages={data.total_pages} count={data.count} pageSize={data.page_size} onPage={list.setPage} />
      )}

      <PersonFormDialog kind="admin" open={formOpen} onOpenChange={setFormOpen} person={editing} />
      <PersonDrawer
        kind="admin"
        person={viewing}
        open={Boolean(viewing)}
        onOpenChange={(o) => !o && setViewing(null)}
        onEdit={viewing ? () => openEdit(viewing) : undefined}
        onToggleActive={viewing ? () => setConfirm({ type: "toggle", admin: viewing }) : undefined}
      />
      <PermissionsDialog admin={perms} onClose={() => setPerms(null)} />
      <ConfirmDialog
        open={Boolean(confirm)}
        onOpenChange={(o) => !o && setConfirm(null)}
        pending={update.isPending || remove.isPending}
        onConfirm={runConfirm}
        tone={confirm?.type === "delete" ? "danger" : "warning"}
        title={
          confirm?.type === "delete" ? "Adminni o'chirasizmi?" : confirm?.admin.is_active ? "Adminni nofaol qilasizmi?" : "Faollashtirasizmi?"
        }
        confirmLabel={confirm?.type === "delete" ? "O'chirish" : confirm?.admin.is_active ? "Nofaol qilish" : "Faollashtirish"}
        description={
          <>
            <b className="text-foreground">{confirm?.admin.full_name}</b>{" "}
            {confirm?.type === "delete"
              ? "panelga kira olmaydi va ro'yxatdan yashiriladi. Audit uchun ma'lumotlar saqlanadi."
              : confirm?.admin.is_active
                ? "tizimga kira olmaydi va uning barcha sessiyalari bekor qilinadi. Ma'lumotlari o'chirilmaydi."
                : "yana panelga kira oladi."}
          </>
        }
      />
    </>
  );
}

export default function AdminsPage() {
  return (
    <RequirePermission requires="super">
      <PageTransition>
        <AdminsContent />
      </PageTransition>
    </RequirePermission>
  );
}
