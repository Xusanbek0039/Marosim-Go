"use client";

import { animate, useInView, useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";

import { formatNumber } from "@/lib/format";
import { useMotionPreference } from "@/motion/preference";
import { duration } from "@/motion/tokens";

/** Counts up from the previous value to `value` once visible. */
export function AnimatedNumber({ value, className }: { value: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const previous = useRef(0);
  const inView = useInView(ref, { once: true });
  const systemReduced = useReducedMotion();
  const { reduced } = useMotionPreference();

  useEffect(() => {
    const node = ref.current;
    if (!node || !inView) return;
    if (reduced || systemReduced) {
      node.textContent = formatNumber(value);
      previous.current = value;
      return;
    }
    const controls = animate(previous.current, value, {
      duration: duration.counter,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (latest) => {
        node.textContent = formatNumber(latest);
      },
    });
    previous.current = value;
    return () => controls.stop();
  }, [value, inView, reduced, systemReduced]);

  return (
    <span ref={ref} className={className} aria-label={formatNumber(value)}>
      0
    </span>
  );
}
