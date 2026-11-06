"use client";

import { Loader2Icon, TriangleAlertIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { AlertDialog as AlertPrimitive } from "radix-ui";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { modalVariants, overlayVariants } from "@/motion/tokens";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: React.ReactNode;
  confirmLabel: string;
  tone?: "danger" | "warning" | "default";
  pending?: boolean;
  onConfirm: () => void;
}

const TONES = {
  danger: { icon: "bg-red-500/12 text-red-600 dark:text-red-400", button: "bg-red-600 text-white hover:bg-red-700" },
  warning: {
    icon: "bg-amber-500/14 text-amber-700 dark:text-amber-300",
    button: "bg-amber-700 text-white hover:bg-amber-800",
  },
  default: { icon: "bg-blue-500/12 text-blue-600 dark:text-blue-300", button: "" },
};

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  tone = "danger",
  pending,
  onConfirm,
}: ConfirmDialogProps) {
  const style = TONES[tone];
  return (
    <AlertPrimitive.Root open={open} onOpenChange={(next) => !pending && onOpenChange(next)}>
      <AnimatePresence>
        {open && (
          <AlertPrimitive.Portal forceMount>
            <AlertPrimitive.Overlay asChild forceMount>
              <motion.div
                className="fixed inset-0 z-50 bg-slate-950/45 backdrop-blur-sm"
                variants={overlayVariants}
                initial="initial"
                animate="animate"
                exit="exit"
              />
            </AlertPrimitive.Overlay>
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
              <AlertPrimitive.Content asChild forceMount>
                <motion.div
                  variants={modalVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  className="glass-strong flex w-full max-w-md flex-col gap-4 rounded-3xl p-7 outline-none"
                >
                  <div className={cn("flex size-13 items-center justify-center rounded-2xl", style.icon)}>
                    <TriangleAlertIcon className="size-6" aria-hidden />
                  </div>
                  <AlertPrimitive.Title className="text-xl font-extrabold tracking-tight">{title}</AlertPrimitive.Title>
                  <AlertPrimitive.Description className="text-sm leading-relaxed text-muted-foreground">
                    {description}
                  </AlertPrimitive.Description>
                  <div className="mt-2 flex gap-3">
                    <AlertPrimitive.Cancel asChild>
                      <Button variant="outline" className="h-11 flex-1" disabled={pending}>
                        Bekor qilish
                      </Button>
                    </AlertPrimitive.Cancel>
                    <Button
                      className={cn("h-11 flex-1 shadow-none", style.button)}
                      onClick={onConfirm}
                      disabled={pending}
                    >
                      {pending && <Loader2Icon className="animate-spin" />}
                      {confirmLabel}
                    </Button>
                  </div>
                </motion.div>
              </AlertPrimitive.Content>
            </div>
          </AlertPrimitive.Portal>
        )}
      </AnimatePresence>
    </AlertPrimitive.Root>
  );
}
