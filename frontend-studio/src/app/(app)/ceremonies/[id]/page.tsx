"use client";

import { ArrowLeftIcon, CalendarDaysIcon, PencilIcon, PhoneIcon, SendIcon, ShieldCheckIcon, UserMinusIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Badge, Button, Card, EmptyState, ErrorState, Field, Input, Modal, Select, Skeleton, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { ACCESS_LABELS, formatDateTime, formatEventDate, formatPhone, PARTICIPANT_LABELS, STATUS_LABELS, STATUS_TONE } from "@/lib/format";
import { STUDIO_TRANSITIONS, useCeremony, useInvite, useParticipants, useRevoke, useUpdateCeremony } from "@/lib/studio";
import type { AccessStatus, Ceremony, Participant, ParticipantType } from "@/lib/types";

const ACCESS_TONE: Record<AccessStatus, "warning" | "success" | "neutral" | "danger"> = {
  INVITED: "warning",
  ACTIVE: "success",
  DECLINED: "neutral",
  REVOKED: "danger",
};

const STATUS_ACTION: Record<string, string> = { READY: "Tayyor deb belgilash", DRAFT: "Qoralamaga qaytarish", ARCHIVED: "Arxivlash" };

function EditModal({ ceremony, open, onClose }: { ceremony: Ceremony; open: boolean; onClose: () => void }) {
  const update = useUpdateCeremony(ceremony.id);
  const [values, setValues] = useState({ title: ceremony.title, event_date: ceremony.event_date, description: ceremony.description });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const set = (key: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));
  return (
    <Modal open={open} onClose={onClose} title="Marosimni tahrirlash">
      <form
        noValidate
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          update.mutate(values, {
            onSuccess: () => {
              toast.success("Saqlandi");
              onClose();
            },
            onError: (err) => {
              if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors);
              else toast.error(err instanceof ApiError ? err.message : "Saqlab bo'lmadi");
            },
          });
        }}
      >
        <Field label="Sarlavha" htmlFor="title" error={errors.title}>
          <Input id="title" value={values.title} onChange={set("title")} maxLength={200} />
        </Field>
        <Field label="Sana" htmlFor="event_date" error={errors.event_date}>
          <Input id="event_date" type="date" value={values.event_date} onChange={set("event_date")} />
        </Field>
        <Field label="Izoh" htmlFor="description" error={errors.description}>
          <Textarea id="description" value={values.description} onChange={set("description")} maxLength={2000} />
        </Field>
        <Button type="submit" loading={update.isPending}>
          Saqlash
        </Button>
      </form>
    </Modal>
  );
}

function InviteForm({ ceremonyId, takenCouple }: { ceremonyId: string; takenCouple: Set<ParticipantType> }) {
  const invite = useInvite(ceremonyId);
  const firstFree: ParticipantType = !takenCouple.has("BRIDE") ? "BRIDE" : !takenCouple.has("GROOM") ? "GROOM" : "OTHER";
  const [phone, setPhone] = useState("");
  const [type, setType] = useState<ParticipantType>(firstFree);
  const [errors, setErrors] = useState<Record<string, string>>({});

  return (
    <form
      noValidate
      className="flex flex-col gap-3 rounded-2xl border border-glass-border bg-muted/40 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        setErrors({});
        invite.mutate(
          { phone_number: phone, participant_type: type },
          {
            onSuccess: () => {
              toast.success("Taklif yuborildi");
              setPhone("");
              setType("OTHER");
            },
            onError: (err) => {
              if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors);
              else toast.error(err instanceof ApiError ? err.message : "Yuborib bo'lmadi");
            },
          },
        );
      }}
    >
      <p className="text-sm font-bold">Ishtirokchini taklif qilish</p>
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_150px_auto] sm:items-start">
        <Field label="Telefon raqam" htmlFor="invite_phone" error={errors.phone_number}>
          <div className="relative">
            <PhoneIcon className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="invite_phone"
              type="tel"
              inputMode="tel"
              placeholder="+998 90 123 45 67"
              className="pl-10 tabular-nums"
              aria-invalid={Boolean(errors.phone_number)}
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
        </Field>
        <Field label="Kim" htmlFor="invite_type" error={errors.participant_type}>
          <Select id="invite_type" value={type} onChange={(e) => setType(e.target.value as ParticipantType)}>
            {(["BRIDE", "GROOM", "OTHER"] as const).map((t) => (
              <option key={t} value={t} disabled={t !== "OTHER" && takenCouple.has(t)}>
                {PARTICIPANT_LABELS[t]}
              </option>
            ))}
          </Select>
        </Field>
        <Button type="submit" loading={invite.isPending} className="sm:mt-[26px]">
          <SendIcon /> Yuborish
        </Button>
      </div>
      <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
        <ShieldCheckIcon className="mt-0.5 size-3.5 shrink-0" />
        Shaxs taklifni o&apos;z hisobidan qabul qilmaguncha marosimni ko&apos;rmaydi, ismi ham ko&apos;rinmaydi. Raqam ro&apos;yxatdan
        o&apos;tmagan bo&apos;lsa, ro&apos;yxatdan o&apos;tgach taklifni ko&apos;radi.
      </p>
    </form>
  );
}

function ParticipantsCard({ ceremony }: { ceremony: Ceremony }) {
  const { data, error, isPending, refetch } = useParticipants(ceremony.id);
  const revoke = useRevoke(ceremony.id);
  const [confirm, setConfirm] = useState<Participant | null>(null);
  const open = (data ?? []).filter((p) => p.access_status === "INVITED" || p.access_status === "ACTIVE");
  const takenCouple = new Set(open.map((p) => p.participant_type).filter((t) => t !== "OTHER"));

  return (
    <Card className="flex flex-col gap-4">
      <h2 className="text-lg font-bold">Ishtirokchilar</h2>
      {ceremony.can_manage && <InviteForm key={open.length} ceremonyId={ceremony.id} takenCouple={takenCouple} />}
      {isPending ? (
        <Skeleton className="h-24" />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : data.length === 0 ? (
        <EmptyState title="Hali ishtirokchi yo'q" description="Kelin va kuyovni telefon raqami orqali taklif qiling." />
      ) : (
        <ul className="flex flex-col">
          <AnimatePresence initial={false}>
            {data.map((p) => (
              <motion.li
                key={p.id}
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex flex-wrap items-center gap-3 border-t border-border/70 py-3 first:border-t-0"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">{p.display_name ?? formatPhone(p.phone_number)}</p>
                  <p className="text-xs text-muted-foreground tabular-nums">
                    {PARTICIPANT_LABELS[p.participant_type]}
                    {p.display_name ? ` · ${formatPhone(p.phone_number)}` : ""} · {formatDateTime(p.responded_at ?? p.invited_at)}
                  </p>
                </div>
                <Badge tone={ACCESS_TONE[p.access_status]}>{ACCESS_LABELS[p.access_status]}</Badge>
                {ceremony.can_manage && (p.access_status === "INVITED" || p.access_status === "ACTIVE") && (
                  <Button size="sm" variant="ghost" aria-label="Olib tashlash" onClick={() => setConfirm(p)}>
                    <UserMinusIcon />
                  </Button>
                )}
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
      <Modal open={Boolean(confirm)} onClose={() => setConfirm(null)} title="Ishtirokchini olib tashlaysizmi?">
        <p className="mb-5 text-sm text-muted-foreground">
          {confirm && `${PARTICIPANT_LABELS[confirm.participant_type]} (${formatPhone(confirm.phone_number)})`} marosimga kirish
          huquqini darhol yo&apos;qotadi. Keyin qayta taklif qilish mumkin.
        </p>
        <div className="flex gap-3">
          <Button variant="outline" className="flex-1" onClick={() => setConfirm(null)}>
            Bekor qilish
          </Button>
          <Button
            variant="danger"
            className="flex-1"
            loading={revoke.isPending}
            onClick={() =>
              confirm &&
              revoke.mutate(confirm.id, {
                onSuccess: () => {
                  toast.success("Olib tashlandi");
                  setConfirm(null);
                },
                onError: (e) => toast.error(e instanceof ApiError ? e.message : "Bajarilmadi"),
              })
            }
          >
            Olib tashlash
          </Button>
        </div>
      </Modal>
    </Card>
  );
}

export default function StudioCeremonyPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, isPending, refetch } = useCeremony(id);
  const update = useUpdateCeremony(id);
  const [editing, setEditing] = useState(false);

  return (
    <>
      <Link href="/" className="flex items-center gap-1.5 px-1 text-sm font-semibold text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-4" /> Marosimlar
      </Link>
      {isPending ? (
        <Skeleton className="h-56 rounded-3xl" />
      ) : error ? (
        <Card>
          <ErrorState error={error} onRetry={() => refetch()} />
        </Card>
      ) : (
        <>
          <Card className="flex flex-col gap-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <Badge tone={STATUS_TONE[data.status]}>{STATUS_LABELS[data.status]}</Badge>
                <h1 className="mt-2 text-2xl font-extrabold tracking-tight sm:text-3xl">{data.title}</h1>
                <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
                  <CalendarDaysIcon className="size-4" /> {formatEventDate(data.event_date)} · {data.studio.name}
                </p>
              </div>
              {data.can_manage && (
                <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                  <PencilIcon /> Tahrirlash
                </Button>
              )}
            </div>
            {data.description && <p className="max-w-2xl text-sm leading-relaxed">{data.description}</p>}
            {data.can_manage && STUDIO_TRANSITIONS[data.status].length > 0 && (
              <div className="flex flex-wrap gap-2 border-t border-border/70 pt-4">
                {STUDIO_TRANSITIONS[data.status].map((next) => (
                  <Button
                    key={next}
                    size="sm"
                    variant={next === "READY" ? "primary" : "outline"}
                    loading={update.isPending && update.variables?.status === next}
                    onClick={() =>
                      update.mutate(
                        { status: next },
                        {
                          onSuccess: () => toast.success(`Holat: ${STATUS_LABELS[next]}`),
                          onError: (e) => toast.error(e instanceof ApiError ? e.message : "O'zgartirib bo'lmadi"),
                        },
                      )
                    }
                  >
                    {STATUS_ACTION[next] ?? STATUS_LABELS[next]}
                  </Button>
                ))}
                {data.status === "DRAFT" && (
                  <p className="w-full text-xs text-muted-foreground">Qoralama marosim kelin-kuyovga ko&apos;rinmaydi.</p>
                )}
              </div>
            )}
            {!data.can_manage && (
              <p className="text-xs text-muted-foreground">Sizda faqat ko&apos;rish huquqi bor (Yuklovchi).</p>
            )}
          </Card>
          <ParticipantsCard ceremony={data} />
          {editing && <EditModal ceremony={data} open={editing} onClose={() => setEditing(false)} />}
        </>
      )}
    </>
  );
}
