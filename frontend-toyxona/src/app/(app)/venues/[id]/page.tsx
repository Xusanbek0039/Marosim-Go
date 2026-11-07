"use client";

import {
  ArrowLeftIcon,
  Building2Icon,
  CalendarDaysIcon,
  ImagesIcon,
  ImageUpIcon,
  LayersIcon,
  MapPinIcon,
  PencilIcon,
  PhoneIcon,
  PlusIcon,
  SettingsIcon,
  ShieldCheckIcon,
  UserPlusIcon,
  UsersIcon,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { PhoneInput } from "@/components/phone-input";
import { CalendarPreview } from "@/components/calendar-preview";
import { GalleryTab } from "@/components/gallery-tab";
import { Avatar, Badge, Button, Card, cn, EmptyState, ErrorState, Field, Input, Modal, Select, Skeleton } from "@/components/ui";
import { VenueForm, venueToForm } from "@/components/venue-form";
import { ApiError } from "@/lib/api";
import { formatDateTime, formatMoney, formatPhone } from "@/lib/format";
import type { MembershipRole, Venue, VenueHall, VenueMember } from "@/lib/types";
import {
  can,
  MEMBER_ROLES,
  PUBLICATION,
  REGION_LABELS,
  useAddMember,
  useCreateHall,
  useMembers,
  useUpdateHall,
  useUpdateMember,
  useUpdateVenue,
  useVenue,
  VENUE_TYPE_LABELS,
} from "@/lib/venues";

type Tab = "schedule" | "profile" | "gallery" | "halls" | "team";

const errorText = (err: unknown, fallback: string) => (err instanceof ApiError ? err.message : fallback);
const digits = (s: string) => s.replace(/\D/g, "");

// ------------------------------------------------------------------ header
function VenueHeader({ venue }: { venue: Venue }) {
  const update = useUpdateVenue(venue.id);
  const file = useRef<HTMLInputElement>(null);
  const pub = PUBLICATION[venue.publication_status];
  const editable = can(venue, "EDIT_PROFILE");

  const upload = (f: File | undefined) => {
    if (!f) return;
    if (f.size > 6 * 1024 * 1024) return toast.error("Rasm 6 MB dan oshmasin");
    const form = new FormData();
    form.append("cover_image", f);
    update.mutate(form, {
      onSuccess: () => toast.success("Muqova yangilandi"),
      onError: (e) => toast.error(e instanceof ApiError ? (e.fieldErrors.cover_image ?? e.message) : "Yuklab bo'lmadi"),
    });
  };

  return (
    <Card className="overflow-hidden p-0 sm:p-0">
      <div className="relative h-40 bg-gradient-to-br from-blue-600/85 to-cyan-500/75 sm:h-52">
        {venue.cover_image ? (
          // eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side
          <img src={venue.cover_image} alt="" className="size-full object-cover" />
        ) : (
          <Building2Icon className="absolute right-6 bottom-4 size-24 text-white/20" aria-hidden />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/60 via-transparent" />
        {editable && (
          <>
            <input ref={file} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => upload(e.target.files?.[0])} />
            <Button size="sm" variant="outline" className="absolute top-3 right-3 text-white" loading={update.isPending} onClick={() => file.current?.click()}>
              <ImageUpIcon /> Muqova
            </Button>
          </>
        )}
        <div className="absolute bottom-4 left-5 right-5 text-white">
          <div className="mb-2 flex flex-wrap gap-1.5">
            <Badge tone={pub.tone}>{pub.label}</Badge>
            {!venue.is_active && <Badge tone="danger">Administrator bloklagan</Badge>}
          </div>
          <h1 className="truncate text-2xl font-extrabold tracking-tight drop-shadow sm:text-3xl">{venue.name}</h1>
        </div>
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-2 px-5 py-4 text-sm text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <MapPinIcon className="size-4" /> {REGION_LABELS[venue.region]}
          {venue.district ? `, ${venue.district}` : ""} · {venue.address}
        </span>
        {venue.phone_number && (
          <a href={`tel:${venue.phone_number}`} className="flex items-center gap-1.5 hover:text-foreground">
            <PhoneIcon className="size-4" /> <span className="tabular-nums">{formatPhone(venue.phone_number)}</span>
          </a>
        )}
        <span className="flex items-center gap-1.5">
          <UsersIcon className="size-4" /> {venue.capacity_min}–{venue.capacity_max} kishi
        </span>
        <span className="flex items-center gap-1.5 font-semibold text-foreground tabular-nums">{formatMoney(venue.base_price)}</span>
        {venue.membership_role && (
          <span className="ml-auto flex items-center gap-1.5">
            <ShieldCheckIcon className="size-4" /> Siz: {MEMBER_ROLES[venue.membership_role].label}
          </span>
        )}
      </div>
      <p className="border-t border-border/70 px-5 py-3 text-xs text-muted-foreground">
        {pub.hint}
        {venue.publication_status !== "APPROVED" && " Ommaga chiqarish so'rovi va administrator tasdig'i keyingi bosqichda (Phase E) qo'shiladi."}
      </p>
    </Card>
  );
}

// ------------------------------------------------------------------ tabs
function Tabs({ tab, setTab, tabs }: { tab: Tab; setTab: (t: Tab) => void; tabs: { key: Tab; label: string; icon: typeof LayersIcon }[] }) {
  return (
    <div className="glass flex gap-1 overflow-x-auto rounded-2xl p-1" role="tablist" aria-label="To'yxona bo'limlari">
      {tabs.map((t) => (
        <button
          key={t.key}
          type="button"
          role="tab"
          aria-selected={tab === t.key}
          onClick={() => setTab(t.key)}
          className={cn(
            "relative flex flex-1 items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold whitespace-nowrap transition-colors",
            tab === t.key ? "text-white" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {tab === t.key && (
            <motion.span layoutId="venue-tab" className="absolute inset-0 rounded-xl brand-gradient" transition={{ type: "spring", stiffness: 380, damping: 32 }} />
          )}
          <t.icon className="relative size-4" aria-hidden />
          <span className="relative">{t.label}</span>
        </button>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------ profile
function ProfileTab({ venue }: { venue: Venue }) {
  const update = useUpdateVenue(venue.id);
  const [errors, setErrors] = useState<Record<string, string>>({});
  if (!can(venue, "EDIT_PROFILE")) {
    return (
      <Card>
        <dl className="text-sm">
          {[
            ["Turi", VENUE_TYPE_LABELS[venue.venue_type]],
            ["Manzil", venue.address],
            ["Aloqa", formatPhone(venue.phone_number)],
            ["Tavsif", venue.description || "—"],
            ["Yangilangan", formatDateTime(venue.updated_at)],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 border-b border-border/70 py-3 last:border-b-0">
              <dt className="text-muted-foreground">{k}</dt>
              <dd className="text-right font-medium whitespace-pre-line">{v}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 text-xs text-muted-foreground">Sizda faqat ko&apos;rish huquqi bor.</p>
      </Card>
    );
  }
  return (
    <Card>
      <VenueForm
        key={venue.updated_at}
        initial={venueToForm(venue)}
        errors={errors}
        pending={update.isPending}
        submitLabel="Saqlash"
        onSubmit={(payload) => {
          setErrors({});
          update.mutate(payload, {
            onSuccess: () => toast.success("Saqlandi"),
            onError: (err) => {
              if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors);
              else toast.error(errorText(err, "Saqlab bo'lmadi"));
            },
          });
        }}
      />
    </Card>
  );
}

// ------------------------------------------------------------------ halls
function HallForm({ venue, hall, onDone }: { venue: Venue; hall?: VenueHall; onDone: () => void }) {
  const create = useCreateHall(venue.id);
  const update = useUpdateHall(venue.id);
  const [values, setValues] = useState({
    name: hall?.name ?? "",
    capacity: hall ? String(hall.capacity) : "",
    base_price: hall?.base_price ? String(Math.round(Number(hall.base_price))) : "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const pending = create.isPending || update.isPending;

  return (
    <form
      noValidate
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        const local: Record<string, string> = {};
        if (!values.name.trim()) local.name = "Zal nomini kiriting";
        if (!Number(digits(values.capacity))) local.capacity = "Sig'imni kiriting";
        setErrors(local);
        if (Object.keys(local).length) return;
        const body = {
          name: values.name.trim(),
          capacity: Number(digits(values.capacity)),
          base_price: digits(values.base_price) || null,
        };
        const handlers = {
          onSuccess: () => {
            toast.success(hall ? "Zal saqlandi" : "Zal qo'shildi");
            onDone();
          },
          onError: (err: unknown) => {
            if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors);
            else toast.error(errorText(err, "Saqlab bo'lmadi"));
          },
        };
        if (hall) update.mutate({ id: hall.id, ...body }, handlers);
        else create.mutate(body, handlers);
      }}
    >
      <Field label="Zal nomi" htmlFor="hall_name" error={errors.name}>
        <Input id="hall_name" value={values.name} onChange={(e) => setValues((v) => ({ ...v, name: e.target.value }))} maxLength={100} placeholder="Masalan: Oq zal" />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Sig'im (kishi)" htmlFor="hall_capacity" error={errors.capacity}>
          <Input id="hall_capacity" inputMode="numeric" value={values.capacity} onChange={(e) => setValues((v) => ({ ...v, capacity: e.target.value }))} className="tabular-nums" />
        </Field>
        <Field label="Narx (so'm)" htmlFor="hall_price" error={errors.base_price} hint={`Bo'sh qoldirilsa: ${formatMoney(venue.base_price)}`}>
          <Input
            id="hall_price"
            inputMode="numeric"
            value={values.base_price.replace(/\B(?=(\d{3})+(?!\d))/g, " ")}
            onChange={(e) => setValues((v) => ({ ...v, base_price: digits(e.target.value) }))}
            className="tabular-nums"
          />
        </Field>
      </div>
      <Button type="submit" loading={pending}>
        {hall ? "Saqlash" : "Qo'shish"}
      </Button>
    </form>
  );
}

function HallsTab({ venue }: { venue: Venue }) {
  const manage = can(venue, "MANAGE_HALLS");
  const toggle = useUpdateHall(venue.id);
  const [editing, setEditing] = useState<VenueHall | "new" | null>(null);

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">Zallar</h2>
          <p className="text-sm text-muted-foreground">Har bir zalning bandligi alohida yuritiladi. Bitta zal band bo&apos;lsa, boshqasi bo&apos;sh qoladi.</p>
        </div>
        {manage && (
          <Button size="sm" onClick={() => setEditing("new")}>
            <PlusIcon /> Zal
          </Button>
        )}
      </div>
      {venue.halls.length === 0 ? (
        <EmptyState title="Zal yo'q" />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          <AnimatePresence initial={false}>
            {venue.halls.map((h) => (
              <motion.li
                key={h.id}
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn("flex items-center gap-3 rounded-2xl border border-glass-border bg-muted/40 p-4", !h.is_active && "opacity-60")}
              >
                <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 text-white">
                  <LayersIcon className="size-5" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-bold">{h.name}</p>
                  <p className="text-xs text-muted-foreground tabular-nums">
                    {h.capacity} kishi · {formatMoney(h.effective_base_price)}
                    {h.base_price === null && " (umumiy)"}
                  </p>
                </div>
                {manage ? (
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={toggle.isPending && toggle.variables?.id === h.id}
                      onClick={() =>
                        toggle.mutate(
                          { id: h.id, is_active: !h.is_active },
                          { onError: (e) => toast.error(errorText(e, "O'zgartirib bo'lmadi")) },
                        )
                      }
                    >
                      {h.is_active ? "O'chirish" : "Yoqish"}
                    </Button>
                    <Button size="sm" variant="ghost" aria-label="Tahrirlash" onClick={() => setEditing(h)}>
                      <PencilIcon />
                    </Button>
                  </div>
                ) : (
                  !h.is_active && <Badge>Nofaol</Badge>
                )}
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
      <Modal open={editing !== null} onClose={() => setEditing(null)} title={editing === "new" ? "Yangi zal" : "Zalni tahrirlash"}>
        {editing !== null && <HallForm venue={venue} hall={editing === "new" ? undefined : editing} onDone={() => setEditing(null)} />}
      </Modal>
    </Card>
  );
}

// ------------------------------------------------------------------ team
function AddMemberForm({ venueId }: { venueId: string }) {
  const add = useAddMember(venueId);
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState<MembershipRole>("MANAGER");
  const [errors, setErrors] = useState<Record<string, string>>({});
  return (
    <form
      noValidate
      className="flex flex-col gap-3 rounded-2xl border border-glass-border bg-muted/40 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        setErrors({});
        add.mutate(
          { phone_number: phone, role },
          {
            onSuccess: () => {
              toast.success("A'zo qo'shildi");
              setPhone("");
            },
            onError: (err) => {
              if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors);
              else toast.error(errorText(err, "Qo'shib bo'lmadi"));
            },
          },
        );
      }}
    >
      <p className="text-sm font-bold">Jamoaga qo&apos;shish</p>
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_190px_auto] sm:items-start">
        <Field label="Telefon raqam" htmlFor="member_phone" error={errors.phone_number}>
          <PhoneInput id="member_phone" value={phone} onChange={setPhone} />
        </Field>
        <Field label="Rol" htmlFor="member_role" error={errors.role}>
          <Select id="member_role" value={role} onChange={(e) => setRole(e.target.value as MembershipRole)}>
            {(Object.keys(MEMBER_ROLES) as MembershipRole[]).map((r) => (
              <option key={r} value={r}>
                {MEMBER_ROLES[r].label}
              </option>
            ))}
          </Select>
        </Field>
        <Button type="submit" loading={add.isPending} className="sm:mt-[26px]">
          <UserPlusIcon /> Qo&apos;shish
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        {MEMBER_ROLES[role].hint}. Faqat platformada &quot;To&apos;yxona&quot; hisobi ochilgan raqamni qo&apos;shish mumkin.
      </p>
    </form>
  );
}

function MemberRow({ venueId, member }: { venueId: string; member: VenueMember }) {
  const update = useUpdateMember(venueId);
  const name = member.user.full_name || formatPhone(member.user.phone_number);
  const [first, last] = name.split(" ");
  const change = (body: { role?: MembershipRole; is_active?: boolean }) =>
    update.mutate({ id: member.id, ...body }, { onSuccess: () => toast.success("Saqlandi"), onError: (e) => toast.error(errorText(e, "O'zgartirib bo'lmadi")) });

  return (
    <li className={cn("flex flex-wrap items-center gap-3 border-t border-border/70 py-3 first:border-t-0", !member.is_active && "opacity-60")}>
      <Avatar first={first} last={last} className="size-9 text-xs" />
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold">{name}</p>
        <p className="text-xs text-muted-foreground tabular-nums">{formatPhone(member.user.phone_number)}</p>
      </div>
      <Select aria-label="Rol" className="h-9 w-44" value={member.role} disabled={update.isPending} onChange={(e) => change({ role: e.target.value as MembershipRole })}>
        {(Object.keys(MEMBER_ROLES) as MembershipRole[]).map((r) => (
          <option key={r} value={r}>
            {MEMBER_ROLES[r].label}
          </option>
        ))}
      </Select>
      <Button size="sm" variant={member.is_active ? "ghost" : "outline"} loading={update.isPending && update.variables?.is_active !== undefined} onClick={() => change({ is_active: !member.is_active })}>
        {member.is_active ? "Chetlatish" : "Qaytarish"}
      </Button>
    </li>
  );
}

function TeamTab({ venue }: { venue: Venue }) {
  const { data, error, isPending, refetch } = useMembers(venue.id, true);
  return (
    <Card className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-bold">Jamoa</h2>
        <p className="text-sm text-muted-foreground">Menejer va jadval yurituvchilar o&apos;z hisobidan kirib, ruxsat berilgan ishlarni bajaradi.</p>
      </div>
      <AddMemberForm venueId={venue.id} />
      {isPending ? (
        <Skeleton className="h-24" />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (
        <ul className="flex flex-col">
          {data.map((m) => (
            <MemberRow key={m.id} venueId={venue.id} member={m} />
          ))}
        </ul>
      )}
    </Card>
  );
}

// ------------------------------------------------------------------ page
export default function VenuePage() {
  const { id } = useParams<{ id: string }>();
  const { data: venue, error, isPending, refetch } = useVenue(id);
  const [tab, setTab] = useState<Tab>("schedule");

  const tabs: { key: Tab; label: string; icon: typeof LayersIcon }[] = [
    { key: "schedule", label: "Jadval", icon: CalendarDaysIcon },
    { key: "profile", label: "Profil", icon: SettingsIcon },
    { key: "gallery", label: "Rasmlar", icon: ImagesIcon },
    { key: "halls", label: "Zallar", icon: LayersIcon },
    ...(can(venue, "MANAGE_MEMBERS") ? [{ key: "team" as const, label: "Jamoa", icon: UsersIcon }] : []),
  ];

  return (
    <>
      <Link href="/" className="flex items-center gap-1.5 px-1 text-sm font-semibold text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-4" /> To&apos;yxonalarim
      </Link>
      {isPending ? (
        <>
          <Skeleton className="h-64 rounded-3xl" />
          <Skeleton className="h-12 rounded-2xl" />
        </>
      ) : error ? (
        <Card>
          <ErrorState error={error} onRetry={() => refetch()} />
        </Card>
      ) : (
        <>
          <VenueHeader venue={venue} />
          <Tabs tab={tab} setTab={setTab} tabs={tabs} />
          <AnimatePresence mode="wait">
            <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.2 }}>
              {tab === "schedule" && (
                <Card>
                  <CalendarPreview halls={venue.halls} />
                </Card>
              )}
              {tab === "profile" && <ProfileTab venue={venue} />}
              {tab === "gallery" && <GalleryTab venue={venue} />}
              {tab === "halls" && <HallsTab venue={venue} />}
              {tab === "team" && <TeamTab venue={venue} />}
            </motion.div>
          </AnimatePresence>
        </>
      )}
    </>
  );
}
