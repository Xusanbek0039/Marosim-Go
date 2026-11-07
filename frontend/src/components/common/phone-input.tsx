"use client";

import { forwardRef } from "react";

import { PHONE_PREFIX, toUzE164 } from "@/lib/phone";
import { cn } from "@/lib/utils";

/** "+998901234567" → "90 123 45 67" (partial input formats as it is typed). */
function display(value: string) {
  const d = toUzE164(value).slice(PHONE_PREFIX.length);
  return [d.slice(0, 2), d.slice(2, 5), d.slice(5, 7), d.slice(7, 9)].filter(Boolean).join(" ");
}

type Props = Omit<React.ComponentProps<"input">, "value" | "onChange" | "type"> & {
  value: string;
  /** Always "+998XXXXXXXXX" (possibly incomplete) or "" when empty. */
  onChange: (value: string) => void;
};

/** Uzbek-only phone field: the "+998" prefix is fixed, only the 9 local digits are typed. */
export const PhoneInput = forwardRef<HTMLInputElement, Props>(function PhoneInput({ value, onChange, className, ...props }, ref) {
  return (
    <div
      className={cn(
        "flex h-11 w-full items-center overflow-hidden rounded-xl border border-input bg-white/60 transition-colors focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/20 has-[input[aria-invalid=true]]:border-destructive dark:bg-slate-950/40 dark:focus-within:border-cyan-400/70",
        className,
      )}
    >
      <span className="flex h-full items-center border-r border-input bg-muted/60 px-3 text-sm font-semibold text-muted-foreground tabular-nums select-none" aria-hidden>
        {PHONE_PREFIX}
      </span>
      <input
        ref={ref}
        type="tel"
        inputMode="numeric"
        autoComplete="tel-national"
        placeholder="90 123 45 67"
        value={display(value)}
        onChange={(e) => onChange(toUzE164(e.target.value))}
        className="h-full min-w-0 flex-1 bg-transparent px-3 text-base tabular-nums outline-none placeholder:text-muted-foreground md:text-sm"
        {...props}
      />
    </div>
  );
});
