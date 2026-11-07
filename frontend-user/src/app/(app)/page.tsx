"use client";

import { CalendarHeartIcon, CheckIcon, ChevronRightIcon, MailOpenIcon, XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { toast } from "sonner";

import { PageTitle } from "@/components/shell";
import { Badge, Button, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useMe } from "@/lib/auth";
import { useInvitations, useMyCeremonies, useRespond } from "@/lib/ceremonies";
import { formatEventDate, PARTICIPANT_LABELS, STATUS_LABELS, STATUS_TONE } from "@/lib/format";
import type { Invitation } from "@/lib/types";

function InvitationCard({ invitation }: { invitation: Invitation }) {
  const respond = useRespond();
  // mutateAsync, not mutate(cb): this card unmounts as soon as the list refreshes, and per-call
  // callbacks of an unmounted observer are skipped — the promise still resolves.
  const answer = (kind: "accept" | "decline") =>
    respond
      .mutateAsync({ id: invitation.id, answer: kind })
      .then(() => toast.success(kind === "accept" ? "Taklif qabul qilindi" : "Taklif rad etildi"))
      .catch((e) => toast.error(e instanceof ApiError ? e.message : "Javob yuborilmadi"));
  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: 30 }}
      className="flex flex-wrap items-center gap-3 rounded-2xl border border-cyan-400/30 bg-cyan-500/[0.07] p-4"
    >
      <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl brand-gradient text-white">
        <MailOpenIcon className="size-5" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-bold">{invitation.ceremony_title}</p>
        <p className="text-sm text-muted-foreground">
          {invitation.studio_name} · {formatEventDate(invitation.event_date)} · siz: <b>{invitation.participant_type ? PARTICIPANT_LABELS[invitation.participant_type] : "Ko'ruvchi"}</b>
        </p>
      </div>
      <div className="flex gap-2">
        <Button size="sm" variant="ghost" onClick={() => answer("decline")} disabled={respond.isPending}>
          <XIcon /> Rad etish
        </Button>
        <Button size="sm" onClick={() => answer("accept")} loading={respond.isPending}>
          <CheckIcon /> Qabul qilish
        </Button>
      </div>
    </motion.li>
  );
}

export default function HomePage() {
  const { data: me } = useMe();
  const ceremonies = useMyCeremonies();
  const invitations = useInvitations();

  return (
    <>
      <PageTitle title={`Salom${me?.first_name ? `, ${me.first_name}` : ""}!`} subtitle="Sizga biriktirilgan marosimlar" />

      {invitations.data && invitations.data.length > 0 && (
        <Card className="flex flex-col gap-3">
          <h2 className="text-base font-bold">Yangi takliflar</h2>
          <p className="text-sm text-muted-foreground">
            Studiya sizni marosimga qo&apos;shmoqchi. Qabul qilsangizgina marosim va uning materiallari sizga ko&apos;rinadi.
          </p>
          <ul className="flex flex-col gap-2.5">
            <AnimatePresence initial={false}>
              {invitations.data.map((inv) => (
                <InvitationCard key={inv.id} invitation={inv} />
              ))}
            </AnimatePresence>
          </ul>
        </Card>
      )}

      {ceremonies.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-36 rounded-3xl" />
          ))}
        </div>
      ) : ceremonies.error ? (
        <Card>
          <ErrorState error={ceremonies.error} onRetry={() => ceremonies.refetch()} />
        </Card>
      ) : ceremonies.data.results.length === 0 ? (
        <Card>
          <EmptyState
            title="Hali marosimlar yo'q"
            description="Studiya sizni telefon raqamingiz orqali taklif qilganda shu yerda ko'rinadi."
          />
        </Card>
      ) : (
        <motion.ul
          className="grid gap-4 sm:grid-cols-2"
          initial="initial"
          animate="animate"
          variants={{ animate: { transition: { staggerChildren: 0.06 } } }}
        >
          {ceremonies.data.results.map((c) => (
            <motion.li key={c.id} variants={{ initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 } }}>
              <Link
                href={`/ceremonies/${c.id}`}
                className="glass group flex h-full flex-col gap-3 rounded-3xl p-5 transition hover:-translate-y-0.5 hover:border-cyan-400/40"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="flex size-11 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 text-white">
                    <CalendarHeartIcon className="size-5" aria-hidden />
                  </span>
                  <Badge tone={STATUS_TONE[c.status]}>{STATUS_LABELS[c.status]}</Badge>
                </div>
                <div>
                  <p className="text-lg font-bold">{c.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {formatEventDate(c.event_date)} · {c.studio.name}
                  </p>
                </div>
                <span className="mt-auto flex items-center gap-1 text-sm font-semibold text-brand dark:text-cyan-300">
                  Ochish <ChevronRightIcon className="size-4 transition group-hover:translate-x-0.5" />
                </span>
              </Link>
            </motion.li>
          ))}
        </motion.ul>
      )}
    </>
  );
}
