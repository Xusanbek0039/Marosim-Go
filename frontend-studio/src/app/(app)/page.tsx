"use client";

import { CalendarHeartIcon, ChevronRightIcon, PlusIcon, SearchIcon, UsersIcon } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageTitle } from "@/components/shell";
import { Avatar, Badge, Button, Card, cn, EmptyState, ErrorState, Field, Input, Modal, Select, Skeleton, Textarea } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatEventDate, STATUS_LABELS, STATUS_TONE } from "@/lib/format";
import { useCreateCeremony, useMyStudios, useStudioCeremonies } from "@/lib/studio";
import type { CeremonyStatus, MyStudioMembership } from "@/lib/types";

const ROLE_LABELS = { OWNER: "Egasi", MANAGER: "Menejer", UPLOADER: "Yuklovchi" } as const;
const FILTERS: { value: CeremonyStatus | ""; label: string }[] = [
  { value: "", label: "Barchasi" },
  { value: "DRAFT", label: "Qoralama" },
  { value: "READY", label: "Tayyor" },
  { value: "ARCHIVED", label: "Arxiv" },
];

function CreateCeremonyModal({
  open,
  onClose,
  managed,
}: {
  open: boolean;
  onClose: () => void;
  managed: MyStudioMembership[];
}) {
  // The modal mounts its children only while open, so the form starts fresh every time.
  return (
    <Modal open={open} onClose={onClose} title="Yangi marosim">
      <CreateCeremonyForm onClose={onClose} managed={managed} />
    </Modal>
  );
}

function CreateCeremonyForm({ onClose, managed }: { onClose: () => void; managed: MyStudioMembership[] }) {
  const router = useRouter();
  const create = useCreateCeremony();
  const [values, setValues] = useState({
    title: "",
    event_date: "",
    description: "",
    studio_id: managed[0]?.studio.id ?? "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const set = (key: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));

  return (
      <form
        noValidate
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          const local: Record<string, string> = {};
          if (!values.title.trim()) local.title = "Sarlavhani kiriting";
          if (!values.event_date) local.event_date = "Sanani tanlang";
          setErrors(local);
          if (Object.keys(local).length) return;
          create.mutate(
            { ...values, studio_id: managed.length > 1 ? values.studio_id : undefined },
            {
              onSuccess: (c) => {
                toast.success("Marosim yaratildi");
                onClose();
                router.push(`/ceremonies/${c.id}`);
              },
              onError: (err) => {
                if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors);
                else toast.error("Yaratib bo'lmadi");
              },
            },
          );
        }}
      >
        {managed.length > 1 && (
          <Field label="Studiya" htmlFor="studio_id" error={errors.studio_id}>
            <Select id="studio_id" value={values.studio_id} onChange={set("studio_id")}>
              {managed.map((m) => (
                <option key={m.studio.id} value={m.studio.id}>
                  {m.studio.name}
                </option>
              ))}
            </Select>
          </Field>
        )}
        <Field label="Sarlavha" htmlFor="title" error={errors.title}>
          <Input id="title" value={values.title} onChange={set("title")} placeholder="Masalan: Dilnoza & Jasur to'yi" maxLength={200} />
        </Field>
        <Field label="Marosim sanasi" htmlFor="event_date" error={errors.event_date}>
          <Input id="event_date" type="date" value={values.event_date} onChange={set("event_date")} />
        </Field>
        <Field label="Izoh (ixtiyoriy)" htmlFor="description" error={errors.description}>
          <Textarea id="description" value={values.description} onChange={set("description")} maxLength={2000} />
        </Field>
        <p className="text-xs text-muted-foreground">Marosim &quot;Qoralama&quot; holatida yaratiladi — kelin-kuyov uni &quot;Tayyor&quot; qilganingizdan keyin ko&apos;radi.</p>
        <div className="flex gap-3">
          <Button type="button" variant="outline" className="flex-1" onClick={onClose}>
            Bekor qilish
          </Button>
          <Button type="submit" className="flex-1" loading={create.isPending}>
            Yaratish
          </Button>
        </div>
      </form>
  );
}

export default function StudioHomePage() {
  const studios = useMyStudios();
  const [status, setStatus] = useState<CeremonyStatus | "">("");
  const [draft, setDraft] = useState("");
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const ceremonies = useStudioCeremonies({ status: status || undefined, search: search || undefined });

  useEffect(() => {
    const t = setTimeout(() => setSearch(draft.trim()), 350);
    return () => clearTimeout(t);
  }, [draft]);

  const managed = (studios.data ?? []).filter((m) => m.can_manage);

  return (
    <>
      <PageTitle
        title="Marosimlar"
        subtitle="Studiyangiz marosimlari va ishtirokchilari"
        actions={
          managed.length > 0 && (
            <Button onClick={() => setCreating(true)}>
              <PlusIcon /> Yangi marosim
            </Button>
          )
        }
      />

      {studios.isPending ? (
        <Skeleton className="h-24 rounded-3xl" />
      ) : studios.data && studios.data.length === 0 ? (
        <Card>
          <EmptyState
            title="Siz hali hech qaysi studiyaga biriktirilmagansiz"
            description="Studiya egasi yoki platforma administratori sizni studiyaga qo'shishi kerak."
          />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {studios.data?.map((m) => (
            <Card key={m.studio.id} className="flex items-center gap-4 p-4 sm:p-5">
              <Avatar first={m.studio.name} src={m.studio.profile_picture} className="size-14 rounded-2xl text-lg" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-lg font-bold">{m.studio.name}</p>
                <p className="truncate text-sm text-muted-foreground">{m.studio.address || "—"}</p>
              </div>
              <div className="flex flex-col items-end gap-1.5">
                <Badge tone="brand">{ROLE_LABELS[m.role]}</Badge>
                <span className="text-xs text-muted-foreground tabular-nums">{m.ceremonies_count} marosim</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {studios.data && studios.data.length > 0 && (
        <Card className="flex flex-col gap-4 p-4 sm:p-5">
          <div className="flex flex-wrap items-center gap-2.5">
            <label className="relative min-w-[220px] flex-1">
              <span className="sr-only">Qidirish</span>
              <SearchIcon className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Marosim nomi bo'yicha qidirish" className="pl-10" />
            </label>
            <div className="glass flex gap-1 rounded-xl p-1" role="group" aria-label="Holat filtri">
              {FILTERS.map((f) => (
                <button
                  key={f.value}
                  type="button"
                  aria-pressed={status === f.value}
                  onClick={() => setStatus(f.value)}
                  className={cn(
                    "relative rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
                    status === f.value ? "text-white" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {status === f.value && (
                    <motion.span layoutId="status-filter" className="absolute inset-0 rounded-lg brand-gradient" transition={{ type: "spring", stiffness: 380, damping: 32 }} />
                  )}
                  <span className="relative">{f.label}</span>
                </button>
              ))}
            </div>
          </div>

          {ceremonies.isPending ? (
            <div className="flex flex-col gap-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : ceremonies.error ? (
            <ErrorState error={ceremonies.error} onRetry={() => ceremonies.refetch()} />
          ) : ceremonies.data.results.length === 0 ? (
            <EmptyState
              title={search || status ? "Hech narsa topilmadi" : "Hali marosimlar yo'q"}
              description={search || status ? "Qidiruv yoki filtrni o'zgartiring." : "Birinchi marosimni yarating."}
            />
          ) : (
            <ul className={cn("flex flex-col transition-opacity", ceremonies.isFetching && "opacity-70")}>
              {ceremonies.data.results.map((c, i) => (
                <motion.li
                  key={c.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0, transition: { delay: i * 0.03 } }}
                  className="border-t border-border/70 first:border-t-0"
                >
                  <Link href={`/ceremonies/${c.id}`} className="group flex items-center gap-3 rounded-2xl px-2 py-3 transition hover:bg-muted/60">
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 text-white">
                      <CalendarHeartIcon className="size-5" aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold">{c.title}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {formatEventDate(c.event_date)}
                        {studios.data.length > 1 ? ` · ${c.studio.name}` : ""}
                      </p>
                    </div>
                    <span className="hidden items-center gap-1 text-xs text-muted-foreground tabular-nums sm:flex">
                      <UsersIcon className="size-3.5" /> {c.participants_summary.active}/{c.participants_summary.active + c.participants_summary.invited}
                    </span>
                    <Badge tone={STATUS_TONE[c.status]}>{STATUS_LABELS[c.status]}</Badge>
                    <ChevronRightIcon className="size-4 text-muted-foreground transition group-hover:translate-x-0.5" />
                  </Link>
                </motion.li>
              ))}
            </ul>
          )}
        </Card>
      )}

      <CreateCeremonyModal open={creating} onClose={() => setCreating(false)} managed={managed} />
    </>
  );
}
