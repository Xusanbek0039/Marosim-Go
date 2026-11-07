"use client";

import { MoonIcon, SunIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";
import { flushSync } from "react-dom";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useMotionPreference } from "@/motion/preference";

const useMounted = () =>
  useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

/**
 * Switches theme with a circular "liquid" reveal from the button (View Transitions API),
 * falling back to an instant switch when unsupported or when motion is reduced.
 */
export function useThemeSwitch() {
  const { resolvedTheme, setTheme } = useTheme();
  const { reduced } = useMotionPreference();

  return (next: string, origin?: { x: number; y: number }) => {
    const doc = document as Document & { startViewTransition?: (cb: () => void) => { ready: Promise<void> } };
    if (!doc.startViewTransition || reduced || !origin) {
      setTheme(next);
      return;
    }
    const radius = Math.hypot(
      Math.max(origin.x, window.innerWidth - origin.x),
      Math.max(origin.y, window.innerHeight - origin.y),
    );
    const transition = doc.startViewTransition(() => {
      flushSync(() => setTheme(next));
    });
    transition.ready.then(() => {
      document.documentElement.animate(
        { clipPath: [`circle(0px at ${origin.x}px ${origin.y}px)`, `circle(${radius}px at ${origin.x}px ${origin.y}px)`] },
        { duration: 520, easing: "cubic-bezier(0.16, 1, 0.3, 1)", pseudoElement: "::view-transition-new(root)" },
      );
    });
    return resolvedTheme;
  };
}

export function ThemeToggle() {
  const { resolvedTheme } = useTheme();
  const mounted = useMounted();
  const switchTheme = useThemeSwitch();
  const isDark = mounted ? resolvedTheme === "dark" : true;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          aria-label={isDark ? "Yorug' rejimga o'tish" : "Qorong'i rejimga o'tish"}
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            switchTheme(isDark ? "light" : "dark", { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 });
          }}
          className="overflow-hidden"
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={isDark ? "moon" : "sun"}
              initial={{ y: 14, rotate: -60, opacity: 0 }}
              animate={{ y: 0, rotate: 0, opacity: 1 }}
              exit={{ y: -14, rotate: 60, opacity: 0 }}
              transition={{ duration: 0.22 }}
              className="inline-flex"
            >
              {isDark ? <MoonIcon className="size-[18px]" /> : <SunIcon className="size-[18px]" />}
            </motion.span>
          </AnimatePresence>
        </Button>
      </TooltipTrigger>
      <TooltipContent>{isDark ? "Yorug' rejim" : "Qorong'i rejim"}</TooltipContent>
    </Tooltip>
  );
}
