"use client";

import { useState } from "react";

import { Modal } from "./ui";

/** Portfolio / gallery grid of a public business; a tap opens the photo large. */
export function PhotoGrid({ images, title }: { images: { id: string; image: string }[]; title: string }) {
  const [open, setOpen] = useState<string | null>(null);
  if (images.length === 0) return null;
  return (
    <>
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {images.map((img, i) => (
          <li key={img.id} className={i === 0 ? "col-span-2 row-span-2" : undefined}>
            <button type="button" onClick={() => setOpen(img.image)} className="block size-full overflow-hidden rounded-2xl" aria-label={`${i + 1}-rasmni ochish`}>
              {/* eslint-disable-next-line @next/next/no-img-element -- proxied media, re-encoded server-side */}
              <img src={img.image} alt="" className="aspect-[4/3] size-full object-cover transition duration-500 hover:scale-105" />
            </button>
          </li>
        ))}
      </ul>
      <Modal open={Boolean(open)} onClose={() => setOpen(null)} title={title}>
        {/* eslint-disable-next-line @next/next/no-img-element -- proxied media */}
        {open && <img src={open} alt="" className="w-full rounded-2xl object-contain" />}
      </Modal>
    </>
  );
}
