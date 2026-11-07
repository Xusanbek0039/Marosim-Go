"use client";

import { useReducedMotion } from "motion/react";
import { createContext, useCallback, useContext, useMemo, useSyncExternalStore } from "react";

/**
 * Reduced motion = OS setting OR the in-app switch (Settings page).
 * The in-app choice is a harmless UI preference, so localStorage is fine here.
 */
const KEY = "mg:reduce-motion";
const listeners = new Set<() => void>();

function read(): boolean {
  try {
    return window.localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

interface MotionPreference {
  /** Effective value: true when animations should be minimised. */
  reduced: boolean;
  /** The user's in-app choice. */
  userReduced: boolean;
  setUserReduced: (value: boolean) => void;
}

const Ctx = createContext<MotionPreference>({ reduced: false, userReduced: false, setUserReduced: () => {} });

export function MotionPreferenceProvider({ children }: { children: React.ReactNode }) {
  const system = useReducedMotion() ?? false;
  const userReduced = useSyncExternalStore(subscribe, read, () => false);

  const setUserReduced = useCallback((value: boolean) => {
    try {
      window.localStorage.setItem(KEY, value ? "1" : "0");
    } catch {
      /* storage blocked: preference just won't persist */
    }
    listeners.forEach((l) => l());
  }, []);

  const value = useMemo(
    () => ({ reduced: system || userReduced, userReduced, setUserReduced }),
    [system, userReduced, setUserReduced],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useMotionPreference = () => useContext(Ctx);
