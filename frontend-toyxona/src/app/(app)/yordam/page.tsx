"use client";

import { ArrowLeftIcon, CheckIcon, LifeBuoyIcon, PlusIcon, SendIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageTitle } from "@/components/shell";
import { Badge, Button, Card, cn, EmptyState, ErrorState, Field, Input, Modal, Skeleton, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { TICKET_STATUS, useCloseTicket, useCreateTicket, useReply, useTicket, useTickets } from "@/lib/support";

const errorText = (e: unknown) => (e instanceof ApiError ? (Object.values(e.fieldErrors)[0] as string | undefined) ?? e.message : "Yuborib bo'lmadi");

function NewTicketModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (id: string) => void }) {
  const create = useCreateTicket();
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const close = () => {
    setSubject("");
    setBody("");
    onClose();
  };
  return (
    <Modal open={open} onClose={close} title="Yordam so'rash">
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate(
            { subject: subject.trim(), body: body.trim() },
            {
              onSuccess: (t) => {
                toast.success("Xatingiz yuborildi. Javob shu sahifada ko'rinadi.");
                close();
                onCreated(t.id);
              },
              onError: (err) => toast.error(errorText(err)),
            },
          );
        }}
      >
        <Field label="Mavzu" htmlFor="t-subject">
          <Input id="t-subject" value={subject} maxLength={200} required autoFocus placeholder="Masalan: video ochilmayapti" onChange={(e) => setSubject(e.target.value)} />
        </Field>
        <Field label="Xabar" htmlFor="t-body" hint="Muammoni batafsil yozing: qaysi sahifa, nima bo'ldi, qachondan beri.">
          <Textarea id="t-body" value={body} maxLength={5000} required className="min-h-36" onChange={(e) => setBody(e.target.value)} />
        </Field>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={close}>
            Bekor qilish
          </Button>
          <Button type="submit" loading={create.isPending} disabled={!subject.trim() || !body.trim()}>
            <SendIcon /> Yuborish
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function Thread({ id, onBack }: { id: string; onBack: () => void }) {
  const { data, error, isPending, refetch } = useTicket(id);
  const reply = useReply(id);
  const closeTicket = useCloseTicket(id);
  const [body, setBody] = useState("");

  if (isPending) return <Skeleton className="h-64" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  const status = TICKET_STATUS[data.status];

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start gap-3">
        <Button size="sm" variant="ghost" onClick={onBack} aria-label="Ro'yxatga qaytish">
          <ArrowLeftIcon />
        </Button>
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-bold">{data.subject}</h2>
          <p className="text-xs text-muted-foreground">Yuborilgan: {formatDateTime(data.created_at)}</p>
        </div>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>
      <ul className="flex flex-col gap-3">
        {data.messages.map((m) => (
          <li key={m.id} className={cn("flex flex-col gap-1", m.is_mine ? "items-end" : "items-start")}>
            <div className={cn("max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap", m.is_mine ? "brand-gradient text-white" : "bg-muted")}>{m.body}</div>
            <span className="px-1 text-xs text-muted-foreground">
              {m.is_mine ? "Siz" : m.author_name} · {formatDateTime(m.created_at)}
            </span>
          </li>
        ))}
      </ul>
      <form
        className="flex flex-col gap-2 border-t border-border/70 pt-4"
        onSubmit={(e) => {
          e.preventDefault();
          reply.mutate(body.trim(), { onSuccess: () => setBody(""), onError: (err) => toast.error(errorText(err)) });
        }}
      >
        <Textarea
          aria-label="Xabar"
          value={body}
          maxLength={5000}
          placeholder={data.status === "CLOSED" ? "Yozsangiz, xat qayta ochiladi" : "Qo'shimcha ma'lumot yoki savol"}
          onChange={(e) => setBody(e.target.value)}
        />
        <div className="flex flex-wrap justify-end gap-2">
          {data.status !== "CLOSED" && (
            <Button
              type="button"
              variant="ghost"
              loading={closeTicket.isPending}
              onClick={() => closeTicket.mutate(undefined, { onSuccess: () => toast.success("Xat yopildi"), onError: (err) => toast.error(errorText(err)) })}
            >
              <CheckIcon /> Muammo hal bo&apos;ldi
            </Button>
          )}
          <Button type="submit" loading={reply.isPending} disabled={!body.trim()}>
            <SendIcon /> Yuborish
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default function SupportPage() {
  const { data, error, isPending, refetch } = useTickets();
  const [open, setOpen] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  return (
    <div className="flex flex-col gap-6">
      <PageTitle
        title="Yordam"
        subtitle="Savol yoki muammo bo'lsa, yozing — MarosimGo jamoasi shu yerda javob beradi."
        actions={
          !open && (
            <Button onClick={() => setCreating(true)}>
              <PlusIcon /> Yangi xat
            </Button>
          )
        }
      />
      {open ? (
        <Thread id={open} onBack={() => setOpen(null)} />
      ) : isPending ? (
        <Skeleton className="h-40" />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : data.results.length === 0 ? (
        <Card>
          <EmptyState
            title="Hali xat yozmagansiz"
            description="Muammo yoki savol bo'lsa, «Yangi xat» tugmasini bosing."
            action={
              <Button onClick={() => setCreating(true)}>
                <LifeBuoyIcon /> Yordam so&apos;rash
              </Button>
            }
          />
        </Card>
      ) : (
        <Card className="p-0 sm:p-0">
          <ul className="divide-y divide-border/70">
            {data.results.map((t) => (
              <li key={t.id}>
                <button type="button" onClick={() => setOpen(t.id)} className="flex w-full items-center gap-3 px-5 py-4 text-left transition hover:bg-muted/50">
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold">{t.subject}</p>
                    <p className="truncate text-xs text-muted-foreground">{t.last_message}</p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <Badge tone={TICKET_STATUS[t.status].tone}>{TICKET_STATUS[t.status].label}</Badge>
                    <span className="text-xs text-muted-foreground tabular-nums">{formatDateTime(t.last_message_at)}</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}
      <NewTicketModal open={creating} onClose={() => setCreating(false)} onCreated={setOpen} />
    </div>
  );
}
