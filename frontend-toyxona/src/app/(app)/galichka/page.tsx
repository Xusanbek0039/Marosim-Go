"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { PageTitle } from "@/components/shell";
import { PaidBadge } from "@/components/paid-badge";
import { Badge, Button, Card, ErrorState, Field, Skeleton, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { formatMoney, formatEventDate } from "@/lib/format";

type Target = { id: string; name: string; kind: "studio" | "venue" };
type Purchase = { id: string; plan: { name: string }; state: string; ends_at: string | null; admin_note: string; price: string; studio: string | null; venue: string | null };
type Status = { is_verified: boolean; purchase_enabled: boolean; active: Purchase | null; pending: Purchase | null; paid_until: string | null; payment_instructions: string; plans: { id: string; name: string; price: string; duration_months: number }[] };
const stateLabels: Record<string, string> = { PENDING: "To'lov kutilmoqda", ACTIVE: "Faol", SCHEDULED: "Navbatda", EXPIRED: "Muddati tugagan", REJECTED: "Rad etilgan", CANCELLED: "Bekor qilingan" };

function PurchasePanel({ target }: { target: Target }) {
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const [planId, setPlanId] = useState("");
  const key = ["badge-status", target.id];
  const status = useQuery({ queryKey: key, queryFn: () => api.get<Status>("/me/subscriptions/status/", { [target.kind]: target.id }), refetchInterval: 60_000 });
  const history = useQuery({ queryKey: ["badge-history"], queryFn: () => api.get<Purchase[]>("/me/subscriptions/") });
  const refresh = () => { qc.invalidateQueries({ queryKey: key }); qc.invalidateQueries({ queryKey: ["badge-history"] }); qc.invalidateQueries({ queryKey: ["studio"] }); qc.invalidateQueries({ queryKey: ["venues"] }); };
  const buy = useMutation({
    mutationFn: () => api.post("/me/subscriptions/", { plan: planId, [target.kind]: target.id, user_note: note.trim() }),
    onSuccess: () => { refresh(); setPlanId(""); setNote(""); toast.success("So'rov yuborildi. To'lov tekshirilgach galichka yoqiladi."); },
    onError: (e) => toast.error(e.message),
  });
  const cancel = useMutation({ mutationFn: (id: string) => api.post(`/me/subscriptions/${id}/cancel/`), onSuccess: refresh, onError: (e) => toast.error(e.message) });
  if (status.isPending) return <Skeleton className="h-56 rounded-3xl" />;
  if (status.error) return <ErrorState error={status.error} onRetry={() => status.refetch()} />;
  const s = status.data;
  return <>
    <Card className="flex flex-col gap-3">
      <h2 className="flex items-center gap-2 text-lg font-bold">{target.name} <PaidBadge verified={s.is_verified} /></h2>
      <p className="text-sm text-muted-foreground">{s.active ? `Galichka ${formatEventDate(s.active.ends_at!.slice(0, 10))} gacha faol.` : "Galichka hali faol emas."}</p>
      {s.paid_until && s.active && s.paid_until !== s.active.ends_at && <p className="text-sm">Keyingi davrlar bilan: {formatEventDate(s.paid_until.slice(0, 10))} gacha.</p>}
      <p className="text-xs text-muted-foreground">Galichka — faol pulli obuna belgisi. Faqat tanlangan biznesga tegishli; muddat tugaganda avtomatik yo&apos;qoladi.</p>
    </Card>
    {s.pending ? <Card className="flex flex-col gap-3">
      <Badge tone="warning">To&apos;lov tasdig&apos;i kutilmoqda</Badge>
      <p>{s.pending.plan.name} · {formatMoney(s.pending.price)}</p>
      <p className="text-sm whitespace-pre-line">{s.payment_instructions || "To'lov ma'lumotlari uchun administratorga murojaat qiling."}</p>
      <Button variant="ghost" loading={cancel.isPending} onClick={() => cancel.mutate(s.pending!.id)}>So&apos;rovni bekor qilish</Button>
    </Card> : <Card className="flex flex-col gap-4">
      <h2 className="text-lg font-bold">Galichka sotib olish</h2>
      {!s.purchase_enabled ? <p>Sotib olish vaqtincha o&apos;chirilgan.</p> : s.plans.length === 0 ? <p>Hozircha sotuvda tarif yo&apos;q.</p> : <>
        <div className="grid gap-3 sm:grid-cols-2">{s.plans.map((p) => <button key={p.id} type="button" aria-pressed={planId === p.id}
          className={`rounded-2xl border p-4 text-left ${planId === p.id ? "border-cyan-500 ring-2 ring-cyan-500" : "border-border"}`} onClick={() => setPlanId(p.id)}>
          <span className="block font-bold">{p.name}</span><span className="text-sm">{formatMoney(p.price)} · {p.duration_months} oy</span>
        </button>)}</div>
        {planId && <>
          <p className="rounded-2xl bg-muted p-4 text-sm whitespace-pre-line">{s.payment_instructions || "To'lov ma'lumotlari uchun administratorga murojaat qiling."}</p>
          <Field label="To'lov haqida izoh" htmlFor="payment-note"><Textarea id="payment-note" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} placeholder="To'lov usuli va chek raqami" /></Field>
          <Button loading={buy.isPending} onClick={() => buy.mutate()}>To&apos;ladim — so&apos;rov yuborish</Button>
        </>}
      </>}
    </Card>}
    {history.error && <ErrorState error={history.error} onRetry={() => history.refetch()} />}
    {history.data && <Card className="flex flex-col gap-3"><h2 className="font-bold">Xaridlar tarixi</h2>{history.data.filter((p) => p[target.kind] === target.id).map((p) => <div key={p.id} className="border-b border-border py-2 text-sm"><b>{p.plan.name}</b> · {stateLabels[p.state] ?? p.state} · {formatMoney(p.price)}{p.admin_note && <p>{p.admin_note}</p>}</div>)}</Card>}
  </>;
}

export default function BadgePage() {
  const targets = useQuery({ queryKey: ["badge-targets"], queryFn: () => api.get<Target[]>("/me/subscriptions/targets/") });
  const [selected, setSelected] = useState("");
  if (targets.isPending) return <Skeleton className="h-56 rounded-3xl" />;
  if (targets.error) return <ErrorState error={targets.error} onRetry={() => targets.refetch()} />;
  const target = targets.data.find((t) => t.id === selected) ?? targets.data[0];
  return <>
    <PageTitle title="Galichka" subtitle="Biznesingiz uchun pulli obuna belgisi" />
    {target ? <>
      <label className="flex flex-col gap-2 text-sm font-semibold">Biznesni tanlang
        <select className="rounded-xl border border-border bg-background p-3" value={target.id} onChange={(e) => setSelected(e.target.value)}>{targets.data.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
      </label>
      <PurchasePanel key={target.id} target={target} />
    </> : <Card>Galichkani faqat faol biznes egasi sotib olishi mumkin.</Card>}
  </>;
}
