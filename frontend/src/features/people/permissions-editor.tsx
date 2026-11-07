"use client";

import { CheckIcon } from "lucide-react";
import { motion } from "motion/react";

import { Skeleton } from "@/components/ui/skeleton";
import { usePermissionCatalog } from "@/features/resources";
import type { PermissionCode, PermissionDef } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { spring } from "@/motion/tokens";

function group(catalog: PermissionDef[]) {
  const map = new Map<string, { label: string; items: PermissionDef[] }>();
  for (const p of catalog) {
    const entry = map.get(p.module) ?? { label: p.module_label, items: [] };
    entry.items.push(p);
    map.set(p.module, entry);
  }
  return [...map.entries()];
}

/** Grouped permission toggles for an ADMIN account (Super Admin only). */
export function PermissionsEditor({
  value,
  onChange,
}: {
  value: PermissionCode[];
  onChange: (next: PermissionCode[]) => void;
}) {
  const { data: catalog, isPending } = usePermissionCatalog();

  if (isPending || !catalog) {
    return (
      <div className="grid gap-3 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-36 rounded-2xl" />
        ))}
      </div>
    );
  }

  const selected = new Set(value);
  const toggle = (code: PermissionCode) => {
    const next = new Set(selected);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    // "view" is required by every other action of the same module
    const [module, action] = code.split(".");
    if (action !== "view" && next.has(code)) next.add(`${module}.view` as PermissionCode);
    if (action === "view" && !next.has(code)) {
      for (const c of [...next]) if (c.startsWith(`${module}.`)) next.delete(c);
    }
    onChange(catalog.map((p) => p.code).filter((c) => next.has(c)));
  };

  const setModule = (items: PermissionDef[], on: boolean) => {
    const next = new Set(selected);
    for (const p of items) {
      if (on) next.add(p.code);
      else next.delete(p.code);
    }
    onChange(catalog.map((p) => p.code).filter((c) => next.has(c)));
  };

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {group(catalog).map(([module, { label, items }]) => {
        const all = items.every((p) => selected.has(p.code));
        return (
          <fieldset key={module} className="flex flex-col gap-1 rounded-2xl border border-glass-border bg-muted/40 p-3">
            <legend className="sr-only">{label}</legend>
            <div className="flex items-center justify-between px-1 pb-1">
              <span className="text-sm font-bold">{label}</span>
              <button
                type="button"
                onClick={() => setModule(items, !all)}
                className="text-xs font-semibold text-brand hover:underline dark:text-cyan-300"
              >
                {all ? "Hammasini olish" : "Hammasi"}
              </button>
            </div>
            {items.map((p) => {
              const on = selected.has(p.code);
              return (
                <button
                  key={p.code}
                  type="button"
                  role="checkbox"
                  aria-checked={on}
                  onClick={() => toggle(p.code)}
                  className={cn(
                    "flex items-center gap-2.5 rounded-xl px-2 py-2 text-left text-[13px] transition hover:bg-muted",
                    on ? "font-semibold text-foreground" : "text-muted-foreground",
                  )}
                >
                  <span
                    className={cn(
                      "flex size-5 shrink-0 items-center justify-center rounded-md border transition-colors",
                      on ? "border-transparent bg-gradient-to-br from-blue-600 to-cyan-500 text-white" : "border-input",
                    )}
                  >
                    {on && (
                      <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} transition={spring.pop}>
                        <CheckIcon className="size-3.5" strokeWidth={3} />
                      </motion.span>
                    )}
                  </span>
                  {p.label}
                </button>
              );
            })}
          </fieldset>
        );
      })}
    </div>
  );
}
