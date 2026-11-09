"use client";

import { ImagePlusIcon, XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { PageTitle } from "@/components/shell";
import { Button, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { MAX_PORTFOLIO_IMAGES, useDeletePortfolio, useMyStudios, usePortfolio, useUploadPortfolio } from "@/lib/studio";
import type { MyStudioMembership } from "@/lib/types";

const MAX_BYTES = 5 * 1024 * 1024;
const errorText = (e: unknown, fallback: string) => (e instanceof ApiError ? (e.fieldErrors.image ?? e.message) : fallback);

function StudioPortfolio({ membership }: { membership: MyStudioMembership }) {
  const { studio, can_manage } = membership;
  const { data, error, isPending, refetch } = usePortfolio(studio.id);
  const upload = useUploadPortfolio(studio.id);
  const remove = useDeletePortfolio(studio.id);
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const left = MAX_PORTFOLIO_IMAGES - (data?.length ?? 0);

  const add = async (files: FileList | null) => {
    if (!files?.length) return;
    const list = Array.from(files).filter((f) => f.size <= MAX_BYTES).slice(0, left);
    if (list.length < files.length) toast.error("Ba'zi rasmlar 5 MB dan katta yoki limitdan oshdi");
    setBusy(true);
    let done = 0;
    for (const file of list) {
      try {
        await upload.mutateAsync(file);
        done += 1;
      } catch (e) {
        toast.error(`${file.name}: ${errorText(e, "yuklanmadi")}`);
      }
    }
    setBusy(false);
    if (done) toast.success(`${done} ta rasm yuklandi`);
  };

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">{studio.name}</h2>
          <p className="text-sm text-muted-foreground">
            {data?.length ?? 0}/{MAX_PORTFOLIO_IMAGES} rasm · mijozlar studiya profilida ko&apos;radi
          </p>
        </div>
        {can_manage && left > 0 && (
          <>
            <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={(e) => (add(e.target.files), (e.target.value = ""))} />
            <Button onClick={() => input.current?.click()} loading={busy}>
              <ImagePlusIcon /> Rasm qo&apos;shish
            </Button>
          </>
        )}
      </div>
      {isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : data.length === 0 ? (
        <EmptyState title="Portfolio bo'sh" description="Eng yaxshi ishlaringizdan suratlar qo'shing — ular reklama kartangizda chiqadi." />
      ) : (
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <AnimatePresence initial={false}>
            {data.map((img) => (
              <motion.li key={img.id} layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} className="group relative aspect-square overflow-hidden rounded-xl">
                {/* eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side */}
                <img src={img.image} alt="" className="size-full object-cover" />
                {can_manage && (
                  <button
                    type="button"
                    aria-label="Rasmni o'chirish"
                    onClick={() => remove.mutate(img.id, { onError: (e) => toast.error(errorText(e, "O'chirilmadi")) })}
                    className="absolute top-1.5 right-1.5 inline-flex size-7 items-center justify-center rounded-full bg-slate-950/70 text-white opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100"
                  >
                    <XIcon className="size-4" />
                  </button>
                )}
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </Card>
  );
}

export default function PortfolioPage() {
  const studios = useMyStudios();
  return (
    <>
      <PageTitle title="Portfolio" subtitle="Ishlaringiz — mijozlar ilovasida reklama sifatida ko'rinadi" />
      {studios.isPending ? (
        <Skeleton className="h-48 rounded-3xl" />
      ) : studios.error ? (
        <Card>
          <ErrorState error={studios.error} onRetry={() => studios.refetch()} />
        </Card>
      ) : studios.data.length === 0 ? (
        <Card>
          <EmptyState title="Studiya topilmadi" description="Hisobingiz hali studiyaga biriktirilmagan." />
        </Card>
      ) : (
        studios.data.map((m) => <StudioPortfolio key={m.studio.id} membership={m} />)
      )}
    </>
  );
}
