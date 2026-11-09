"use client";

import { PaidBadge } from "@/components/paid-badge";

import { CheckIcon, CrownIcon, DownloadIcon, ImageOffIcon, UsersIcon, XIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageTitle } from "@/components/shell";
import { Badge, Button, Card, cn, ErrorState, Field, Skeleton, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatEventDate, formatMoney } from "@/lib/format";
import {
  type MySubscription,
  type Plan,
  STATE,
  useCancelRequest,
  useMySubscriptions,
  useRequestSubscription,
  useSubscriptionStatus,
} from "@/lib/subscriptions";

const day = (iso: string | null) => (iso ? formatEventDate(iso.slice(0, 10)) : "—");

export default function SubscriptionPage() {
  const status = useSubscriptionStatus();
  const history = useMySubscriptions();
  const [selected, setSelected] = useState<string | null>(null);

  if (status.isPending) return <Skeleton className="h-96 rounded-3xl" />;
  if (status.error)
    return (
      <Card>
        <ErrorState error={status.error} onRetry={() => status.refetch()} />
      </Card>
    );
  const s = status.data;
  const plan = s.plans.find((p) => p.id === selected) ?? null;
  const perMonth = (p: Plan) => Number(p.price) / p.duration_months;
  const base = s.plans.length ? Math.max(...s.plans.map(perMonth)) : 0;

  return (
    <>
      <PageTitle title="Obuna" subtitle="Logosiz ko'rish, yuklab olish va ko'proq odamga ulashish" />

      {/* current state */}
      <Card className="flex flex-wrap items-center gap-4">
        <span className={cn("flex size-12 items-center justify-center rounded-2xl text-white", s.clean_access ? "brand-gradient" : "bg-slate-500/60")}>
          <CrownIcon className="size-6" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          {s.active ? (
            <>
              <p className="text-lg font-bold">
                {s.active.plan.name} obuna faol <PaidBadge verified={s.is_verified} /> <Badge tone="success">Faol</Badge>
              </p>
              <p className="text-sm text-muted-foreground">
                {day(s.active.ends_at)} gacha
                {s.paid_until && s.paid_until !== s.active.ends_at && <> · navbatdagisi bilan {day(s.paid_until)} gacha</>} · {s.viewer_limit} kishiga ulashish
              </p>
            </>
          ) : (
            <>
              <p className="text-lg font-bold">Obuna yo&apos;q</p>
              <p className="text-sm text-muted-foreground">
                Video va rasmlar MarosimGo logosi bilan ko&apos;rsatiladi, yuklab olib bo&apos;lmaydi, {s.viewer_limit} kishiga ulashish mumkin.
              </p>
            </>
          )}
        </div>
      </Card>

      {s.pending && <PendingCard sub={s.pending} instructions={s.payment_instructions} />}

      {/* plans */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {s.plans.map((p) => {
          const saving = base ? Math.round((1 - perMonth(p) / base) * 100) : 0;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => setSelected(p.id)}
              disabled={Boolean(s.pending) || !s.purchase_enabled}
              className={cn(
                "glass relative flex flex-col gap-3 rounded-3xl p-5 text-left transition hover:-translate-y-0.5 disabled:pointer-events-none disabled:opacity-60",
                selected === p.id && "ring-2 ring-brand",
              )}
            >
              {saving >= 5 && <span className="absolute top-3 right-3 rounded-full bg-emerald-600 px-2 py-0.5 text-[11px] font-bold text-white">−{saving}%</span>}
              <p className="text-base font-bold">{p.name}</p>
              <p className="text-2xl font-extrabold tracking-tight">{formatMoney(p.price)}</p>
              <p className="text-xs text-muted-foreground">oyiga ≈ {formatMoney(perMonth(p))}</p>
              <ul className="flex flex-col gap-1.5 text-sm">
                <Perk icon={CheckIcon}>Profil galichkasi</Perk>
                <Perk icon={ImageOffIcon}>Logosiz video va rasmlar</Perk>
                <Perk icon={DownloadIcon}>Yuklab olish</Perk>
                <Perk icon={UsersIcon}>{p.max_viewers} kishiga ruxsat</Perk>
              </ul>
            </button>
          );
        })}
      </div>

      {!s.purchase_enabled && <Card>Sotib olish vaqtincha o&apos;chirilgan.</Card>}
      {plan && !s.pending && s.purchase_enabled && <RequestForm plan={plan} instructions={s.payment_instructions} onDone={() => setSelected(null)} />}

      <Card className="flex flex-col gap-2 text-sm text-muted-foreground">
        <p>
          • Obuna faqat siz uchun: siz ruxsat bergan odamlar videoni <b>logo bilan ko&apos;radi va yuklab ololmaydi</b>.
        </p>
        <p>• Obuna faol bo&apos;lganda yangi muddat avvalgisi tugagan kundan boshlanadi — to&apos;langan kunlar yo&apos;qolmaydi.</p>
        <p>• Muddat tugagach videolar yana logo bilan ko&apos;rsatiladi.</p>
      </Card>

      {history.data && history.data.length > 0 && (
        <Card className="flex flex-col gap-3">
          <h2 className="text-base font-bold">Tarix</h2>
          <ul className="flex flex-col divide-y divide-border text-sm">
            {history.data.map((h) => (
              <li key={h.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2.5">
                <span className="w-20 font-semibold">{h.plan.name}</span>
                <span className="w-32">{formatMoney(h.paid_amount ?? h.price)}</span>
                <Badge tone={STATE[h.state].tone}>{STATE[h.state].label}</Badge>
                <span className="text-muted-foreground">
                  {h.starts_at ? `${day(h.starts_at)} — ${day(h.ends_at)}` : `so'rov: ${day(h.created_at)}`}
                </span>
                {h.admin_note && <span className="w-full text-xs text-muted-foreground">Izoh: {h.admin_note}</span>}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}

function Perk({ icon: Icon, children }: { icon: typeof CheckIcon; children: React.ReactNode }) {
  return (
    <li className="flex items-center gap-2">
      <Icon className="size-4 shrink-0 text-cyan-600 dark:text-cyan-300" aria-hidden /> {children}
    </li>
  );
}

function Instructions({ text }: { text: string }) {
  return text ? (
    <div className="rounded-2xl bg-muted p-4 text-sm whitespace-pre-line">{text}</div>
  ) : (
    <p className="text-sm text-muted-foreground">To&apos;lov ma&apos;lumotlari uchun administrator bilan bog&apos;laning.</p>
  );
}

function RequestForm({ plan, instructions, onDone }: { plan: Plan; instructions: string; onDone: () => void }) {
  const request = useRequestSubscription();
  const [note, setNote] = useState("");
  return (
    <Card className="flex flex-col gap-4">
      <h2 className="text-lg font-bold">
        {plan.name} — {formatMoney(plan.price)}
      </h2>
      <div className="flex flex-col gap-2">
        <p className="text-sm font-semibold">1. To&apos;lovni amalga oshiring</p>
        <Instructions text={instructions} />
      </div>
      <Field label="2. To'lov haqida yozing (ixtiyoriy)" htmlFor="sub-note" hint="Masalan: qaysi karta yoki ilova orqali, chek raqami">
        <Textarea id="sub-note" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Click orqali to'ladim, chek №123456" />
      </Field>
      <p className="text-xs text-muted-foreground">So&apos;rovdan keyin administrator to&apos;lovni tekshirib obunani yoqadi.</p>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onDone}>
          Bekor qilish
        </Button>
        <Button
          loading={request.isPending}
          onClick={() =>
            request.mutate(
              { plan: plan.id, user_note: note.trim() },
              {
                onSuccess: () => {
                  toast.success("So'rov yuborildi. To'lov tasdiqlangach obuna yoqiladi.");
                  onDone();
                },
                onError: (e) => toast.error(e instanceof ApiError ? Object.values(e.fieldErrors)[0] || e.message : "Yuborilmadi"),
              },
            )
          }
        >
          <CheckIcon /> To&apos;ladim — so&apos;rov yuborish
        </Button>
      </div>
    </Card>
  );
}

function PendingCard({ sub, instructions }: { sub: MySubscription; instructions: string }) {
  const cancel = useCancelRequest();
  return (
    <Card className="flex flex-col gap-3 border-amber-400/40">
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-bold">
          {sub.plan.name} — {formatMoney(sub.price)}
        </p>
        <Badge tone="warning">To&apos;lov tasdig&apos;i kutilmoqda</Badge>
      </div>
      <p className="text-sm text-muted-foreground">
        So&apos;rov {day(sub.created_at)} kuni yuborilgan. Administrator to&apos;lovni tasdiqlagach obuna avtomatik yoqiladi.
      </p>
      <Instructions text={instructions} />
      <div>
        <Button
          size="sm"
          variant="ghost"
          loading={cancel.isPending}
          onClick={() => cancel.mutate(sub.id, { onSuccess: () => toast.success("So'rov bekor qilindi") })}
        >
          <XIcon /> So&apos;rovni bekor qilish
        </Button>
      </div>
    </Card>
  );
}
