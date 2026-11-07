"use client";

import {
  Building2Icon,
  ImagePlusIcon,
  LayersIcon,
  Loader2Icon,
  MapPinIcon,
  MoreHorizontalIcon,
  PencilIcon,
  PhoneIcon,
  PlusIcon,
  PowerIcon,
  Trash2Icon,
  UsersIcon,
  XIcon,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { CardsSkeleton, EmptyState, ErrorState, GlassCard, PageHeader, Pagination, StatusBadge } from "@/components/common";
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
import { Input } from "@/components/ui/input";
import { useCan } from "@/features/auth/hooks";
import { STATUS_FILTER, useListState } from "@/features/use-list-state";
import {
  formatMoney,
  MAX_GALLERY_IMAGES,
  MAX_IMAGE_BYTES,
  MEMBER_ROLE_LABELS,
  PUBLICATION,
  REGION_LABELS,
  useAddHall,
  useDeleteImage,
  useUpdateHall,
  useUploadImage,
  VENUE_TYPE_LABELS,
  venuesResource,
} from "@/features/venues/api";
import { VenueFormDialog } from "@/features/venues/venue-form-dialog";
import { ApiError } from "@/lib/api/client";
import type { AdminVenue, PublicationStatus, VenueRegion } from "@/lib/api/types";
import { avatarGradient, formatDate, formatPhone } from "@/lib/format";
import { cn } from "@/lib/utils";
import { listContainer, stagger } from "@/motion/tokens";

const ORDERING = [
  { value: "-created_at", label: "Eng yangilari" },
  { value: "name", label: "Nomi (A–Z)" },
  { value: "base_price", label: "Arzonroq" },
  { value: "-capacity_max", label: "Sig'imi katta" },
];
const FILTERS = [
  STATUS_FILTER,
  {
    key: "publication_status",
    label: "Ommaga chiqish",
    options: (Object.keys(PUBLICATION) as PublicationStatus[]).map((k) => ({ value: k, label: PUBLICATION[k].label })),
  },
  { key: "region", label: "Hudud", options: (Object.keys(REGION_LABELS) as VenueRegion[]).map((k) => ({ value: k, label: REGION_LABELS[k] })) },
];

const errorText = (e: unknown, fallback: string) => (e instanceof ApiError ? (e.fieldErrors.image ?? e.fieldErrors.name ?? e.message) : fallback);

function PublicationBadge({ status }: { status: PublicationStatus }) {
  return <span className={cn("inline-flex h-6 items-center rounded-full px-2.5 text-xs font-bold", PUBLICATION[status].className)}>{PUBLICATION[status].label}</span>;
}

function Cover({ venue, className }: { venue: AdminVenue; className?: string }) {
  const src = venue.cover_image ?? venue.images[0]?.image;
  return (
    <div className={cn("relative overflow-hidden bg-gradient-to-br", avatarGradient(venue.id), className)}>
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element -- backend media, re-encoded server-side
        <img src={src} alt="" className="size-full object-cover" />
      ) : (
        <div className="flex size-full items-center justify-center text-white/85">
          <Building2Icon className="size-9" aria-hidden />
        </div>
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/45 to-transparent" aria-hidden />
    </div>
  );
}

// ------------------------------------------------------------------ gallery
function Gallery({ venue, editable }: { venue: AdminVenue; editable: boolean }) {
  const upload = useUploadImage(venue.id);
  const remove = useDeleteImage(venue.id);
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const left = MAX_GALLERY_IMAGES - venue.images.length;

  const add = async (files: FileList | null) => {
    if (!files?.length) return;
    const list = Array.from(files);
    const tooBig = list.filter((f) => f.size > MAX_IMAGE_BYTES);
    if (tooBig.length) toast.error(`${tooBig.length} ta rasm 5 MB dan katta, o'tkazib yuborildi`);
    const ok = list.filter((f) => f.size <= MAX_IMAGE_BYTES).slice(0, left);
    if (list.length - tooBig.length > left) toast.error(`Ko'pi bilan ${MAX_GALLERY_IMAGES} ta rasm: faqat ${left} tasi yuklanadi`);
    setBusy(true);
    let done = 0;
    for (const file of ok) {
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
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-bold">
          Galereya <span className="font-medium text-muted-foreground tabular-nums">{venue.images.length}/{MAX_GALLERY_IMAGES}</span>
        </h4>
        {editable && left > 0 && (
          <>
            <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={(e) => (add(e.target.files), (e.target.value = ""))} />
            <Button size="sm" variant="outline" onClick={() => input.current?.click()} disabled={busy}>
              {busy ? <Loader2Icon className="animate-spin" /> : <ImagePlusIcon />} Rasm qo&apos;shish
            </Button>
          </>
        )}
      </div>
      {venue.images.length === 0 ? (
        <p className="rounded-2xl bg-muted/50 p-4 text-center text-sm text-muted-foreground">Rasm yo&apos;q. JPG, PNG yoki WEBP, har biri 5 MB gacha.</p>
      ) : (
        <ul className="grid grid-cols-3 gap-2">
          <AnimatePresence initial={false}>
            {venue.images.map((img) => (
              <motion.li key={img.id} layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} className="group relative aspect-square overflow-hidden rounded-xl">
                {/* eslint-disable-next-line @next/next/no-img-element -- backend media */}
                <img src={img.image} alt="" className="size-full object-cover" />
                {editable && (
                  <button
                    type="button"
                    aria-label="Rasmni o'chirish"
                    onClick={() => remove.mutate(img.id, { onError: (e) => toast.error(errorText(e, "O'chirilmadi")) })}
                    className="absolute top-1.5 right-1.5 inline-flex size-7 items-center justify-center rounded-full bg-slate-950/70 text-white opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100"
                  >
                    <XIcon className="size-4" />
                  </button>
                )}
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </section>
  );
}

// -------------------------------------------------------------------- halls
function Halls({ venue, editable }: { venue: AdminVenue; editable: boolean }) {
  const add = useAddHall(venue.id);
  const update = useUpdateHall(venue.id);
  const [name, setName] = useState("");
  const [capacity, setCapacity] = useState("");
  return (
    <section className="flex flex-col gap-3">
      <h4 className="text-sm font-bold">Zallar</h4>
      <ul className="flex flex-col gap-2">
        {venue.halls.map((h) => (
          <li key={h.id} className={cn("flex items-center gap-3 rounded-2xl bg-muted/50 px-3.5 py-2.5 text-sm", !h.is_active && "opacity-60")}>
            <LayersIcon className="size-4 text-muted-foreground" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold">{h.name}</p>
              <p className="text-xs text-muted-foreground tabular-nums">
                {h.capacity} kishi · {formatMoney(h.effective_base_price)}
              </p>
            </div>
            {editable && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => update.mutate({ id: h.id, is_active: !h.is_active }, { onError: (e) => toast.error(errorText(e, "Bajarilmadi")) })}
              >
                {h.is_active ? "O'chirish" : "Yoqish"}
              </Button>
            )}
          </li>
        ))}
      </ul>
      {editable && (
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!name.trim() || !Number(capacity)) return toast.error("Zal nomi va sig'imini kiriting");
            add.mutate(
              { name: name.trim(), capacity: Number(capacity), base_price: null },
              {
                onSuccess: () => (setName(""), setCapacity(""), toast.success("Zal qo'shildi")),
                onError: (e) => toast.error(errorText(e, "Qo'shilmadi")),
              },
            );
          }}
        >
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Yangi zal nomi" aria-label="Zal nomi" className="h-9" />
          <Input value={capacity} onChange={(e) => setCapacity(e.target.value.replace(/\D/g, ""))} placeholder="Sig'im" aria-label="Sig'im" inputMode="numeric" className="h-9 w-24" />
          <Button type="submit" size="sm" disabled={add.isPending} aria-label="Zal qo'shish">
            <PlusIcon />
          </Button>
        </form>
      )}
    </section>
  );
}

type Confirm = { type: "delete" | "toggle"; venue: AdminVenue } | null;

function VenuesContent() {
  const can = useCan();
  const list = useListState({ ordering: "-created_at", pageSize: 12 });
  const { data, error, isPending, refetch } = venuesResource.useList(list.params);
  const update = venuesResource.useUpdate();
  const remove = venuesResource.useDelete();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<AdminVenue | null>(null);
  const [viewingId, setViewingId] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<Confirm>(null);
  // Live detail so gallery / hall changes show up in the open drawer immediately.
  const detail = venuesResource.useDetail(viewingId);
  const viewing = detail.data ?? data?.results.find((v) => v.id === viewingId) ?? null;

  const openEdit = (venue: AdminVenue) => {
    setViewingId(null);
    setEditing(venue);
    setFormOpen(true);
  };

  const runConfirm = () => {
    if (!confirm) return;
    const { venue, type } = confirm;
    const onError = (e: Error) => toast.error(e instanceof ApiError ? e.message : "Amal bajarilmadi");
    const close = () => {
      setConfirm(null);
      setViewingId(null);
    };
    if (type === "delete") remove.mutate(venue.id, { onSuccess: () => (toast.success("To'yxona o'chirildi"), close()), onError });
    else
      update.mutate(
        { id: venue.id, values: { is_active: !venue.is_active } },
        { onSuccess: (v) => (toast.success(v.is_active ? "Faollashtirildi" : "Bloklandi"), close()), onError },
      );
  };

  return (
    <>
      <PageHeader
        title="To'yxonalar"
        crumb="Boshqaruv / To'yxonalar"
        actions={
          can("venues.create") && (
            <Button
              onClick={() => {
                setEditing(null);
                setFormOpen(true);
              }}
            >
              <PlusIcon /> To&apos;yxona qo&apos;shish
            </Button>
          )
        }
      />

      <GlassCard className="p-4 sm:p-5">
        <ListToolbar
          search={list.search}
          onSearch={list.setSearch}
          placeholder="Nomi, manzili, tumani yoki telefoni"
          filters={FILTERS}
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
            title={list.hasQuery ? "Hech narsa topilmadi" : "Hali to'yxonalar yo'q"}
            description={list.hasQuery ? "Qidiruv yoki filtrni o'zgartiring." : "Avval 'To'yxona' rolidagi foydalanuvchi yarating, so'ng to'yxona qo'shing."}
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
          {data.results.map((venue) => {
            const owner = venue.members.find((m) => m.role === "OWNER");
            return (
              <GlassCard key={venue.id} interactive className="flex flex-col overflow-hidden p-0 sm:p-0">
                <button type="button" onClick={() => setViewingId(venue.id)} className="relative text-left" aria-label={`${venue.name}: batafsil`}>
                  <Cover venue={venue} className="h-32" />
                  <span className="absolute top-3 left-3">
                    <PublicationBadge status={venue.publication_status} />
                  </span>
                </button>
                <div className="flex flex-col gap-3 p-5">
                  <div className="flex items-start justify-between gap-2">
                    <button type="button" onClick={() => setViewingId(venue.id)} className="min-w-0 text-left">
                      <h3 className="truncate font-bold">{venue.name}</h3>
                      <p className="mt-0.5 flex items-center gap-1 truncate text-xs text-muted-foreground">
                        <MapPinIcon className="size-3.5 shrink-0" aria-hidden />
                        {REGION_LABELS[venue.region]}
                        {venue.district ? `, ${venue.district}` : ""}
                      </p>
                    </button>
                    {(can("venues.update") || can("venues.delete")) && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon-sm" aria-label={`${venue.name}: amallar`}>
                            <MoreHorizontalIcon />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          {can("venues.update") && (
                            <>
                              <DropdownMenuItem onSelect={() => openEdit(venue)}>
                                <PencilIcon /> Tahrirlash
                              </DropdownMenuItem>
                              <DropdownMenuItem onSelect={() => setConfirm({ type: "toggle", venue })}>
                                <PowerIcon /> {venue.is_active ? "Bloklash" : "Faollashtirish"}
                              </DropdownMenuItem>
                            </>
                          )}
                          {can("venues.delete") && (
                            <>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem variant="destructive" onSelect={() => setConfirm({ type: "delete", venue })}>
                                <Trash2Icon /> O&apos;chirish
                              </DropdownMenuItem>
                            </>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </div>
                  <dl className="grid grid-cols-3 gap-2 text-center">
                    {[
                      ["Zal", String(venue.halls.filter((h) => h.is_active).length)],
                      ["Sig'im", `${venue.capacity_min}–${venue.capacity_max}`],
                      ["Narx", formatMoney(venue.base_price).replace(" so'm", "")],
                    ].map(([k, v]) => (
                      <div key={k} className="rounded-xl bg-muted/60 px-2 py-1.5">
                        <dt className="text-[10px] font-bold text-muted-foreground uppercase">{k}</dt>
                        <dd className="truncate text-[13px] font-bold tabular-nums">{v}</dd>
                      </div>
                    ))}
                  </dl>
                  <div className="flex items-center justify-between gap-2">
                    <StatusBadge active={venue.is_active} />
                    <span className="truncate text-xs text-muted-foreground">{owner?.full_name || "—"}</span>
                  </div>
                </div>
              </GlassCard>
            );
          })}
        </motion.section>
      )}

      {data && data.count > 0 && (
        <Pagination page={data.page} totalPages={data.total_pages} count={data.count} pageSize={data.page_size} onPage={list.setPage} />
      )}

      <VenueFormDialog open={formOpen} onOpenChange={setFormOpen} venue={editing} />

      <MotionDrawer
        open={Boolean(viewingId)}
        onOpenChange={(o) => !o && setViewingId(null)}
        title="To'yxona tafsiloti"
        footer={
          viewing && can("venues.update") ? (
            <>
              <Button variant="outline" className="h-11 flex-1" onClick={() => setConfirm({ type: "toggle", venue: viewing })}>
                {viewing.is_active ? "Bloklash" : "Faollashtirish"}
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
            <Cover venue={viewing} className="h-40 shrink-0 rounded-3xl" />
            <div className="flex flex-col gap-1.5">
              <div className="flex flex-wrap gap-1.5">
                <PublicationBadge status={viewing.publication_status} />
                <StatusBadge active={viewing.is_active} />
              </div>
              <h3 className="text-xl font-extrabold">{viewing.name}</h3>
              <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <MapPinIcon className="size-4 shrink-0" aria-hidden /> {viewing.address}
              </p>
              {viewing.phone_number && (
                <a href={`tel:${viewing.phone_number}`} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
                  <PhoneIcon className="size-4" aria-hidden /> <span className="tabular-nums">{formatPhone(viewing.phone_number)}</span>
                </a>
              )}
            </div>
            <div className="rounded-2xl border border-glass-border bg-muted/40 px-4">
              {[
                ["Turi", VENUE_TYPE_LABELS[viewing.venue_type]],
                ["Hudud", `${REGION_LABELS[viewing.region]}${viewing.district ? `, ${viewing.district}` : ""}`],
                ["Sig'im", `${viewing.capacity_min}–${viewing.capacity_max} kishi`],
                ["Asosiy narx", formatMoney(viewing.base_price)],
                ["Yaratilgan", formatDate(viewing.created_at)],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-4 border-b border-border/70 py-3 text-sm last:border-b-0">
                  <span className="text-muted-foreground">{label}</span>
                  <span className="text-right font-medium tabular-nums">{value}</span>
                </div>
              ))}
            </div>
            {viewing.description && <p className="text-sm leading-relaxed whitespace-pre-line text-muted-foreground">{viewing.description}</p>}
            <Gallery venue={viewing} editable={can("venues.update")} />
            <Halls venue={viewing} editable={can("venues.update")} />
            <section className="flex flex-col gap-2">
              <h4 className="flex items-center gap-1.5 text-sm font-bold">
                <UsersIcon className="size-4" aria-hidden /> Jamoa
              </h4>
              {viewing.members.map((m) => (
                <div key={m.membership_id} className={cn("flex items-center justify-between rounded-2xl bg-muted/50 px-3.5 py-2.5 text-sm", !m.is_active && "opacity-60")}>
                  <div className="min-w-0">
                    <p className="truncate font-semibold">{m.full_name || "—"}</p>
                    <p className="text-xs text-muted-foreground tabular-nums">{formatPhone(m.phone_number)}</p>
                  </div>
                  <span className="text-xs font-semibold text-muted-foreground">{MEMBER_ROLE_LABELS[m.role]}</span>
                </div>
              ))}
            </section>
          </>
        )}
      </MotionDrawer>

      <ConfirmDialog
        open={Boolean(confirm)}
        onOpenChange={(o) => !o && setConfirm(null)}
        pending={update.isPending || remove.isPending}
        onConfirm={runConfirm}
        tone={confirm?.type === "delete" ? "danger" : "warning"}
        title={confirm?.type === "delete" ? "To'yxonani o'chirasizmi?" : confirm?.venue.is_active ? "To'yxonani bloklaysizmi?" : "Faollashtirasizmi?"}
        confirmLabel={confirm?.type === "delete" ? "O'chirish" : confirm?.venue.is_active ? "Bloklash" : "Faollashtirish"}
        description={
          <>
            <b className="text-foreground">{confirm?.venue.name}</b>{" "}
            {confirm?.type === "delete"
              ? "ro'yxatdan yashiriladi. Ma'lumotlar audit uchun saqlanadi."
              : confirm?.venue.is_active
                ? "bloklanadi: egasi faqat ko'ra oladi, o'zgartira olmaydi."
                : "yana faol bo'ladi."}
          </>
        }
      />
    </>
  );
}

export default function VenuesPage() {
  return (
    <RequirePermission requires="venues.view">
      <PageTransition>
        <VenuesContent />
      </PageTransition>
    </RequirePermission>
  );
}
