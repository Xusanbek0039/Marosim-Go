"use client";

import { ImageUpIcon, Trash2Icon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useId, useMemo, useState } from "react";

import { cn } from "@/lib/utils";
import { fieldErrorVariants } from "@/motion/tokens";

export function Field({
  label,
  error,
  hint,
  children,
  className,
  htmlFor,
}: {
  label: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
  htmlFor?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={htmlFor} className="text-[13px] font-semibold text-foreground/85">
        {label}
      </label>
      {children}
      <AnimatePresence initial={false}>
        {error ? (
          <motion.p
            key="error"
            role="alert"
            variants={fieldErrorVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            className="overflow-hidden text-xs font-medium text-destructive"
          >
            {error}
          </motion.p>
        ) : hint ? (
          <p className="text-xs text-muted-foreground">{hint}</p>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

const MAX_BYTES = 5 * 1024 * 1024;
const ACCEPT = ["image/jpeg", "image/png", "image/webp"];

/**
 * Image picker with instant preview. Client-side checks are for UX only —
 * the server re-validates, decodes and re-encodes every upload.
 */
export function ImageUpload({
  label,
  currentUrl,
  value,
  onChange,
  error,
  rounded = "2xl",
}: {
  label: string;
  currentUrl?: string | null;
  value: File | null | undefined;
  onChange: (file: File | null | undefined) => void;
  error?: string;
  rounded?: "2xl" | "full";
}) {
  const id = useId();
  const [localError, setLocalError] = useState<string>();
  const preview = useMemo(() => (value ? URL.createObjectURL(value) : null), [value]);
  useEffect(() => () => void (preview && URL.revokeObjectURL(preview)), [preview]);

  const shown = value === null ? null : (preview ?? currentUrl ?? null);

  function pick(file?: File) {
    if (!file) return;
    if (!ACCEPT.includes(file.type)) return setLocalError("Faqat JPG, PNG yoki WEBP rasm yuklang.");
    if (file.size > MAX_BYTES) return setLocalError("Rasm hajmi 5 MB dan oshmasligi kerak.");
    setLocalError(undefined);
    onChange(file);
  }

  return (
    <Field label={label} error={localError ?? error} htmlFor={id}>
      <div
        className={cn(
          "flex items-center gap-4 rounded-2xl border-[1.5px] border-dashed border-cyan-500/40 bg-cyan-500/[0.04] p-3.5 transition hover:border-cyan-500/70",
        )}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          pick(e.dataTransfer.files?.[0]);
        }}
      >
        <div
          className={cn(
            "flex size-16 shrink-0 items-center justify-center overflow-hidden bg-cyan-500/12 text-cyan-600 dark:text-cyan-300",
            rounded === "full" ? "rounded-full" : "rounded-2xl",
          )}
        >
          {shown ? (
            // eslint-disable-next-line @next/next/no-img-element -- local blob/media preview
            <img src={shown} alt="" className="size-full object-cover" />
          ) : (
            <ImageUpIcon className="size-6" aria-hidden />
          )}
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <label htmlFor={id} className="cursor-pointer text-sm font-bold hover:text-brand">
            {shown ? "Rasmni almashtirish" : "Rasm tanlash yoki shu yerga tashlash"}
          </label>
          <span className="text-xs text-muted-foreground">JPG, PNG yoki WEBP · maks. 5 MB</span>
          <input
            id={id}
            type="file"
            accept={ACCEPT.join(",")}
            className="sr-only"
            onChange={(e) => {
              pick(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </div>
        {shown && (
          <button
            type="button"
            onClick={() => onChange(value instanceof File ? undefined : null)}
            className="inline-flex size-9 items-center justify-center rounded-xl text-muted-foreground transition hover:bg-red-500/10 hover:text-red-600"
            aria-label="Rasmni olib tashlash"
          >
            <Trash2Icon className="size-4" />
          </button>
        )}
      </div>
    </Field>
  );
}
