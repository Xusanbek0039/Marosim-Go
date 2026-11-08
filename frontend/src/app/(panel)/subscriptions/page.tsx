"use client";

import { BanIcon, CheckIcon, CoinsIcon, CrownIcon, HourglassIcon, ListIcon, PlusIcon, ReceiptIcon, SaveIcon, TagIcon, WalletIcon, XIcon } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState, ErrorState, GlassCard, PageHeader, Pagination, RowsSkeleton } from "@/components/common";
import { ListToolbar } from "@/components/common/list-toolbar";
import { RequirePermission } from "@/components/layout/require-permission";
import { MotionDialog } from "@/components/motion/motion-dialog";
import { PageTransition } from "@/components/motion/page-transition";
import { AnimatedTabs } from "@/components/monitoring/primitives";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useCan } from "@/features/auth/hooks";
import {
  type AdminSubscription,
  formatMoney,
  type Payment,
  PAYMENT_METHODS,
  type PaymentMethod,
  type Plan,
  STATE,
  type SubscriptionState,
  subscriptionsResource,
  useDecision,
  useGrant,
  usePlans,
  useSettings,
  useSummary,
  useUpdatePlan,
  useUpdateSettings,
} from "@/features/subscriptions/api";
import { useListState } from "@/features/use-list-state";
import { api, ApiError } from "@/lib/api/client";
import type { Paginated, UserSummary } from "@/lib/api/types";
import { formatDate, formatDateTime, formatPhone } from "@/lib/format";
import { cn } from "@/lib/utils";

const FILTERS = [
  {
    key: "state",
    label: "Holat",
    options: (Object.keys(STATE) as SubscriptionState[]).map((k) => ({ value: k, label: STATE[k].label })),
  },
];
const ORDERING = [
  { value: "-created_at", label: "Eng yangilari" },
  { value: "ends_at", label: "Tugashi yaqin" },
  { value: "-price", label: "Narxi yuqori" },
];
const nativeSelect =
  "h-11 w-full rounded-xl border border-input bg-white/60 px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-slate-950/40";

const errorText = (e: unknown, fallback: string) =>
  e instanceof ApiError ? (Object.values(e.fieldErrors)[0] as string | undefined) ?? e.message : fallback;

function StateBadge({ state }: { state: SubscriptionState }) {
  return <span className={cn("inline-flex h-6 items-center rounded-full px-2.5 text-xs font-bold", STATE[state].className)}>{STATE[state].label}</span>;
}

// ================================================================ summary
function SummaryCards() {
  const { data } = useSummary();
  const cards = [
    { label: "To'lov kutayotgan", value: data ? String(data.pending) : "—", icon: HourglassIcon, tone: "from-amber-500 to-orange-500" },
    { label: "Faol obunachilar", value: data ? String(data.active) : "—", icon: CrownIcon, tone: "from-blue-600 to-cyan-500" },
    { label: "Shu oy tushum", value: data ? formatMoney(data.revenue_month) : "—", icon: CoinsIcon, tone: "from-emerald-500 to-teal-500" },
    { label: "Jami tushum", value: data ? formatMoney(data.revenue_total) : "—", icon: WalletIcon, tone: "from-violet-500 to-fuchsia-500" },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((c) => (
        <GlassCard key={c.label} className="flex items-center gap-4 p-4 sm:p-5">
          <span className={cn("flex size-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br text-white", c.tone)}>
            <c.icon className="size-5" aria-hidden />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-muted-foreground">{c.label}</p>
            <p className="truncate text-lg font-extrabold tabular-nums">{c.value}</p>
          </div>
        </GlassCard>
      ))}
    </div>
  );
}

// =========================================================== payment form
function PaymentFields({ value, onChange, price }: { value: Payment; onChange: (v: Payment) => void; price?: string }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="p-method">To&apos;lov usuli</Label>
        <select id="p-method" className={nativeSelect} value={value.payment_method ?? ""} onChange={(e) => onChange({ ...value, payment_method: e.target.value as PaymentMethod })}>
          <option value="">Tanlanmagan</option>
          {Object.entries(PAYMENT_METHODS).map(([k, l]) => (
            <option key={k} value={k}>
              {l}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="p-amount">To&apos;langan summa (so&apos;m)</Label>
        <Input
          id="p-amount"
          inputMode="numeric"
          placeholder={price ? String(Math.round(Number(price))) : ""}
          value={value.paid_amount ?? ""}
          onChange={(e) => onChange({ ...value, paid_amount: e.target.value.replace(/[^\d]/g, "") || null })}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="p-ref">Chek / tranzaksiya raqami</Label>
        <Input id="p-ref" maxLength={120} value={value.payment_reference ?? ""} onChange={(e) => onChange({ ...value, payment_reference: e.target.value })} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="p-note">Izoh (mijozga ko&apos;rinadi)</Label>
        <Input id="p-note" maxLength={500} value={value.admin_note ?? ""} onChange={(e) => onChange({ ...value, admin_note: e.target.value })} />
      </div>
    </div>
  );
}

type Dialog = { kind: "approve" | "reject" | "cancel"; sub: AdminSubscription } | null;

function DecisionDialog({ dialog, onClose }: { dialog: Dialog; onClose: () => void }) {
  const decide = useDecision();
  const [payment, setPayment] = useState<Payment>({});
  const sub = dialog?.sub;
  const titles = { approve: "To'lovni tasdiqlash", reject: "So'rovni rad etish", cancel: "Obunani bekor qilish" };
  const submit = () => {
    if (!dialog) return;
    const body: Payment = dialog.kind === "approve" ? payment : { admin_note: payment.admin_note ?? "" };
    decide.mutate(
      { id: dialog.sub.id, action: dialog.kind, body },
      {
        onSuccess: () => {
          toast.success(dialog.kind === "approve" ? "Obuna yoqildi" : dialog.kind === "reject" ? "Rad etildi" : "Bekor qilindi");
          setPayment({});
          onClose();
        },
        onError: (e) => toast.error(errorText(e, "Bajarilmadi")),
      },
    );
  };
  return (
    <MotionDialog
      open={Boolean(dialog)}
      onOpenChange={(o) => !o && onClose()}
      title={dialog ? titles[dialog.kind] : ""}
      description={sub ? `${sub.user.full_name} · ${formatPhone(sub.user.phone_number)} · ${sub.plan.name} — ${formatMoney(sub.price)}` : undefined}
      footer={
        <>
          <Button variant="outline" className="h-11 flex-1" onClick={onClose}>
            Yopish
          </Button>
          <Button
            className={cn("h-11 flex-1", dialog?.kind !== "approve" && "bg-red-600 text-white hover:bg-red-700")}
            onClick={submit}
            disabled={decide.isPending}
          >
            {dialog?.kind === "approve" ? <CheckIcon /> : <XIcon />} {dialog ? titles[dialog.kind] : ""}
          </Button>
        </>
      }
    >
      {sub && (
        <div className="flex flex-col gap-4">
          {sub.user_note && (
            <p className="rounded-2xl bg-muted/60 p-3 text-sm">
              <span className="font-semibold">Mijoz izohi:</span> {sub.user_note}
            </p>
          )}
          {dialog?.kind === "approve" ? (
            <>
              <PaymentFields value={payment} onChange={setPayment} price={sub.price} />
              <p className="text-xs text-muted-foreground">
                Summa bo&apos;sh qolsa tarif narxi ({formatMoney(sub.price)}) yoziladi. Mijozda faol obuna bo&apos;lsa, yangi davr u tugagan kundan boshlanadi.
              </p>
            </>
          ) : (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="d-note">Sabab (mijozga ko&apos;rinadi)</Label>
              <Textarea id="d-note" maxLength={500} value={payment.admin_note ?? ""} onChange={(e) => setPayment({ admin_note: e.target.value })} />
              {dialog?.kind === "cancel" && <p className="text-xs text-muted-foreground">Obuna darhol to&apos;xtaydi: videolar yana logo bilan ko&apos;rinadi.</p>}
            </div>
          )}
        </div>
      )}
    </MotionDialog>
  );
}

function GrantDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const plans = usePlans(open);
  const grant = useGrant();
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [user, setUser] = useState<UserSummary | null>(null);
  const [planId, setPlanId] = useState("");
  const [payment, setPayment] = useState<Payment>({ payment_method: "CASH" });

  const search = async () => {
    try {
      const res = await api.get<Paginated<UserSummary>>("/users/", { search: query.trim(), role: "USER", page_size: 8 });
      setUsers(res.results);
      if (!res.results.length) toast.message("Foydalanuvchi topilmadi");
    } catch (e) {
      toast.error(errorText(e, "Qidirib bo'lmadi (users.view ruxsati kerak)"));
    }
  };
  const plan = plans.data?.find((p) => p.id === planId);

  return (
    <MotionDialog
      open={open}
      onOpenChange={(o) => !o && onClose()}
      size="lg"
      title="Obuna berish"
      description="Mijoz to'lovni naqd yoki boshqa yo'l bilan qilgan bo'lsa — to'lovni qayd etib, obunani darhol yoqing."
      footer={
        <>
          <Button variant="outline" className="h-11 flex-1" onClick={onClose}>
            Bekor qilish
          </Button>
          <Button
            className="h-11 flex-1"
            disabled={!user || !planId || grant.isPending}
            onClick={() =>
              grant.mutate(
                { user_id: user!.id, plan: planId, ...payment },
                {
                  onSuccess: () => {
                    toast.success("Obuna berildi");
                    setUser(null);
                    setUsers([]);
                    setQuery("");
                    onClose();
                  },
                  onError: (e) => toast.error(errorText(e, "Berilmadi")),
                },
              )
            }
          >
            <CrownIcon /> Obuna berish
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <Label htmlFor="g-q">Mijoz</Label>
          {user ? (
            <div className="flex items-center justify-between gap-3 rounded-2xl bg-muted/60 px-4 py-3">
              <div>
                <p className="font-semibold">{user.full_name || "—"}</p>
                <p className="text-sm text-muted-foreground tabular-nums">{formatPhone(user.phone_number)}</p>
              </div>
              <Button size="sm" variant="ghost" onClick={() => setUser(null)}>
                O&apos;zgartirish
              </Button>
            </div>
          ) : (
            <>
              <div className="flex gap-2">
                <Input id="g-q" placeholder="Telefon yoki ism" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), search())} />
                <Button variant="outline" className="h-11" onClick={search} disabled={query.trim().length < 2}>
                  Qidirish
                </Button>
              </div>
              {users.length > 0 && (
                <ul className="flex flex-col gap-1">
                  {users.map((u) => (
                    <li key={u.id}>
                      <button type="button" onClick={() => setUser(u)} className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm hover:bg-muted">
                        <span className="font-semibold">{u.full_name || "—"}</span>
                        <span className="text-muted-foreground tabular-nums">{formatPhone(u.phone_number)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
        <div className="flex flex-col gap-2">
          <Label>Tarif</Label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {(plans.data ?? []).filter((p) => p.is_active).map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setPlanId(p.id)}
                className={cn("rounded-2xl border p-3 text-left transition", planId === p.id ? "border-cyan-500 bg-cyan-500/10" : "border-border hover:bg-muted/60")}
              >
                <p className="text-sm font-bold">{p.name}</p>
                <p className="text-xs text-muted-foreground tabular-nums">{formatMoney(p.price)}</p>
              </button>
            ))}
          </div>
        </div>
        <PaymentFields value={payment} onChange={setPayment} price={plan?.price} />
      </div>
    </MotionDialog>
  );
}

// =========================================================== list tab
function SubscriptionsTab() {
  const can = useCan();
  const list = useListState({ ordering: "-created_at" });
  const { data, error, isPending, refetch } = subscriptionsResource.useList(list.params);
  const [dialog, setDialog] = useState<Dialog>(null);
  const canDecide = can("subscriptions.update");

  return (
    <div className="flex flex-col gap-4">
      <ListToolbar
        search={list.search}
        onSearch={list.setSearch}
        placeholder="Mijoz ismi, telefoni yoki chek raqami"
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
          <EmptyState title={list.hasQuery ? "Hech narsa topilmadi" : "Hali obuna yo'q"} description="Mijozlar user panelidagi 'Obuna' bo'limidan so'rov yuboradi." />
        ) : (
          <ul className="divide-y divide-border/70">
            {data.results.map((s) => (
              <motion.li key={s.id} layout className="flex flex-wrap items-center gap-x-5 gap-y-2 px-5 py-4">
                <div className="min-w-48 flex-1">
                  <p className="font-semibold">{s.user.full_name || "—"}</p>
                  <p className="text-sm text-muted-foreground tabular-nums">{formatPhone(s.user.phone_number)}</p>
                </div>
                <div className="w-36">
                  <p className="font-semibold">{s.plan.name}</p>
                  <p className="text-xs text-muted-foreground">{s.max_viewers} kishi</p>
                </div>
                <div className="w-36 tabular-nums">
                  <p className="font-semibold">{formatMoney(s.paid_amount ?? s.price)}</p>
                  <p className="text-xs text-muted-foreground">{s.payment_method ? PAYMENT_METHODS[s.payment_method] : s.state === "PENDING" ? "to'lanmagan" : "—"}</p>
                </div>
                <div className="w-44 text-sm">
                  <StateBadge state={s.state} />
                  <p className="mt-1 text-xs text-muted-foreground">
                    {s.starts_at ? `${formatDate(s.starts_at)} — ${formatDate(s.ends_at)}` : `so'rov: ${formatDateTime(s.created_at)}`}
                  </p>
                </div>
                <div className="ml-auto flex gap-2">
                  {canDecide && s.state === "PENDING" && (
                    <>
                      <Button size="sm" variant="ghost" onClick={() => setDialog({ kind: "reject", sub: s })}>
                        <XIcon /> Rad etish
                      </Button>
                      <Button size="sm" onClick={() => setDialog({ kind: "approve", sub: s })}>
                        <CheckIcon /> Tasdiqlash
                      </Button>
                    </>
                  )}
                  {canDecide && (s.state === "ACTIVE" || s.state === "SCHEDULED") && (
                    <Button size="sm" variant="destructive" onClick={() => setDialog({ kind: "cancel", sub: s })}>
                      <BanIcon /> Bekor qilish
                    </Button>
                  )}
                </div>
                {(s.user_note || s.payment_reference || s.admin_note) && (
                  <p className="w-full text-xs text-muted-foreground">
                    {[s.user_note && `Mijoz: ${s.user_note}`, s.payment_reference && `Chek: ${s.payment_reference}`, s.admin_note && `Admin: ${s.admin_note}`]
                      .filter(Boolean)
                      .join(" · ")}
                    {s.decided_by && ` · ${s.decided_by.full_name}`}
                  </p>
                )}
              </motion.li>
            ))}
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

// ============================================================== plans tab
function PlanRow({ plan, editable }: { plan: Plan; editable: boolean }) {
  const update = useUpdatePlan();
  const [form, setForm] = useState({ name: plan.name, price: String(Math.round(Number(plan.price))), max_viewers: String(plan.max_viewers), duration_months: String(plan.duration_months) });
  const dirty =
    form.name !== plan.name ||
    Number(form.price) !== Math.round(Number(plan.price)) ||
    Number(form.max_viewers) !== plan.max_viewers ||
    Number(form.duration_months) !== plan.duration_months;
  const save = (body: Partial<Plan>) =>
    update.mutate({ id: plan.id, ...body }, { onSuccess: () => toast.success("Saqlandi"), onError: (e) => toast.error(errorText(e, "Saqlanmadi")) });
  const num = (v: string) => v.replace(/[^\d]/g, "");
  return (
    <li className={cn("grid items-end gap-3 px-5 py-4 sm:grid-cols-[1fr_1fr_0.7fr_0.7fr_auto]", !plan.is_active && "opacity-60")}>
      <div className="flex flex-col gap-1.5">
        <Label className="text-xs">Nomi ({plan.code})</Label>
        <Input disabled={!editable} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label className="text-xs">Narx (so&apos;m)</Label>
        <Input disabled={!editable} inputMode="numeric" value={form.price} onChange={(e) => setForm({ ...form, price: num(e.target.value) })} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label className="text-xs">Muddat (oy)</Label>
        <Input disabled={!editable} inputMode="numeric" value={form.duration_months} onChange={(e) => setForm({ ...form, duration_months: num(e.target.value) })} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label className="text-xs">Ruxsat (kishi)</Label>
        <Input disabled={!editable} inputMode="numeric" value={form.max_viewers} onChange={(e) => setForm({ ...form, max_viewers: num(e.target.value) })} />
      </div>
      <div className="flex h-11 items-center gap-3">
        {editable && (
          <>
            <label className="flex items-center gap-2 text-xs font-semibold">
              <Switch checked={plan.is_active} onCheckedChange={(on) => save({ is_active: on })} /> Sotuvda
            </label>
            <Button
              size="sm"
              disabled={!dirty || update.isPending}
              onClick={() =>
                save({ name: form.name.trim(), price: form.price, max_viewers: Number(form.max_viewers), duration_months: Number(form.duration_months) })
              }
            >
              <SaveIcon /> Saqlash
            </Button>
          </>
        )}
      </div>
    </li>
  );
}

function PlansTab() {
  const can = useCan();
  const plans = usePlans();
  const editable = can("subscriptions.plans");
  return (
    <GlassCard className="flex flex-col gap-0 p-0 sm:p-0">
      <div className="px-5 pt-5">
        <h3 className="text-base font-bold">Tariflar</h3>
        <p className="text-sm text-muted-foreground">
          Yangi narx faqat bundan keyingi so&apos;rovlarga ta&apos;sir qiladi; sotilgan obunalar o&apos;z narxi va limitini saqlaydi.
          {!editable && " Tahrirlash uchun `subscriptions.plans` ruxsati kerak."}
        </p>
      </div>
      {plans.isPending ? (
        <div className="p-5">
          <RowsSkeleton rows={4} />
        </div>
      ) : plans.error ? (
        <ErrorState error={plans.error} onRetry={() => plans.refetch()} />
      ) : (
        <ul className="divide-y divide-border/70">
          {plans.data.map((p) => (
            <PlanRow key={`${p.id}-${p.price}-${p.name}-${p.max_viewers}-${p.duration_months}`} plan={p} editable={editable} />
          ))}
        </ul>
      )}
    </GlassCard>
  );
}

// ============================================================ settings tab
function PaymentInfoTab() {
  const can = useCan();
  const settings = useSettings();
  const update = useUpdateSettings();
  const [draft, setDraft] = useState<string | null>(null);
  const value = draft ?? settings.data?.payment_instructions ?? "";
  const editable = can("subscriptions.plans");
  return (
    <GlassCard className="flex flex-col gap-4">
      <div>
        <h3 className="text-base font-bold">To&apos;lov ma&apos;lumotlari</h3>
        <p className="text-sm text-muted-foreground">Mijoz obuna tanlaganda shu matnni ko&apos;radi: karta raqami, qabul qiluvchi, telefon va h.k.</p>
      </div>
      <Textarea
        rows={7}
        maxLength={2000}
        disabled={!editable}
        value={value}
        onChange={(e) => setDraft(e.target.value)}
        placeholder={"Karta: 8600 1234 5678 9012\nQabul qiluvchi: Ali Valiyev\nClick / Payme: +998 90 123 45 67\nTo'lovdan so'ng chek raqamini izohga yozing."}
      />
      {editable && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">{settings.data?.updated_at && `Oxirgi o'zgarish: ${formatDateTime(settings.data.updated_at)}`}</p>
          <Button
            disabled={draft === null || update.isPending}
            onClick={() =>
              update.mutate(
                { payment_instructions: value },
                { onSuccess: () => (setDraft(null), toast.success("Saqlandi")), onError: (e) => toast.error(errorText(e, "Saqlanmadi")) },
              )
            }
          >
            <SaveIcon /> Saqlash
          </Button>
        </div>
      )}
    </GlassCard>
  );
}

// ================================================================== page
type Tab = "list" | "plans" | "payment";

function SubscriptionsContent() {
  const can = useCan();
  const [tab, setTab] = useState<Tab>("list");
  const [grantOpen, setGrantOpen] = useState(false);
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Obunalar"
        crumb="To'lovlar qo'lda tasdiqlanadi"
        actions={
          can("subscriptions.create") && (
            <Button onClick={() => setGrantOpen(true)}>
              <PlusIcon /> Obuna berish
            </Button>
          )
        }
      />
      <SummaryCards />
      <AnimatedTabs
        layoutId="subscriptions-tab"
        value={tab}
        onChange={setTab}
        tabs={[
          { value: "list", label: "So'rovlar va to'lovlar", icon: ListIcon },
          { value: "plans", label: "Tariflar", icon: TagIcon },
          { value: "payment", label: "To'lov ma'lumotlari", icon: ReceiptIcon },
        ]}
      />
      {tab === "list" && <SubscriptionsTab />}
      {tab === "plans" && <PlansTab />}
      {tab === "payment" && <PaymentInfoTab />}
      <GrantDialog open={grantOpen} onClose={() => setGrantOpen(false)} />
    </div>
  );
}

export default function SubscriptionsPage() {
  return (
    <RequirePermission requires="subscriptions.view">
      <PageTransition>
        <SubscriptionsContent />
      </PageTransition>
    </RequirePermission>
  );
}
