"use client";

import { motion } from "motion/react";

import { Logo, ThemeToggle } from "./shell";

export function AuthFrame({ subtitle, children }: { subtitle: string; children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-dvh items-center justify-center p-4">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } }}
        className="glass-strong w-full max-w-[420px] rounded-[28px] p-7 shadow-[0_0_80px_-30px_rgb(6_182_212/0.55)] sm:p-8"
      >
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <Logo />
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        {children}
      </motion.div>
    </div>
  );
}
