"use client";

import { motion } from "motion/react";

import { pageVariants } from "@/motion/tokens";

/** Fade/slide/blur-in for every panel page. */
export function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" className="flex flex-col gap-6">
      {children}
    </motion.div>
  );
}
