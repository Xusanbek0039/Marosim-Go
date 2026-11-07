"use client";

import { XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { Dialog as DialogPrimitive } from "radix-ui";

import { cn } from "@/lib/utils";
import { drawerVariants, modalVariants, overlayVariants } from "@/motion/tokens";

interface BaseProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

function Overlay() {
  return (
    <DialogPrimitive.Overlay asChild forceMount>
      <motion.div
        className="fixed inset-0 z-50 bg-slate-950/45 backdrop-blur-sm"
        variants={overlayVariants}
        initial="initial"
        animate="animate"
        exit="exit"
      />
    </DialogPrimitive.Overlay>
  );
}

function CloseButton() {
  return (
    <DialogPrimitive.Close
      className="absolute top-4 right-4 inline-flex size-9 items-center justify-center rounded-xl border border-glass-border text-muted-foreground transition hover:bg-muted hover:text-foreground focus-visible:ring-4 focus-visible:ring-brand/25 focus-visible:outline-none"
      aria-label="Yopish"
    >
      <XIcon className="size-4" />
    </DialogPrimitive.Close>
  );
}

/** Centered glass modal with scale/fade entrance and exit. */
export function MotionDialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  className,
  size = "md",
}: BaseProps & { size?: "sm" | "md" | "lg" }) {
  const width = { sm: "max-w-md", md: "max-w-xl", lg: "max-w-3xl" }[size];
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <DialogPrimitive.Portal forceMount>
            <Overlay />
            <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:items-center">
              <DialogPrimitive.Content asChild forceMount>
                <motion.div
                  variants={modalVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  className={cn(
                    "glass-strong relative my-auto flex w-full flex-col gap-5 rounded-3xl p-6 shadow-[0_0_80px_-30px_rgb(6_182_212/0.5)] outline-none sm:p-7",
                    width,
                    className,
                  )}
                >
                  <div className="flex flex-col gap-1.5 pr-10">
                    <DialogPrimitive.Title className="text-xl font-extrabold tracking-tight">{title}</DialogPrimitive.Title>
                    {description ? (
                      <DialogPrimitive.Description className="text-sm text-muted-foreground">
                        {description}
                      </DialogPrimitive.Description>
                    ) : (
                      <DialogPrimitive.Description className="sr-only">{String(title)}</DialogPrimitive.Description>
                    )}
                  </div>
                  {children}
                  {footer}
                  <CloseButton />
                </motion.div>
              </DialogPrimitive.Content>
            </div>
          </DialogPrimitive.Portal>
        )}
      </AnimatePresence>
    </DialogPrimitive.Root>
  );
}

/** Right-side glass drawer for detail views. */
export function MotionDrawer({ open, onOpenChange, title, description, children, footer, className }: BaseProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <DialogPrimitive.Portal forceMount>
            <Overlay />
            <DialogPrimitive.Content asChild forceMount>
              <motion.aside
                variants={drawerVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                className={cn(
                  "glass-strong fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col gap-6 overflow-y-auto rounded-l-3xl border-l border-cyan-400/20 p-6 outline-none sm:p-7",
                  className,
                )}
              >
                <div className="flex flex-col gap-1 pr-10">
                  <DialogPrimitive.Title className="text-xs font-bold tracking-[0.14em] text-cyan-600 uppercase dark:text-cyan-300">
                    {title}
                  </DialogPrimitive.Title>
                  <DialogPrimitive.Description className={description ? "text-sm text-muted-foreground" : "sr-only"}>
                    {description ?? String(title)}
                  </DialogPrimitive.Description>
                </div>
                {children}
                {footer ? <div className="mt-auto flex gap-3 pt-2">{footer}</div> : null}
                <CloseButton />
              </motion.aside>
            </DialogPrimitive.Content>
          </DialogPrimitive.Portal>
        )}
      </AnimatePresence>
    </DialogPrimitive.Root>
  );
}
