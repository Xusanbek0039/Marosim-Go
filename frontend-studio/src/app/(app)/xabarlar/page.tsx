"use client";

import { ArrowLeftIcon, MessageCircleIcon, SendIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { BadgeUpsell } from "@/components/badge-upsell";
import { PageTitle } from "@/components/shell";
import { Avatar, Button, Card, cn, EmptyState, ErrorState, Select, Skeleton, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useMyStudios, useSendStudioMessage, useStudioChats, useStudioThread } from "@/lib/studio";
import type { MyStudioMembership } from "@/lib/types";

function Inbox({ membership }: { membership: MyStudioMembership }) {
  const { studio } = membership;
  const chats = useStudioChats(studio.id);
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-4">
      {!studio.is_verified && <BadgeUpsell title="Mijozlar sizga yoza olishi uchun galichka oling" compact />}
      <Card className="grid min-h-[60dvh] gap-0 overflow-hidden p-0 sm:p-0 md:grid-cols-[300px_1fr]">
        <aside className={cn("flex flex-col border-border md:border-r", openId && "hidden md:flex")}>
          <p className="border-b border-border px-4 py-3 text-sm font-bold">Suhbatlar</p>
          {chats.isPending ? (
            <div className="flex flex-col gap-2 p-3">
              <Skeleton className="h-14 rounded-xl" />
              <Skeleton className="h-14 rounded-xl" />
            </div>
          ) : chats.error ? (
            <ErrorState error={chats.error} onRetry={() => chats.refetch()} />
          ) : chats.data.length === 0 ? (
            <EmptyState title="Hali xabar yo'q" description="Mijozlar studiya profilingizdan yozganda shu yerda ko'rinadi." />
          ) : (
            <ul className="flex flex-col overflow-y-auto">
              {chats.data.map((c) => {
                const [first, ...rest] = c.customer.name.split(" ");
                return (
                  <li key={c.id}>
                    <button
                      type="button"
                      onClick={() => setOpenId(c.id)}
                      className={cn("flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-muted", openId === c.id && "bg-muted")}
                    >
                      <Avatar first={first} last={rest.join(" ")} className="size-10 text-xs" />
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center justify-between gap-2">
                          <span className="truncate text-sm font-semibold">{c.customer.name}</span>
                          {c.unread > 0 && <span className="brand-gradient rounded-full px-2 py-0.5 text-[11px] font-bold text-white">{c.unread}</span>}
                        </span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {c.last_message ? `${c.last_message.from_studio ? "Siz: " : ""}${c.last_message.body}` : ""}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </aside>
        <section className={cn("flex min-h-[60dvh] flex-col", !openId && "hidden md:flex")}>
          {openId ? (
            <Thread studioId={studio.id} conversationId={openId} onBack={() => setOpenId(null)} />
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-muted-foreground">
              <MessageCircleIcon className="size-10" aria-hidden />
              <p className="text-sm">Suhbatni tanlang</p>
            </div>
          )}
        </section>
      </Card>
    </div>
  );
}

function Thread({ studioId, conversationId, onBack }: { studioId: string; conversationId: string; onBack: () => void }) {
  const thread = useStudioThread(studioId, conversationId);
  const send = useSendStudioMessage(studioId, conversationId);
  const [text, setText] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const count = thread.data?.messages.length ?? 0;

  useEffect(() => end.current?.scrollIntoView({ block: "end" }), [count]);

  const submit = () => {
    const body = text.trim();
    if (!body) return;
    send.mutate(body, {
      onSuccess: () => (setText(""), thread.refetch()),
      onError: (e) => toast.error(e instanceof ApiError && e.code === "badge_required" ? "Javob yozish uchun galichka kerak." : e.message),
    });
  };

  if (thread.isPending) return <Skeleton className="m-4 h-40 rounded-2xl" />;
  if (thread.error) return <ErrorState error={thread.error} onRetry={() => thread.refetch()} />;
  const t = thread.data;
  return (
    <>
      <header className="flex items-center gap-2 border-b border-border px-4 py-3">
        <button type="button" onClick={onBack} className="rounded-lg p-1 hover:bg-muted md:hidden" aria-label="Orqaga">
          <ArrowLeftIcon className="size-4" />
        </button>
        <p className="font-bold">{t.customer.name}</p>
      </header>
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-4">
        {t.messages.map((m) => (
          <div key={m.id} className={cn("flex", m.from_studio ? "justify-end" : "justify-start")}>
            <div className={cn("max-w-[80%] rounded-2xl px-3.5 py-2 text-sm", m.from_studio ? "brand-gradient rounded-br-md text-white" : "rounded-bl-md bg-muted")}>
              <p className="break-words whitespace-pre-line">{m.body}</p>
              <p className={cn("mt-0.5 text-right text-[10px]", m.from_studio ? "text-white/70" : "text-muted-foreground")}>{formatDateTime(m.created_at)}</p>
            </div>
          </div>
        ))}
        <div ref={end} />
      </div>
      {t.can_write ? (
        <form
          className="flex items-end gap-2 border-t border-border p-3"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <Textarea
            value={text}
            maxLength={2000}
            rows={1}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Javob yozing…"
            aria-label="Xabar"
            className="min-h-11 flex-1 resize-none"
          />
          <Button type="submit" loading={send.isPending} disabled={!text.trim()} aria-label="Yuborish" className="size-11 px-0">
            <SendIcon />
          </Button>
        </form>
      ) : (
        <p className="border-t border-border p-3 text-center text-xs text-muted-foreground">
          Javob yozish uchun galichka faol bo&apos;lishi va siz egasi yoki menejer bo&apos;lishingiz kerak.
        </p>
      )}
    </>
  );
}

export default function MessagesPage() {
  const studios = useMyStudios();
  const [selected, setSelected] = useState("");
  const membership = studios.data?.find((m) => m.studio.id === selected) ?? studios.data?.[0];
  return (
    <>
      <PageTitle
        title="Xabarlar"
        subtitle="Mijozlar studiya profilingizdan yozgan savollar"
        actions={
          studios.data && studios.data.length > 1 ? (
            <Select value={membership?.studio.id} onChange={(e) => setSelected(e.target.value)} aria-label="Studiya">
              {studios.data.map((m) => (
                <option key={m.studio.id} value={m.studio.id}>{m.studio.name}</option>
              ))}
            </Select>
          ) : undefined
        }
      />
      {studios.isPending ? (
        <Skeleton className="h-96 rounded-3xl" />
      ) : studios.error ? (
        <Card>
          <ErrorState error={studios.error} onRetry={() => studios.refetch()} />
        </Card>
      ) : !membership ? (
        <Card>
          <EmptyState title="Studiya topilmadi" description="Hisobingiz hali studiyaga biriktirilmagan." />
        </Card>
      ) : (
        <Inbox key={membership.studio.id} membership={membership} />
      )}
    </>
  );
}
