"use client";

import { ArrowLeftIcon, CalendarDaysIcon, HeartIcon, MapPinIcon } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { Gallery } from "@/components/gallery";
import { SharePanel } from "@/components/share-panel";
import { Badge, Card, ErrorState, Skeleton } from "@/components/ui";
import { useMyCeremony } from "@/lib/ceremonies";
import { formatEventDate, PARTICIPANT_LABELS, STATUS_LABELS, STATUS_TONE } from "@/lib/format";

export default function CeremonyPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, isPending, refetch } = useMyCeremony(id);

  return (
    <>
      <Link href="/" className="flex items-center gap-1.5 px-1 text-sm font-semibold text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-4" /> Marosimlarim
      </Link>
      {isPending ? (
        <Skeleton className="h-64 rounded-3xl" />
      ) : error ? (
        <Card>
          <ErrorState error={error} onRetry={() => refetch()} />
        </Card>
      ) : (
        <>
          <Card className="relative overflow-hidden">
            <div aria-hidden className="pointer-events-none absolute -top-20 -right-16 size-64 rounded-full bg-cyan-500/20 blur-3xl" />
            <div className="relative flex flex-col gap-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={STATUS_TONE[data.status]}>{STATUS_LABELS[data.status]}</Badge>
                {data.my_role ? (
                  <Badge tone="brand">Siz: {PARTICIPANT_LABELS[data.my_role]}</Badge>
                ) : (
                  data.access_role === "VIEWER" && <Badge tone="warning">Ko&apos;ruvchi</Badge>
                )}
              </div>
              <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">{data.title}</h1>
              <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <CalendarDaysIcon className="size-4" /> {formatEventDate(data.event_date)}
                </span>
                <span className="flex items-center gap-1.5">
                  <MapPinIcon className="size-4" /> {data.studio.name}
                  {data.studio.address ? `, ${data.studio.address}` : ""}
                </span>
              </div>
              {data.description && <p className="max-w-2xl text-sm leading-relaxed">{data.description}</p>}
            </div>
          </Card>

          <Gallery ceremonyId={data.id} isOwner={data.access_role === "OWNER"} />

          <div className={data.access_role === "OWNER" ? "grid gap-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]" : ""}>
            <Card className="flex flex-col gap-3 self-start">
              <h2 className="flex items-center gap-2 text-base font-bold">
                <HeartIcon className="size-4 text-pink-500" /> Ishtirokchilar
              </h2>
              <ul className="flex flex-col gap-2">
                {data.participants.map((p, i) => (
                  <li key={i} className="flex items-center justify-between rounded-2xl bg-muted/60 px-3.5 py-2.5 text-sm">
                    <span className="font-semibold">{p.full_name || "—"}</span>
                    <span className="text-muted-foreground">{PARTICIPANT_LABELS[p.participant_type]}</span>
                  </li>
                ))}
              </ul>
            </Card>
            {data.access_role === "OWNER" && <SharePanel ceremonyId={data.id} />}
          </div>
        </>
      )}
    </>
  );
}
