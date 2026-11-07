"use client";

import { cn } from "./ui";

/** Only Uzbek numbers: the "+998" prefix is fixed, the user types the 9 local digits. */
export const PHONE_PREFIX = "+998";

/** Any typed form ("90 123 45 67", "998901234567", "+998 (90) 123-45-67") → "+998901234567" or "". */
export function toUzE164(raw: string): string {
  const text = raw.trim();
  // Already ours ("+998…", possibly incomplete): never prefix twice.
  let digits = (text.startsWith(PHONE_PREFIX) ? text.slice(PHONE_PREFIX.length) : text).replace(/\D/g, "");
  // A full international number pasted without "+": 998 + 9 digits. (A 9-digit local number may itself
  // start with "99 8…" — operator 99 — so only a 12-digit value is treated as international.)
  if (!text.startsWith(PHONE_PREFIX) && digits.length >= 12 && digits.startsWith("998")) digits = digits.slice(3);
  return digits ? `${PHONE_PREFIX}${digits.slice(0, 9)}` : "";
}

export const isUzPhone = (value: string) => /^\+998\d{9}$/.test(value);

function display(value: string) {
  const d = toUzE164(value).slice(PHONE_PREFIX.length); // value is already "+998…": no double prefix
  return [d.slice(0, 2), d.slice(2, 5), d.slice(5, 7), d.slice(7, 9)].filter(Boolean).join(" ");
}

export function PhoneInput({
  value,
  onChange,
  className,
  ...props
}: Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "type"> & {
  value: string;
  /** Always "+998XXXXXXXXX" (possibly incomplete) or "". */
  onChange: (value: string) => void;
}) {
  return (
    <div
      className={cn(
        "flex h-11 w-full items-center overflow-hidden rounded-xl border border-input bg-white/60 transition focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/20 has-[input[aria-invalid=true]]:border-danger dark:bg-slate-950/40",
        className,
      )}
    >
      <span className="flex h-full items-center border-r border-input bg-muted px-3 text-sm font-semibold text-muted-foreground tabular-nums select-none" aria-hidden>
        {PHONE_PREFIX}
      </span>
      <input
        type="tel"
        inputMode="numeric"
        placeholder="90 123 45 67"
        value={display(value)}
        onChange={(e) => onChange(toUzE164(e.target.value))}
        className="h-full min-w-0 flex-1 bg-transparent px-3 text-sm tabular-nums outline-none placeholder:text-muted-foreground"
        {...props}
      />
    </div>
  );
}
