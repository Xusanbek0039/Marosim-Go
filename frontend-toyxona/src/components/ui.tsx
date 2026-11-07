"use client";

import { AlertTriangleIcon, InboxIcon, Loader2Icon, RotateCwIcon, XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect } from "react";
import { createPortal } from "react-dom";

import { ApiError } from "@/lib/api";
import { initials } from "@/lib/format";

export const cn = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(" ");

const ease = [0.16, 1, 0.3, 1] as const;
export const fadeUp = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease } },
};

// ----------------------------------------------------------------- button
type Variant = "primary" | "outline" | "ghost" | "danger";
const VARIANTS: Record<Variant, string> = {
  primary:
    "brand-gradient text-white shadow-[0_10px_24px_-12px_rgb(37_99_235/0.85)] hover:brightness-110 disabled:opacity-60",
  outline: "glass hover:bg-muted disabled:opacity-50",
  ghost: "hover:bg-muted disabled:opacity-50",
  danger: "bg-red-500/10 text-danger hover:bg-red-500/20 disabled:opacity-50",
};

export function Button({
  variant = "primary",
  size = "md",
  loading,
  className,
  children,
  disabled,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" | "lg"; loading?: boolean }) {
  return (
    <button
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-semibold whitespace-nowrap outline-none transition active:scale-[0.98] focus-visible:ring-4 focus-visible:ring-brand/30 [&_svg]:size-4",
        size === "sm" ? "h-9 px-3 text-[13px]" : size === "lg" ? "h-12 px-5 text-[15px]" : "h-10 px-4 text-sm",
        VARIANTS[variant],
        className,
      )}
      {...props}
    >
      {loading && <Loader2Icon className="animate-spin" />}
      {children}
    </button>
  );
}

// ------------------------------------------------------------------- form
export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-xl border border-input bg-white/60 px-3.5 text-sm outline-none transition placeholder:text-muted-foreground focus-visible:border-brand focus-visible:ring-4 focus-visible:ring-brand/20 aria-invalid:border-danger dark:bg-slate-950/40",
        className,
      )}
      {...props}
    />
  );
}

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-24 w-full rounded-xl border border-input bg-white/60 px-3.5 py-2.5 text-sm outline-none transition placeholder:text-muted-foreground focus-visible:border-brand focus-visible:ring-4 focus-visible:ring-brand/20 dark:bg-slate-950/40",
        className,
      )}
      {...props}
    />
  );
}

export function Select({ className, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-11 w-full rounded-xl border border-input bg-white/60 px-3 text-sm outline-none focus-visible:border-brand focus-visible:ring-4 focus-visible:ring-brand/20 dark:bg-slate-950/40",
        className,
      )}
      {...props}
    />
  );
}

export function Field({
  label,
  htmlFor,
  error,
  hint,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-[13px] font-semibold text-foreground/85">
        {label}
      </label>
      {children}
      {error ? (
        <p role="alert" className="text-xs font-medium text-danger">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}

// ----------------------------------------------------------------- surface
export function Card({ className, children, ...props }: React.ComponentProps<typeof motion.div>) {
  return (
    <motion.div variants={fadeUp} initial="initial" animate="animate" className={cn("glass rounded-3xl p-5 sm:p-6", className)} {...props}>
      {children}
    </motion.div>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: "neutral" | "brand" | "success" | "warning" | "danger"; children: React.ReactNode }) {
  const tones = {
    neutral: "bg-slate-500/12 text-slate-700 dark:text-slate-300",
    brand: "bg-blue-500/14 text-blue-700 dark:text-blue-300",
    success: "bg-emerald-500/14 text-emerald-700 dark:text-emerald-300",
    warning: "bg-amber-500/14 text-amber-700 dark:text-amber-300",
    danger: "bg-red-500/14 text-red-700 dark:text-red-300",
  };
  return <span className={cn("inline-flex h-6 items-center rounded-full px-2.5 text-xs font-bold", tones[tone])}>{children}</span>;
}

export function Avatar({ first, last, src, className }: { first?: string; last?: string; src?: string | null; className?: string }) {
  return src ? (
    // eslint-disable-next-line @next/next/no-img-element -- proxied media, already re-encoded server-side
    <img src={src} alt="" className={cn("size-10 shrink-0 rounded-full object-cover", className)} />
  ) : (
    <span
      aria-hidden
      className={cn("flex size-10 shrink-0 items-center justify-center rounded-full brand-gradient text-sm font-bold text-white", className)}
    >
      {initials(first, last)}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-muted", className)} />;
}

// ------------------------------------------------------------------ states
export function EmptyState({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <div className="flex size-14 items-center justify-center rounded-3xl bg-gradient-to-br from-blue-500/15 to-cyan-400/15 text-cyan-600 dark:text-cyan-300">
        <InboxIcon className="size-6" aria-hidden />
      </div>
      <h3 className="text-base font-bold">{title}</h3>
      {description && <p className="max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof ApiError ? error.message : "Ma'lumotlarni yuklab bo'lmadi.";
  return (
    <div role="alert" className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <div className="flex size-14 items-center justify-center rounded-3xl bg-red-500/12 text-danger">
        <AlertTriangleIcon className="size-6" aria-hidden />
      </div>
      <p className="max-w-sm text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCwIcon /> Qayta urinish
        </Button>
      )}
    </div>
  );
}

// ------------------------------------------------------------------- modal
export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Portal to <body>: a Card's transform / backdrop-filter becomes the containing block of
  // position:fixed descendants, which would trap the overlay inside the card.
  if (typeof document === "undefined") return null;
  return createPortal(
      <AnimatePresence>
        {open && (
          <motion.div
            className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 p-0 backdrop-blur-sm sm:items-center sm:p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onMouseDown={(e) => e.target === e.currentTarget && onClose()}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label={title}
              className="glass-strong max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-t-3xl p-6 sm:rounded-3xl"
              initial={{ y: 40, opacity: 0, scale: 0.98 }}
              animate={{ y: 0, opacity: 1, scale: 1, transition: { type: "spring", stiffness: 380, damping: 32 } }}
              exit={{ y: 24, opacity: 0, transition: { duration: 0.15 } }}
            >
              <div className="mb-5 flex items-center justify-between gap-3">
                <h2 className="text-lg font-bold">{title}</h2>
                <button type="button" onClick={onClose} aria-label="Yopish" className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted">
                  <XIcon className="size-5" />
                </button>
              </div>
              {children}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>,
    document.body,
  );
}
