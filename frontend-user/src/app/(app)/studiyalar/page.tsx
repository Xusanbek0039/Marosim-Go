"use client";

import { SearchIcon } from "lucide-react";
import { motion } from "motion/react";
import { useDeferredValue, useState } from "react";

import { StudioAdCard } from "@/components/ad-cards";
import { PageTitle } from "@/components/shell";
import { Card, cn, EmptyState, ErrorState, Input, Skeleton } from "@/components/ui";
import { usePublicStudios } from "@/lib/studios";

export default function StudiosPage() {
  const [q, setQ] = useState("");
  const query = useDeferredValue(q.trim());
  const { data, error, isPending, isPlaceholderData, refetch } = usePublicStudios(query);

  return (
    <>
      <PageTitle title="Studiyalar" subtitle="Foto va video studiyalar ishlari, baholari va bo'sh kunlari" />

      <Card className="p-4 sm:p-4">
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input className="pl-9" placeholder="Studiya nomi yoki manzili" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Qidiruv" />
        </div>
      </Card>

      {isPending ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-72 rounded-3xl" />
          ))}
        </div>
      ) : error ? (
        <Card>
          <ErrorState error={error} onRetry={() => refetch()} />
        </Card>
      ) : data.length === 0 ? (
        <Card>
          <EmptyState title={query ? "Hech narsa topilmadi" : "Hali studiyalar yo'q"} description={query ? "Boshqa so'z bilan qidirib ko'ring." : undefined} />
        </Card>
      ) : (
        <motion.ul
          className={cn("grid gap-4 sm:grid-cols-2", isPlaceholderData && "opacity-60")}
          initial="initial"
          animate="animate"
          variants={{ animate: { transition: { staggerChildren: 0.05 } } }}
        >
          {data.map((s, i) => (
            <motion.li key={s.id} variants={{ initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 } }}>
              <StudioAdCard studio={s} top={i === 0 && Boolean(s.stats.rating_count)} />
            </motion.li>
          ))}
        </motion.ul>
      )}
    </>
  );
}
