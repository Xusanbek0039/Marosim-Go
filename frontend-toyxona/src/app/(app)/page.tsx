"use client";

import { Building2Icon, ChevronRightIcon, LayersIcon, PlusIcon, SearchIcon, UsersIcon, WalletIcon } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageTitle } from "@/components/shell";
import { Badge, Button, Card, cn, EmptyState, ErrorState, Input, Modal, Skeleton } from "@/components/ui";
import { EMPTY_VENUE, VenueForm } from "@/components/venue-form";
import { ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Venue } from "@/lib/types";
import { MEMBER_ROLES, PUBLICATION, REGION_LABELS, useCreateVenue, useMyVenues, VENUE_TYPE_LABELS } from "@/lib/venues";

function CreateVenueForm({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const create = useCreateVenue();
  const [errors, setErrors] = useState<Record<string, string>>({});
  return (
    <VenueForm
      initial={EMPTY_VENUE}
      errors={errors}
      pending={create.isPending}
      submitLabel="Yaratish"
      onCancel={onClose}
      onSubmit={(payload) =>
        create.mutate(payload, {
          onSuccess: (v) => {
            toast.success("To'yxona yaratildi. \"Asosiy zal\" avtomatik qo'shildi");
            onClose();
            router.push(`/venues/${v.id}`);
          },
          onError: (err) => {
            if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors);
            else toast.error(err instanceof ApiError ? err.message : "Yaratib bo'lmadi");
          },
        })
      }
    />
  );
}

function VenueCard({ venue, index }: { venue: Venue; index: number }) {
  const pub = PUBLICATION[venue.publication_status];
  const activeHalls = venue.halls.filter((h) => h.is_active).length;
  const stats = [
    { icon: LayersIcon, label: "Zal", value: String(activeHalls) },
    { icon: UsersIcon, label: "Sig'im", value: `${venue.capacity_min}–${venue.capacity_max}` },
    { icon: WalletIcon, label: "Narx", value: formatMoney(venue.base_price).replace(" so'm", "") },
  ];
  return (
    <motion.li initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0, transition: { delay: index * 0.04 } }}>
      <Link
        href={`/venues/${venue.id}`}
        className="glass group flex h-full flex-col overflow-hidden rounded-3xl transition hover:-translate-y-0.5 hover:border-cyan-400/40"
      >
        <div className="relative h-32 w-full overflow-hidden bg-gradient-to-br from-blue-600/80 to-cyan-500/70">
          {venue.cover_image ? (
            // eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side
            <img src={venue.cover_image} alt="" className="size-full object-cover transition duration-500 group-hover:scale-105" />
          ) : (
            <Building2Icon className="absolute right-4 bottom-3 size-16 text-white/25" aria-hidden />
          )}
          <div className="absolute top-3 left-3 flex gap-1.5">
            <Badge tone={pub.tone}>{pub.label}</Badge>
            {!venue.is_active && <Badge tone="danger">Bloklangan</Badge>}
          </div>
        </div>
        <div className="flex flex-1 flex-col gap-3 p-5">
          <div>
            <p className="truncate text-lg font-bold">{venue.name}</p>
            <p className="truncate text-sm text-muted-foreground">
              {VENUE_TYPE_LABELS[venue.venue_type]} · {REGION_LABELS[venue.region]}
              {venue.district ? `, ${venue.district}` : ""}
            </p>
          </div>
          <dl className="grid grid-cols-3 gap-2 text-center">
            {stats.map((s) => (
              <div key={s.label} className="rounded-2xl bg-muted/60 px-2 py-2">
                <dt className="flex items-center justify-center gap-1 text-[11px] font-semibold text-muted-foreground uppercase">
                  <s.icon className="size-3" aria-hidden /> {s.label}
                </dt>
                <dd className="truncate text-sm font-bold tabular-nums">{s.value}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-auto flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{venue.membership_role ? MEMBER_ROLES[venue.membership_role].label : ""}</span>
            <span className="flex items-center gap-1 font-semibold text-brand dark:text-cyan-300">
              Boshqarish <ChevronRightIcon className="size-4 transition group-hover:translate-x-0.5" />
            </span>
          </div>
        </div>
      </Link>
    </motion.li>
  );
}

export default function VenuesPage() {
  const [draft, setDraft] = useState("");
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const venues = useMyVenues(search || undefined);

  useEffect(() => {
    const t = setTimeout(() => setSearch(draft.trim()), 350);
    return () => clearTimeout(t);
  }, [draft]);

  const total = venues.data?.count ?? 0;

  return (
    <>
      <PageTitle
        title="To'yxonalarim"
        subtitle="Zallar, jamoa va bandlik jadvalini shu yerdan boshqarasiz"
        actions={
          <Button onClick={() => setCreating(true)}>
            <PlusIcon /> Yangi to&apos;yxona
          </Button>
        }
      />

      {(total > 3 || search) && (
        <label className="relative">
          <span className="sr-only">Qidirish</span>
          <SearchIcon className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Nomi, manzili yoki tumani bo'yicha" className="pl-10" />
        </label>
      )}

      {venues.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-72 rounded-3xl" />
          ))}
        </div>
      ) : venues.error ? (
        <Card>
          <ErrorState error={venues.error} onRetry={() => venues.refetch()} />
        </Card>
      ) : venues.data.results.length === 0 ? (
        <Card>
          <EmptyState
            title={search ? "Hech narsa topilmadi" : "Hali to'yxona yo'q"}
            description={
              search
                ? "Qidiruvni o'zgartiring."
                : "Birinchi to'yxonangizni qo'shing. U avval yopiq holatda bo'ladi, administrator tasdiqlagach mijozlarga ko'rinadi."
            }
            action={
              !search && (
                <Button onClick={() => setCreating(true)}>
                  <PlusIcon /> To&apos;yxona qo&apos;shish
                </Button>
              )
            }
          />
        </Card>
      ) : (
        <ul className={cn("grid gap-4 transition-opacity sm:grid-cols-2 lg:grid-cols-3", venues.isFetching && "opacity-70")}>
          {venues.data.results.map((v, i) => (
            <VenueCard key={v.id} venue={v} index={i} />
          ))}
        </ul>
      )}

      <Modal open={creating} onClose={() => setCreating(false)} title="Yangi to'yxona">
        <CreateVenueForm onClose={() => setCreating(false)} />
      </Modal>
    </>
  );
}
