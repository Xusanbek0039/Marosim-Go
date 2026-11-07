"use client";

import { EyeIcon, MoreHorizontalIcon, PencilIcon, PlusIcon, PowerIcon, Trash2Icon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { toast } from "sonner";

import {
  EmptyState,
  ErrorState,
  GlassCard,
  PageHeader,
  Pagination,
  RoleBadge,
  RowsSkeleton,
  StatusBadge,
  UserAvatar,
} from "@/components/common";
import { ListToolbar } from "@/components/common/list-toolbar";
import { RequirePermission } from "@/components/layout/require-permission";
import { ConfirmDialog } from "@/components/motion/confirm-dialog";
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
import { PersonDrawer } from "@/features/people/person-drawer";
import { PersonFormDialog } from "@/features/people/person-form-dialog";
import { usersResource } from "@/features/resources";
import { STATUS_FILTER, useListState } from "@/features/use-list-state";
import { ApiError } from "@/lib/api/client";
import type { ManagedUser } from "@/lib/api/types";
import { formatDate } from "@/lib/format";
import { spring } from "@/motion/tokens";

const ORDERING = [
  { value: "-created_at", label: "Eng yangilari" },
  { value: "created_at", label: "Eng eskilari" },
  { value: "first_name", label: "Ism (A–Z)" },
  { value: "-last_login", label: "Oxirgi kirish" },
];

type Confirm = { type: "delete" | "toggle"; user: ManagedUser } | null;

function UsersContent() {
  const can = useCan();
  const list = useListState({ ordering: "-created_at" });
  const { data, error, isPending, isFetching, refetch } = usersResource.useList(list.params);
  const update = usersResource.useUpdate();
  const remove = usersResource.useDelete();

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ManagedUser | null>(null);
  const [viewing, setViewing] = useState<ManagedUser | null>(null);
  const [confirm, setConfirm] = useState<Confirm>(null);

  const openCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };
  const openEdit = (user: ManagedUser) => {
    setViewing(null);
    setEditing(user);
    setFormOpen(true);
  };

  const runConfirm = () => {
    if (!confirm) return;
    const { user, type } = confirm;
    const onError = (e: Error) => toast.error(e instanceof ApiError ? e.message : "Amal bajarilmadi");
    if (type === "delete") {
      remove.mutate(user.id, {
        onSuccess: () => {
          toast.success(`${user.full_name} o'chirildi`);
          setConfirm(null);
          setViewing(null);
        },
        onError,
      });
    } else {
      update.mutate(
        { id: user.id, values: { is_active: !user.is_active } },
        {
          onSuccess: (updated) => {
            toast.success(updated.is_active ? "Faollashtirildi" : "Nofaol qilindi");
            setConfirm(null);
            setViewing((v) => (v?.id === updated.id ? updated : v));
          },
          onError,
        },
      );
    }
  };

  return (
    <>
      <PageHeader
        title="Foydalanuvchilar"
        crumb="Boshqaruv / Foydalanuvchilar"
        actions={
          can("users.create") && (
            <Button onClick={openCreate}>
              <PlusIcon /> Foydalanuvchi qo&apos;shish
            </Button>
          )
        }
      />

      <GlassCard className="flex flex-col gap-4 p-4 sm:p-5">
        <ListToolbar
          search={list.search}
          onSearch={list.setSearch}
          placeholder="Ism, email yoki manzil bo'yicha qidirish"
          filters={[
            STATUS_FILTER,
            {
              key: "role",
              label: "Rol",
              options: [
                { value: "USER", label: "Foydalanuvchi" },
                { value: "STUDIO", label: "Studiya" },
              ],
            },
          ]}
          values={list.filters}
          onFilter={list.setFilter}
          ordering={{ value: list.ordering, options: ORDERING, onChange: list.setOrdering }}
        />

        {isPending ? (
          <RowsSkeleton />
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.results.length === 0 ? (
          <EmptyState
            title={list.hasQuery ? "Hech narsa topilmadi" : "Hali foydalanuvchilar yo'q"}
            description={list.hasQuery ? "Qidiruv yoki filtrlarni o'zgartirib ko'ring." : "Birinchi foydalanuvchini qo'shing."}
            action={
              !list.hasQuery && can("users.create") ? (
                <Button onClick={openCreate}>
                  <PlusIcon /> Qo&apos;shish
                </Button>
              ) : undefined
            }
          />
        ) : (
          <div className={`overflow-x-auto transition-opacity ${isFetching ? "opacity-70" : ""}`}>
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="px-3 py-2.5 font-semibold">Foydalanuvchi</th>
                  <th className="px-3 py-2.5 font-semibold">Rol</th>
                  <th className="px-3 py-2.5 font-semibold">JSHSHIR</th>
                  <th className="px-3 py-2.5 font-semibold">Manzil</th>
                  <th className="px-3 py-2.5 font-semibold">Holat</th>
                  <th className="px-3 py-2.5 font-semibold">Qo&apos;shilgan</th>
                  <th className="px-3 py-2.5 text-right font-semibold">
                    <span className="sr-only">Amallar</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence initial={false}>
                  {data.results.map((user, i) => (
                    <motion.tr
                      key={user.id}
                      layout
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0, transition: { ...spring.soft, delay: i * 0.025 } }}
                      exit={{ opacity: 0 }}
                      className="cursor-pointer border-t border-border/70 transition-colors hover:bg-blue-500/[0.06]"
                      onClick={() => setViewing(user)}
                    >
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-3">
                          <UserAvatar id={user.id} first={user.first_name} last={user.last_name} src={user.profile_picture} />
                          <div className="flex min-w-0 flex-col">
                            <span className="truncate font-semibold">{user.full_name}</span>
                            <span className="truncate text-xs text-muted-foreground">{user.email}</span>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <RoleBadge role={user.role} />
                      </td>
                      <td className="px-3 py-3 tracking-wider text-muted-foreground tabular-nums">{user.pinfl_masked ?? "—"}</td>
                      <td className="max-w-[180px] truncate px-3 py-3 text-muted-foreground">{user.address || "—"}</td>
                      <td className="px-3 py-3">
                        <StatusBadge active={user.is_active} />
                      </td>
                      <td className="px-3 py-3 text-muted-foreground tabular-nums">{formatDate(user.created_at)}</td>
                      <td className="px-3 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <RowActions
                          user={user}
                          onView={() => setViewing(user)}
                          onEdit={can("users.update") ? () => openEdit(user) : undefined}
                          onToggle={can("users.update") ? () => setConfirm({ type: "toggle", user }) : undefined}
                          onDelete={can("users.delete") ? () => setConfirm({ type: "delete", user }) : undefined}
                        />
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        )}

        {data && (
          <Pagination
            page={data.page}
            totalPages={data.total_pages}
            count={data.count}
            pageSize={data.page_size}
            onPage={list.setPage}
          />
        )}
      </GlassCard>

      <PersonFormDialog kind="user" open={formOpen} onOpenChange={setFormOpen} person={editing} />
      <PersonDrawer
        kind="user"
        person={viewing}
        open={Boolean(viewing)}
        onOpenChange={(o) => !o && setViewing(null)}
        onEdit={can("users.update") && viewing ? () => openEdit(viewing) : undefined}
        onToggleActive={can("users.update") && viewing ? () => setConfirm({ type: "toggle", user: viewing }) : undefined}
      />
      <ConfirmDialog
        open={Boolean(confirm)}
        onOpenChange={(o) => !o && setConfirm(null)}
        pending={update.isPending || remove.isPending}
        onConfirm={runConfirm}
        tone={confirm?.type === "delete" ? "danger" : "warning"}
        title={
          confirm?.type === "delete"
            ? "Foydalanuvchini o'chirasizmi?"
            : confirm?.user.is_active
              ? "Nofaol qilasizmi?"
              : "Faollashtirasizmi?"
        }
        confirmLabel={confirm?.type === "delete" ? "O'chirish" : confirm?.user.is_active ? "Nofaol qilish" : "Faollashtirish"}
        description={
          confirm?.type === "delete" ? (
            <>
              <b className="text-foreground">{confirm.user.full_name}</b> ro&apos;yxatdan yashiriladi va tizimga kira olmaydi.
              Ma&apos;lumotlar xavfsizlik uchun bazada saqlanib qoladi.
            </>
          ) : confirm?.user.is_active ? (
            <>
              <b className="text-foreground">{confirm.user.full_name}</b> tizimga kira olmaydi va barcha sessiyalari yopiladi.
              Istalgan payt qayta faollashtirish mumkin.
            </>
          ) : (
            <>
              <b className="text-foreground">{confirm?.user.full_name}</b> yana tizimdan foydalana oladi.
            </>
          )
        }
      />
    </>
  );
}

function RowActions({
  user,
  onView,
  onEdit,
  onToggle,
  onDelete,
}: {
  user: ManagedUser;
  onView: () => void;
  onEdit?: () => void;
  onToggle?: () => void;
  onDelete?: () => void;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={`${user.full_name}: amallar`}>
          <MoreHorizontalIcon />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem onSelect={onView}>
          <EyeIcon /> Ko&apos;rish
        </DropdownMenuItem>
        {onEdit && (
          <DropdownMenuItem onSelect={onEdit}>
            <PencilIcon /> Tahrirlash
          </DropdownMenuItem>
        )}
        {onToggle && (
          <DropdownMenuItem onSelect={onToggle}>
            <PowerIcon /> {user.is_active ? "Nofaol qilish" : "Faollashtirish"}
          </DropdownMenuItem>
        )}
        {onDelete && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onSelect={onDelete}>
              <Trash2Icon /> O&apos;chirish
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function UsersPage() {
  return (
    <RequirePermission requires="users.view">
      <PageTransition>
        <UsersContent />
      </PageTransition>
    </RequirePermission>
  );
}
