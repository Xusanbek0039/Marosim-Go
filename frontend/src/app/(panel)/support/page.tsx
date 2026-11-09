"use client";

import { CheckIcon, InboxIcon, MailCheckIcon, MailQuestionIcon, PlusIcon, SendIcon, UserRoundPenIcon } from "lucide-react";
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
  AUTHOR_ROLES,
  myTickets,
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

type Tab = "inbox" | "mine";

function SupportContent() {
  const { data: me } = useMe();
  const can = useCan();
  const isSuper = me?.role === "SUPER_ADMIN";
  const inbox = isSuper || can("support.view");
  const mine = me?.role === "ADMIN";
  const [tab, setTab] = useState<Tab>(inbox ? "inbox" : "mine");
  const current: Tab = !inbox ? "mine" : !mine ? "inbox" : tab;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Yordam"
        crumb={isSuper ? "Barcha yordam xatlari: kim, qayerdan, kim javob bergan" : "Yordam xatlari"}
      />
      {inbox && mine && (
        <AnimatedTabs
          layoutId="support-tab"
          value={current}
          onChange={setTab}
          tabs={[
            { value: "inbox", label: "Kelgan xatlar", icon: InboxIcon },
            { value: "mine", label: "Mening xatlarim", icon: UserRoundPenIcon },
          ]}
        />
      )}
      {current === "inbox" && <InboxTab seesAdmins={isSuper || can("support.monitor")} />}
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
