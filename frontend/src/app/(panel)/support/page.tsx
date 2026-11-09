"use client";

import { CastleIcon, CheckIcon, ClipboardListIcon, InboxIcon, MailCheckIcon, MailQuestionIcon, PhoneIcon, PlusIcon, SendIcon, UserRoundPenIcon, VideoIcon } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState, ErrorState, GlassCard, PageHeader, Pagination, RowsSkeleton } from "@/components/common";
import { ListToolbar } from "@/components/common/list-toolbar";
import { MotionDialog } from "@/components/motion/motion-dialog";
import { PageTransition } from "@/components/motion/page-transition";
import { AnimatedTabs } from "@/components/monitoring/primitives";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCan, useMe } from "@/features/auth/hooks";
import {
  APPLICATION_KIND,
  APPLICATION_STATUS,
  type ApplicationKind,
  applicationsResource,
  type ApplicationStatus,
  AUTHOR_ROLES,
  myTickets,
  type PartnerApplication,
  STATUS,
  staffTickets,
  type Ticket,
  type TicketStatus,
  useCreateTicket,
  useStaffSummary,
  useThread,
} from "@/features/support/api";
import { useListState } from "@/features/use-list-state";
import { ApiError } from "@/lib/api/client";
import { formatDateTime, formatPhone } from "@/lib/format";
import { cn } from "@/lib/utils";

const errorText = (e: unknown, fallback = "Bajarilmadi") =>
  e instanceof ApiError ? (Object.values(e.fieldErrors)[0] as string | undefined) ?? e.message : fallback;

function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={cn("inline-flex h-6 items-center rounded-full px-2.5 text-xs font-bold", STATUS[status].className)}>{STATUS[status].label}</span>;
}

/** "Studiya · Nur Studio" / "To'yxona · Navro'z" / "Foydalanuvchi". */
function origin(t: Ticket) {
  const role = AUTHOR_ROLES[t.author_role] ?? t.author_role;
  const place = t.studio?.name ?? t.venue?.name;
  return place ? `${role} · ${place}` : role;
}

// ================================================================ thread
function ThreadDialog({ id, staff, onClose }: { id: string | null; staff: boolean; onClose: () => void }) {
  const { query, reply, close } = useThread(id, staff);
  const [body, setBody] = useState("");
  const t = query.data;
  const canWrite = staff ? Boolean(t?.can_reply) : true;

  return (
    <MotionDialog
      open={Boolean(id)}
      onOpenChange={(o) => !o && onClose()}
      size="lg"
      title={t?.subject ?? "Yordam xati"}
      description={
        t && staff
          ? `${t.author.name ?? "—"} · ${formatPhone(t.author.phone_number)} · ${origin(t)}${t.handled_by_name ? ` · javob bergan: ${t.handled_by_name}` : ""}`
          : t
            ? `Super Admin'ga · ${formatDateTime(t.created_at)}`
            : undefined
      }
      footer={
        t && (
          <>
            {t.status !== "CLOSED" && (staff ? t.can_reply : true) && (
              <Button
                variant="outline"
                className="h-11"
                disabled={close.isPending}
                onClick={() => close.mutate(undefined, { onSuccess: () => toast.success("Xat yopildi"), onError: (e) => toast.error(errorText(e)) })}
              >
                <CheckIcon /> Yopish
              </Button>
            )}
            {canWrite && (
              <Button
                className="h-11 flex-1"
                disabled={!body.trim() || reply.isPending}
                onClick={() => reply.mutate(body.trim(), { onSuccess: () => setBody(""), onError: (e) => toast.error(errorText(e)) })}
              >
                <SendIcon /> {staff ? "Javob yuborish" : "Yuborish"}
              </Button>
            )}
          </>
        )
      }
    >
      {query.isPending ? (
        <RowsSkeleton rows={3} />
      ) : query.error ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (
        t && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <StatusBadge status={t.status} />
              {t.closed_at && <span>Yopilgan: {formatDateTime(t.closed_at)}{t.closed_by_name ? ` · ${t.closed_by_name}` : ""}</span>}
            </div>
            <ul className="flex flex-col gap-3">
              {t.messages.map((m) => (
                <li key={m.id} className={cn("flex flex-col gap-1", m.is_mine ? "items-end" : "items-start")}>
                  <div
                    className={cn(
                      "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap",
                      m.is_mine ? "bg-gradient-to-r from-blue-600 to-cyan-600 text-white" : m.is_staff_reply ? "bg-cyan-500/10" : "bg-muted",
                    )}
                  >
                    {m.body}
                  </div>
                  <span className="px-1 text-xs text-muted-foreground">
                    {m.is_mine ? "Siz" : m.author_name}
                    {staff && !m.is_mine ? ` (${m.is_staff_reply ? (m.author_role === "SUPER_ADMIN" ? "Super Admin" : "Admin") : (AUTHOR_ROLES[m.author_role] ?? m.author_role)})` : ""} ·{" "}
                    {formatDateTime(m.created_at)}
                  </span>
                </li>
              ))}
            </ul>
            {canWrite ? (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="s-reply">{staff ? "Javob" : "Xabar"}</Label>
                <Textarea
                  id="s-reply"
                  maxLength={5000}
                  value={body}
                  placeholder={!staff && t.status === "CLOSED" ? "Yozsangiz, xat qayta ochiladi" : undefined}
                  onChange={(e) => setBody(e.target.value)}
                />
                {staff && t.status === "CLOSED" && <p className="text-xs text-muted-foreground">Xat yopilgan — muallif yozsa qayta ochiladi.</p>}
              </div>
            ) : (
              <p className="rounded-2xl bg-muted/60 p-3 text-xs text-muted-foreground">
                {t.audience === "SUPER_ADMIN" ? "Adminlarning xatlariga faqat Super Admin javob beradi. Siz faqat kuzatasiz." : "Bu xatga javob bera olmaysiz."}
              </p>
            )}
          </div>
        )
      )}
    </MotionDialog>
  );
}

// ================================================================ inbox
function SummaryCards() {
  const { data } = useStaffSummary();
  const cards = [
    { label: "Javob kutayotgan", value: data?.open, icon: MailQuestionIcon, tone: "from-amber-500 to-orange-500" },
    { label: "Javob berilgan", value: data?.answered, icon: MailCheckIcon, tone: "from-emerald-500 to-teal-500" },
    { label: "Yopilgan", value: data?.closed, icon: InboxIcon, tone: "from-slate-500 to-slate-600" },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {cards.map((c) => (
        <GlassCard key={c.label} className="flex items-center gap-4 p-4 sm:p-5">
          <span className={cn("flex size-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br text-white", c.tone)}>
            <c.icon className="size-5" aria-hidden />
          </span>
          <div>
            <p className="text-xs font-semibold text-muted-foreground">{c.label}</p>
            <p className="text-lg font-extrabold tabular-nums">{c.value ?? "—"}</p>
          </div>
        </GlassCard>
      ))}
    </div>
  );
}

function InboxTab({ seesAdmins }: { seesAdmins: boolean }) {
  const list = useListState({ ordering: "-last_message_at" });
  const { data, error, isPending, refetch } = staffTickets.useList(list.params);
  const [open, setOpen] = useState<string | null>(null);
  const filters = [
    { key: "status", label: "Holat", options: (Object.keys(STATUS) as TicketStatus[]).map((k) => ({ value: k, label: STATUS[k].label })) },
    {
      key: "author_role",
      label: "Kimdan",
      options: Object.entries(AUTHOR_ROLES)
        .filter(([role]) => seesAdmins || role !== "ADMIN")
        .map(([value, label]) => ({ value, label: label as string })),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <SummaryCards />
      <ListToolbar
        search={list.search}
        onSearch={list.setSearch}
        placeholder="Mavzu, ism, telefon, studiya yoki to'yxona"
        filters={filters}
        values={list.filters}
        onFilter={list.setFilter}
        ordering={{
          value: list.ordering,
          options: [
            { value: "-last_message_at", label: "Oxirgi xabar" },
            { value: "-created_at", label: "Eng yangilari" },
            { value: "created_at", label: "Eng eskilari" },
          ],
          onChange: list.setOrdering,
        }}
      />
      <GlassCard className="p-0 sm:p-0">
        {isPending ? (
          <div className="p-5">
            <RowsSkeleton />
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.results.length === 0 ? (
          <EmptyState title={list.hasQuery ? "Hech narsa topilmadi" : "Xat yo'q"} description="Studiya, to'yxona va foydalanuvchilar o'z panelidagi «Yordam» sahifasidan yozadi." />
        ) : (
          <ul className="divide-y divide-border/70">
            {data.results.map((t) => (
              <motion.li key={t.id} layout>
                <button type="button" onClick={() => setOpen(t.id)} className="flex w-full flex-wrap items-center gap-x-5 gap-y-1 px-5 py-4 text-left transition hover:bg-muted/50">
                  <div className="min-w-56 flex-1">
                    <p className="truncate font-semibold">{t.subject}</p>
                    <p className="truncate text-xs text-muted-foreground">{t.last_message}</p>
                  </div>
                  <div className="w-52 min-w-0">
                    <p className="truncate text-sm font-semibold">{t.author.name ?? "—"}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {origin(t)} · {formatPhone(t.author.phone_number)}
                    </p>
                  </div>
                  <div className="w-44 text-sm">
                    <StatusBadge status={t.status} />
                    <p className="mt-1 truncate text-xs text-muted-foreground">{t.handled_by_name ? `Javob: ${t.handled_by_name}` : formatDateTime(t.last_message_at)}</p>
                  </div>
                  {t.audience === "SUPER_ADMIN" && <span className="rounded-full bg-violet-500/14 px-2.5 py-0.5 text-xs font-bold text-violet-700 dark:text-violet-300">Admin → Super Admin</span>}
                </button>
              </motion.li>
            ))}
          </ul>
        )}
      </GlassCard>
      {data && data.total_pages > 1 && (
        <Pagination page={data.page} totalPages={data.total_pages} count={data.count} pageSize={data.page_size} onPage={list.setPage} />
      )}
      <ThreadDialog id={open} staff onClose={() => setOpen(null)} />
    </div>
  );
}

// ================================================================ my tickets (ADMIN → Super Admin)
function NewTicketDialog({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (id: string) => void }) {
  const create = useCreateTicket();
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const close = () => {
    setSubject("");
    setBody("");
    onClose();
  };
  return (
    <MotionDialog
      open={open}
      onOpenChange={(o) => !o && close()}
      title="Super Admin'ga yozish"
      description="Ruxsat, xato yoki savol — javob shu sahifada ko'rinadi."
      footer={
        <>
          <Button variant="outline" className="h-11 flex-1" onClick={close}>
            Bekor qilish
          </Button>
          <Button
            className="h-11 flex-1"
            disabled={!subject.trim() || !body.trim() || create.isPending}
            onClick={() =>
              create.mutate(
                { subject: subject.trim(), body: body.trim() },
                {
                  onSuccess: (t) => {
                    toast.success("Yuborildi");
                    close();
                    onCreated(t.id);
                  },
                  onError: (e) => toast.error(errorText(e, "Yuborilmadi")),
                },
              )
            }
          >
            <SendIcon /> Yuborish
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="n-subject">Mavzu</Label>
          <Input id="n-subject" maxLength={200} value={subject} onChange={(e) => setSubject(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="n-body">Xabar</Label>
          <Textarea id="n-body" maxLength={5000} className="min-h-36" value={body} onChange={(e) => setBody(e.target.value)} />
        </div>
      </div>
    </MotionDialog>
  );
}

function MineTab() {
  const list = useListState({ ordering: "-last_message_at" });
  const { data, error, isPending, refetch } = myTickets.useList(list.params);
  const [open, setOpen] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setCreating(true)}>
          <PlusIcon /> Super Admin&apos;ga yozish
        </Button>
      </div>
      <GlassCard className="p-0 sm:p-0">
        {isPending ? (
          <div className="p-5">
            <RowsSkeleton rows={3} />
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.results.length === 0 ? (
          <EmptyState title="Hali xat yozmagansiz" description="Ruxsat yoki savol bo'yicha Super Admin'ga shu yerdan yozing." />
        ) : (
          <ul className="divide-y divide-border/70">
            {data.results.map((t) => (
              <li key={t.id}>
                <button type="button" onClick={() => setOpen(t.id)} className="flex w-full items-center gap-4 px-5 py-4 text-left transition hover:bg-muted/50">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold">{t.subject}</p>
                    <p className="truncate text-xs text-muted-foreground">{t.last_message}</p>
                  </div>
                  <StatusBadge status={t.status} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </GlassCard>
      <NewTicketDialog open={creating} onClose={() => setCreating(false)} onCreated={setOpen} />
      <ThreadDialog id={open} staff={false} onClose={() => setOpen(null)} />
    </div>
  );
}

// ================================================================ partner applications (landing page)
function ApplicationBadge({ status }: { status: ApplicationStatus }) {
  const s = APPLICATION_STATUS[status];
  return <span className={cn("inline-flex h-6 items-center rounded-full px-2.5 text-xs font-bold", s.className)}>{s.label}</span>;
}

function ApplicationDialog({ row, onClose }: { row: PartnerApplication | null; onClose: () => void }) {
  const update = applicationsResource.useUpdate();
  const [status, setStatus] = useState<ApplicationStatus | "">("");
  const [note, setNote] = useState<string | null>(null);
  const close = () => {
    setStatus("");
    setNote(null);
    onClose();
  };
  const value = { status: status || row?.status, note: note ?? row?.staff_note ?? "" };
  return (
    <MotionDialog
      open={Boolean(row)}
      onOpenChange={(o) => !o && close()}
      title={row ? `${row.business_name} — ${APPLICATION_KIND[row.kind]}` : ""}
      description={row ? `Yuborilgan: ${formatDateTime(row.created_at)}` : undefined}
      footer={
        <>
          <Button variant="outline" className="h-11 flex-1" onClick={close}>
            Yopish
          </Button>
          <Button
            className="h-11 flex-1"
            disabled={update.isPending}
            onClick={() =>
              row &&
              update.mutate(
                { id: row.id, values: { status: value.status, staff_note: value.note } },
                { onSuccess: () => (toast.success("Saqlandi"), close()), onError: (e) => toast.error(errorText(e)) },
              )
            }
          >
            <CheckIcon /> Saqlash
          </Button>
        </>
      }
    >
      {row && (
        <div className="flex flex-col gap-4 text-sm">
          <div className="grid gap-3 rounded-2xl bg-muted/60 p-4 sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold text-muted-foreground">Murojaatchi</p>
              <p className="font-semibold">{row.full_name}</p>
            </div>
            <div>
              <p className="text-xs font-semibold text-muted-foreground">Telefon</p>
              <a href={`tel:${row.phone_number}`} className="inline-flex items-center gap-1.5 font-semibold text-cyan-700 hover:underline dark:text-cyan-300">
                <PhoneIcon className="size-3.5" aria-hidden /> {formatPhone(row.phone_number)}
              </a>
            </div>
            <div>
              <p className="text-xs font-semibold text-muted-foreground">Viloyat</p>
              <p className="font-semibold">{row.region_label || "—"}</p>
            </div>
            <div>
              <p className="text-xs font-semibold text-muted-foreground">Ko&apos;rib chiqqan</p>
              <p className="font-semibold">{row.handled_by_name ? `${row.handled_by_name}, ${formatDateTime(row.handled_at)}` : "—"}</p>
            </div>
          </div>
          {row.message && <p className="whitespace-pre-wrap rounded-2xl border border-border p-3">{row.message}</p>}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ap-status">Holat</Label>
            <select
              id="ap-status"
              className="h-11 w-full rounded-xl border border-input bg-white/60 px-3 text-sm outline-none focus-visible:border-ring dark:bg-slate-950/40"
              value={value.status}
              onChange={(e) => setStatus(e.target.value as ApplicationStatus)}
            >
              {(Object.keys(APPLICATION_STATUS) as ApplicationStatus[]).map((k) => (
                <option key={k} value={k}>
                  {APPLICATION_STATUS[k].label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ap-note">Izoh (faqat xodimlar ko&apos;radi)</Label>
            <Textarea id="ap-note" maxLength={1000} value={value.note} onChange={(e) => setNote(e.target.value)} />
          </div>
          <p className="text-xs text-muted-foreground">
            Qabul qilsangiz, hisobni qo&apos;lda oching: {row.kind === "STUDIO" ? "Studiyalar" : "To'yxonalar"} sahifasi → yangi qo&apos;shish.
          </p>
        </div>
      )}
    </MotionDialog>
  );
}

function ApplicationsTab() {
  const list = useListState({ ordering: "-created_at" });
  const { data, error, isPending, refetch } = applicationsResource.useList(list.params);
  const [open, setOpen] = useState<PartnerApplication | null>(null);
  const filters = [
    { key: "kind", label: "Turi", options: (Object.keys(APPLICATION_KIND) as ApplicationKind[]).map((k) => ({ value: k, label: APPLICATION_KIND[k] })) },
    {
      key: "status",
      label: "Holat",
      options: (Object.keys(APPLICATION_STATUS) as ApplicationStatus[]).map((k) => ({ value: k, label: APPLICATION_STATUS[k].label })),
    },
  ];
  return (
    <div className="flex flex-col gap-4">
      <ListToolbar
        search={list.search}
        onSearch={list.setSearch}
        placeholder="Nomi, ism, telefon yoki xabar"
        filters={filters}
        values={list.filters}
        onFilter={list.setFilter}
        ordering={{
          value: list.ordering,
          options: [
            { value: "-created_at", label: "Eng yangilari" },
            { value: "created_at", label: "Eng eskilari" },
          ],
          onChange: list.setOrdering,
        }}
      />
      <GlassCard className="p-0 sm:p-0">
        {isPending ? (
          <div className="p-5">
            <RowsSkeleton />
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.results.length === 0 ? (
          <EmptyState title={list.hasQuery ? "Hech narsa topilmadi" : "Ariza yo'q"} description="Studiya va to'yxonalar marosimgo.uz sahifasidagi «Hamkor bo'lish» formasidan ariza yuboradi." />
        ) : (
          <ul className="divide-y divide-border/70">
            {data.results.map((a) => (
              <li key={a.id}>
                <button type="button" onClick={() => setOpen(a)} className="flex w-full flex-wrap items-center gap-x-5 gap-y-1 px-5 py-4 text-left transition hover:bg-muted/50">
                  {a.kind === "STUDIO" ? <VideoIcon className="size-5 shrink-0 text-cyan-600" aria-hidden /> : <CastleIcon className="size-5 shrink-0 text-amber-600" aria-hidden />}
                  <div className="min-w-48 flex-1">
                    <p className="truncate font-semibold">{a.business_name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {APPLICATION_KIND[a.kind]} · {a.region_label || "viloyat ko'rsatilmagan"}
                    </p>
                  </div>
                  <div className="w-48 min-w-0">
                    <p className="truncate text-sm font-semibold">{a.full_name}</p>
                    <p className="text-xs text-muted-foreground tabular-nums">{formatPhone(a.phone_number)}</p>
                  </div>
                  <div className="w-44 text-sm">
                    <ApplicationBadge status={a.status} />
                    <p className="mt-1 text-xs text-muted-foreground">{formatDateTime(a.created_at)}</p>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </GlassCard>
      {data && data.total_pages > 1 && (
        <Pagination page={data.page} totalPages={data.total_pages} count={data.count} pageSize={data.page_size} onPage={list.setPage} />
      )}
      <ApplicationDialog row={open} onClose={() => setOpen(null)} />
    </div>
  );
}

type Tab = "inbox" | "applications" | "mine";

function SupportContent() {
  const { data: me } = useMe();
  const can = useCan();
  const isSuper = me?.role === "SUPER_ADMIN";
  const inbox = isSuper || can("support.view");
  const mine = me?.role === "ADMIN";
  const [tab, setTab] = useState<Tab>(inbox ? "inbox" : "mine");
  const current: Tab = !inbox ? "mine" : !mine && tab === "mine" ? "inbox" : tab;
  const tabs = [
    ...(inbox
      ? [
          { value: "inbox" as const, label: "Kelgan xatlar", icon: InboxIcon },
          { value: "applications" as const, label: "Hamkorlik arizalari", icon: ClipboardListIcon },
        ]
      : []),
    ...(mine ? [{ value: "mine" as const, label: "Mening xatlarim", icon: UserRoundPenIcon }] : []),
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Yordam"
        crumb={isSuper ? "Barcha yordam xatlari va arizalar: kim, qayerdan, kim javob bergan" : "Yordam xatlari"}
      />
      {tabs.length > 1 && <AnimatedTabs layoutId="support-tab" value={current} onChange={setTab} tabs={tabs} />}
      {current === "inbox" && <InboxTab seesAdmins={isSuper || can("support.monitor")} />}
      {current === "applications" && <ApplicationsTab />}
      {current === "mine" && <MineTab />}
    </div>
  );
}

export default function SupportPage() {
  return (
    <PageTransition>
      <SupportContent />
    </PageTransition>
  );
}
