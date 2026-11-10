"use client";

import { CheckIcon, ChevronRightIcon, FolderHeartIcon, FolderOpenIcon, MailOpenIcon, PencilIcon, XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { Recommended } from "@/components/recommended";
import { PageTitle } from "@/components/shell";
import { Badge, Button, Card, cn, EmptyState, ErrorState, Input, Skeleton } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useMe } from "@/lib/auth";
import { useInvitations, useMyCeremonies, useRenameFolder, useRespond } from "@/lib/ceremonies";
import { formatEventDate, PARTICIPANT_LABELS, STATUS_LABELS, STATUS_TONE } from "@/lib/format";
import { DURATION_LABEL } from "@/lib/sharing";
import type { Invitation, MyCeremony } from "@/lib/types";

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
          {invitation.access_duration && <> · <b>{DURATION_LABEL[invitation.access_duration]}</b> ko&apos;rish</>}
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

function FolderCard({ ceremony: c }: { ceremony: MyCeremony }) {
  const rename = useRenameFolder();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(c.folder_name);
  const owner = c.access_role === "OWNER";

  const save = () =>
    rename.mutate(
      { id: c.id, name: name.trim() },
      {
        onSuccess: (res) => {
          setName(res.folder_name);
          setEditing(false);
          toast.success("Papka nomi saqlandi");
        },
        onError: (e) => toast.error(e instanceof ApiError ? e.message : "Saqlanmadi"),
      },
    );

  return (
    <div className="glass group relative flex h-full flex-col gap-3 rounded-3xl p-5 transition hover:-translate-y-0.5 hover:border-cyan-400/40">
      <div className="flex items-start justify-between gap-3">
        <span
          className={cn(
            "flex size-12 items-center justify-center rounded-2xl text-white shadow-lg",
            owner ? "bg-gradient-to-br from-amber-500 to-rose-500" : "bg-gradient-to-br from-blue-600 to-cyan-500",
          )}
        >
          {owner ? <FolderHeartIcon className="size-6" aria-hidden /> : <FolderOpenIcon className="size-6" aria-hidden />}
        </span>
        <div className="flex items-center gap-1.5">
          <Badge tone={STATUS_TONE[c.status]}>{STATUS_LABELS[c.status]}</Badge>
          {!editing && (
            <button
              type="button"
              onClick={() => setEditing(true)}
              aria-label="Papka nomini o'zgartirish"
              className="rounded-lg p-1.5 text-muted-foreground transition hover:bg-muted hover:text-foreground"
            >
              <PencilIcon className="size-4" />
            </button>
          )}
        </div>
      </div>
      {editing ? (
        <form
          className="flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            save();
          }}
        >
          <Input autoFocus maxLength={100} value={name} onChange={(e) => setName(e.target.value)} aria-label="Papka nomi" placeholder={c.title} />
          <div className="flex gap-2">
            <Button size="sm" type="submit" loading={rename.isPending}>
              <CheckIcon /> Saqlash
            </Button>
            <Button
              size="sm"
              variant="ghost"
              type="button"
              onClick={() => {
                setEditing(false);
                setName(c.folder_name);
              }}
            >
              Bekor qilish
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">Bo&apos;sh qoldirsangiz, marosim nomi qaytadi. Nom faqat sizga ko&apos;rinadi.</p>
        </form>
      ) : (
        <Link href={`/ceremonies/${c.id}`} className="flex flex-1 flex-col gap-3">
          <div>
            <p className="text-lg font-bold">{c.folder_name}</p>
            {c.folder_name !== c.title && <p className="text-xs text-muted-foreground">{c.title}</p>}
            <p className="text-sm text-muted-foreground">
              {formatEventDate(c.event_date)} · {c.studio.name}
            </p>
          </div>
          <span className="mt-auto flex items-center gap-1 text-sm font-semibold text-brand dark:text-cyan-300">
            Papkani ochish <ChevronRightIcon className="size-4 transition group-hover:translate-x-0.5" />
          </span>
        </Link>
      )}
    </div>
  );
}

function FolderGroup({ title, hint, items }: { title: string; hint: string; items: MyCeremony[] }) {
  if (items.length === 0) return null;
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-1">
        <h2 className="text-lg font-bold">
          {title} <span className="text-sm font-semibold text-muted-foreground">· {items.length}</span>
        </h2>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </div>
      <motion.ul
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        initial="initial"
        animate="animate"
        variants={{ animate: { transition: { staggerChildren: 0.06 } } }}
      >
        {items.map((c) => (
          <motion.li key={c.id} variants={{ initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 } }}>
            <FolderCard ceremony={c} />
          </motion.li>
        ))}
      </motion.ul>
    </section>
  );
}

export default function HomePage() {
  const { data: me } = useMe();
  const ceremonies = useMyCeremonies();
  const invitations = useInvitations();

  return (
    <>
      <PageTitle title={`Salom${me?.first_name ? `, ${me.first_name}` : ""}!`} subtitle="Mening marosimlarim — har bir marosim alohida papka" />

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
            description="Studiya sizni telefon raqamingiz orqali taklif qilganda shu yerda papka bo'lib ko'rinadi."
          />
        </Card>
      ) : (
        <>
          <FolderGroup
            title="Mening to'yim"
            hint="Siz egasi bo'lgan marosimlar"
            items={ceremonies.data.results.filter((c) => c.access_role === "OWNER")}
          />
          <FolderGroup
            title="Menga ruxsat berilganlar"
            hint="Boshqalar siz bilan ulashgan marosimlar"
            items={ceremonies.data.results.filter((c) => c.access_role === "VIEWER")}
          />
        </>
      )}

      <Recommended />
    </>
  );
}
