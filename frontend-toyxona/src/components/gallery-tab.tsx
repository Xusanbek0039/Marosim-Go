"use client";

import { ImagePlusIcon, Loader2Icon, Trash2Icon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import type { Venue } from "@/lib/types";
import { can, MAX_GALLERY_IMAGES, MAX_IMAGE_BYTES, useDeleteImage, useUploadImage } from "@/lib/venues";

import { Button, Card, cn } from "./ui";

const errorText = (e: unknown, fallback: string) => (e instanceof ApiError ? (e.fieldErrors.image ?? e.message) : fallback);

export function GalleryTab({ venue }: { venue: Venue }) {
  const editable = can(venue, "EDIT_PROFILE");
  const upload = useUploadImage(venue.id);
  const remove = useDeleteImage(venue.id);
  const input = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [dragging, setDragging] = useState(false);
  const left = MAX_GALLERY_IMAGES - venue.images.length;

  const add = async (files: FileList | File[]) => {
    const list = Array.from(files).filter((f) => f.type.startsWith("image/"));
    if (!list.length) return;
    const tooBig = list.filter((f) => f.size > MAX_IMAGE_BYTES);
    if (tooBig.length) toast.error(`${tooBig.length} ta rasm 5 MB dan katta, o'tkazib yuborildi`);
    const fit = list.filter((f) => f.size <= MAX_IMAGE_BYTES);
    if (fit.length > left) toast.error(`Ko'pi bilan ${MAX_GALLERY_IMAGES} ta rasm: faqat ${left} tasi yuklanadi`);
    const queue = fit.slice(0, left);
    if (!queue.length) return;
    setProgress({ done: 0, total: queue.length });
    let ok = 0;
    for (const [i, file] of queue.entries()) {
      try {
        await upload.mutateAsync(file);
        ok += 1;
      } catch (e) {
        toast.error(`${file.name}: ${errorText(e, "yuklanmadi")}`);
      }
      setProgress({ done: i + 1, total: queue.length });
    }
    setProgress(null);
    if (ok) toast.success(`${ok} ta rasm yuklandi`);
  };

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold">Rasmlar</h2>
          <p className="text-sm text-muted-foreground">Mijozlar to&apos;yxonangizni shu rasmlar orqali ko&apos;radi. JPG, PNG, WEBP · har biri 5 MB gacha.</p>
        </div>
        <span className={cn("text-sm font-bold tabular-nums", left === 0 ? "text-danger" : "text-muted-foreground")}>
          {venue.images.length}/{MAX_GALLERY_IMAGES}
        </span>
      </div>

      {editable && left > 0 && (
        <div
          onDragOver={(e) => (e.preventDefault(), setDragging(true))}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            add(e.dataTransfer.files);
          }}
          className={cn(
            "flex flex-col items-center gap-3 rounded-3xl border-2 border-dashed px-6 py-7 text-center transition",
            dragging ? "border-accent bg-cyan-500/10" : "border-glass-border bg-muted/30",
          )}
        >
          <span className="flex size-12 items-center justify-center rounded-2xl brand-gradient text-white">
            {progress ? <Loader2Icon className="size-6 animate-spin" /> : <ImagePlusIcon className="size-6" />}
          </span>
          <p className="text-sm font-semibold">
            {progress ? `Yuklanmoqda: ${progress.done}/${progress.total}` : `Rasmlarni shu yerga tashlang (yana ${left} ta)`}
          </p>
          <input
            ref={input}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files) add(e.target.files);
              e.target.value = "";
            }}
          />
          <Button size="sm" onClick={() => input.current?.click()} disabled={Boolean(progress)}>
            Rasm tanlash
          </Button>
        </div>
      )}

      {venue.images.length === 0 ? (
        <p className="rounded-2xl bg-muted/50 p-6 text-center text-sm text-muted-foreground">Hali rasm yuklanmagan.</p>
      ) : (
        <ul className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          <AnimatePresence initial={false}>
            {venue.images.map((img, i) => (
              <motion.li
                key={img.id}
                layout
                initial={{ opacity: 0, scale: 0.92 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.92 }}
                className={cn("group relative overflow-hidden rounded-2xl", i === 0 ? "col-span-2 row-span-2 aspect-square" : "aspect-square")}
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side */}
                <img src={img.image} alt="" className="size-full object-cover transition duration-500 group-hover:scale-105" />
                {editable && (
                  <button
                    type="button"
                    aria-label="Rasmni o'chirish"
                    disabled={remove.isPending && remove.variables === img.id}
                    onClick={() => remove.mutate(img.id, { onSuccess: () => toast.success("Rasm o'chirildi"), onError: (e) => toast.error(errorText(e, "O'chirilmadi")) })}
                    className="absolute top-2 right-2 inline-flex size-8 items-center justify-center rounded-full bg-slate-950/70 text-white opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100"
                  >
                    <Trash2Icon className="size-4" />
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
