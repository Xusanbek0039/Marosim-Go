"use client";

import { ArrowLeftIcon, CameraIcon, MessageCircleIcon, SendIcon } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { PaidBadge } from "@/components/paid-badge";
import { PageTitle } from "@/components/shell";
import { Button, Card, cn, EmptyState, ErrorState, Skeleton, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { type ChatStudio, useMyChats, useMyThread, useSendToStudio } from "@/lib/studios";

function StudioAvatar({ studio }: { studio: ChatStudio }) {
  return studio.profile_picture ? (
    // eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side
    <img src={studio.profile_picture} alt="" className="size-10 shrink-0 rounded-full object-cover" />
  ) : (
    <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-fuchsia-600/25 to-cyan-500/25 text-cyan-600">
      <CameraIcon className="size-5" aria-hidden />
    </span>
  );
}

function Inbox() {
  const params = useSearchParams();
  const router = useRouter();
  const openId = params.get("studio");
  const chats = useMyChats();
  const open = (id: string | null) => router.replace(id ? `/xabarlar?studio=${id}` : "/xabarlar", { scroll: false });

  return (
    <Card className="grid min-h-[65dvh] gap-0 overflow-hidden p-0 sm:p-0 md:grid-cols-[300px_1fr]">
      <aside className={cn("flex flex-col border-border md:border-r", openId && "hidden md:flex")}>
        <p className="border-b border-border px-4 py-3 text-sm font-bold">Studiyalar</p>
        {chats.isPending ? (
          <div className="flex flex-col gap-2 p-3">
            <Skeleton className="h-14 rounded-xl" />
            <Skeleton className="h-14 rounded-xl" />
          </div>
        ) : chats.error ? (
          <ErrorState error={chats.error} onRetry={() => chats.refetch()} />
        ) : chats.data.length === 0 ? (
          <EmptyState
            title="Hali suhbat yo'q"
            description="Studiya sahifasidagi “Studiyaga yozish” tugmasi orqali savol bering."
            action={<Link href="/studiyalar" className="text-sm font-semibold text-brand dark:text-cyan-300">Studiyalarni ko&apos;rish</Link>}
          />
        ) : (
          <ul className="flex flex-col overflow-y-auto">
            {chats.data.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => open(c.studio.id)}
                  className={cn("flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-muted", openId === c.studio.id && "bg-muted")}
                >
                  <StudioAvatar studio={c.studio} />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-semibold">{c.studio.name} <PaidBadge verified={c.studio.is_verified} /></span>
                      {c.unread > 0 && <span className="brand-gradient rounded-full px-2 py-0.5 text-[11px] font-bold text-white">{c.unread}</span>}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {c.last_message ? `${c.last_message.from_studio ? "" : "Siz: "}${c.last_message.body}` : ""}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>
      <section className={cn("flex min-h-[65dvh] flex-col", !openId && "hidden md:flex")}>
        {openId ? (
          <Thread key={openId} studioId={openId} onBack={() => open(null)} />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-muted-foreground">
            <MessageCircleIcon className="size-10" aria-hidden />
            <p className="text-sm">Suhbatni tanlang</p>
          </div>
        )}
      </section>
    </Card>
  );
}

function Thread({ studioId, onBack }: { studioId: string; onBack: () => void }) {
  const thread = useMyThread(studioId);
  const send = useSendToStudio(studioId);
  const [text, setText] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const count = thread.data?.messages.length ?? 0;

  useEffect(() => end.current?.scrollIntoView({ block: "end" }), [count]);

  const submit = () => {
    const body = text.trim();
    if (!body) return;
    send.mutate(body, {
      onSuccess: () => (setText(""), thread.refetch()),
      onError: (e) => toast.error(e instanceof ApiError && e.code === "badge_required" ? "Bu studiyaga hozir yozib bo'lmaydi." : e.message),
    });
  };

  if (thread.isPending) return <Skeleton className="m-4 h-40 rounded-2xl" />;
  if (thread.error) return <ErrorState error={thread.error} onRetry={() => thread.refetch()} />;
  const t = thread.data;
  return (
    <>
      <header className="flex items-center gap-3 border-b border-border px-4 py-3">
        <button type="button" onClick={onBack} className="rounded-lg p-1 hover:bg-muted md:hidden" aria-label="Orqaga">
          <ArrowLeftIcon className="size-4" />
        </button>
        <StudioAvatar studio={t.studio} />
        <Link href={`/studiyalar/${t.studio.id}`} className="font-bold hover:underline">
          {t.studio.name} <PaidBadge verified={t.studio.is_verified} />
        </Link>
      </header>
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-4">
        {t.messages.length === 0 && (
          <p className="m-auto max-w-xs text-center text-sm text-muted-foreground">
            Sana, narx yoki xizmatlar haqida so&apos;rang — studiya shu yerda javob beradi.
          </p>
        )}
        {t.messages.map((m) => (
          <div key={m.id} className={cn("flex", m.from_studio ? "justify-start" : "justify-end")}>
            <div className={cn("max-w-[80%] rounded-2xl px-3.5 py-2 text-sm", m.from_studio ? "rounded-bl-md bg-muted" : "brand-gradient rounded-br-md text-white")}>
              <p className="break-words whitespace-pre-line">{m.body}</p>
              <p className={cn("mt-0.5 text-right text-[10px]", m.from_studio ? "text-muted-foreground" : "text-white/70")}>{formatDateTime(m.created_at)}</p>
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
            placeholder="Xabar yozing…"
            aria-label="Xabar"
            className="min-h-11 flex-1 resize-none"
          />
          <Button type="submit" loading={send.isPending} disabled={!text.trim()} aria-label="Yuborish" className="size-11 px-0">
            <SendIcon />
          </Button>
        </form>
      ) : (
        <p className="border-t border-border p-3 text-center text-xs text-muted-foreground">Bu studiya hozircha chat orqali xabar qabul qilmaydi.</p>
      )}
    </>
  );
}

export default function MessagesPage() {
  return (
    <>
      <PageTitle title="Xabarlar" subtitle="Studiyalar bilan yozishmalaringiz" />
      <Suspense fallback={<Skeleton className="h-96 rounded-3xl" />}>
        <Inbox />
      </Suspense>
    </>
  );
}
