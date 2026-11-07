/**
 * MarosimGo motion tokens — the single source of truth for every animation.
 * Components never hard-code durations/easings; they import from here.
 * Reduced motion is handled globally by <MotionConfig reducedMotion="user">.
 */
import type { TargetAndTransition, Transition, Variants } from "motion/react";

export const duration = {
  instant: 0.08,
  fast: 0.12,
  base: 0.22,
  slow: 0.36,
  counter: 0.9,
} as const;

export const ease = {
  standard: [0.2, 0.8, 0.2, 1] as const,
  emphasized: [0.16, 1, 0.3, 1] as const,
  exit: [0.4, 0, 1, 1] as const,
};

export const spring = {
  sidebar: { type: "spring", stiffness: 320, damping: 32, mass: 0.9 } satisfies Transition,
  pop: { type: "spring", stiffness: 420, damping: 30 } satisfies Transition,
  soft: { type: "spring", stiffness: 220, damping: 26 } satisfies Transition,
};

export const stagger = { list: 0.04, cards: 0.06 } as const;

// ------------------------------------------------------------------ variants
export const pageVariants: Variants = {
  initial: { opacity: 0, y: 10, filter: "blur(4px)" },
  animate: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: duration.slow, ease: ease.emphasized },
  },
};

export const fadeUp: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: duration.slow, ease: ease.emphasized } },
  exit: { opacity: 0, y: -6, transition: { duration: duration.fast, ease: ease.exit } },
};

export const listContainer = (gap: number = stagger.list): Variants => ({
  initial: {},
  animate: { transition: { staggerChildren: gap } },
});

export const modalVariants: Variants = {
  initial: { opacity: 0, scale: 0.96, y: 8 },
  animate: { opacity: 1, scale: 1, y: 0, transition: spring.pop },
  exit: { opacity: 0, scale: 0.97, y: 4, transition: { duration: duration.fast, ease: ease.exit } },
};

export const overlayVariants: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: duration.base } },
  exit: { opacity: 0, transition: { duration: duration.fast } },
};

export const drawerVariants: Variants = {
  initial: { x: "100%" },
  animate: { x: 0, transition: { duration: duration.slow, ease: ease.emphasized } },
  exit: { x: "100%", transition: { duration: duration.base, ease: ease.exit } },
};

export const fieldErrorVariants: Variants = {
  initial: { opacity: 0, height: 0, y: -4 },
  animate: { opacity: 1, height: "auto", y: 0, transition: { duration: duration.base, ease: ease.standard } },
  exit: { opacity: 0, height: 0, transition: { duration: duration.fast } },
};

/** Horizontal shake used on invalid form submit. */
export const shake: TargetAndTransition = {
  x: [0, -8, 8, -6, 6, -3, 3, 0],
  transition: { duration: 0.42, ease: "easeInOut" },
};

/** Hover lift + glow for glass cards. */
export const cardHover = {
  whileHover: { y: -3, transition: spring.soft },
  whileTap: { scale: 0.985, transition: { duration: duration.instant } },
} as const;

/** Button press feedback. */
export const press = {
  whileTap: { scale: 0.97, transition: { duration: duration.instant } },
} as const;
