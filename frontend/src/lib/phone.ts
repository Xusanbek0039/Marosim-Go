import { z } from "zod";

/**
 * Only Uzbek numbers: +998 followed by 9 digits (the backend accepts the UZ region only and is
 * the source of truth). Inputs use <PhoneInput>, which fixes the "+998" prefix.
 */
export const PHONE_PREFIX = "+998";
export const PHONE_HINT = "Faqat O'zbekiston raqami: +998 90 123 45 67";
const E164_UZ = /^\+998\d{9}$/;

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

export const phoneSchema = z
  .string()
  .trim()
  .min(1, "Telefon raqamni kiriting")
  .transform(toUzE164)
  .refine((v) => E164_UZ.test(v), "Raqam +998 dan keyin 9 ta raqamdan iborat bo'lishi kerak");

export const optionalPhoneSchema = z
  .string()
  .trim()
  .transform(toUzE164)
  .refine((v) => v === "" || E164_UZ.test(v), "Raqam +998 dan keyin 9 ta raqamdan iborat bo'lishi kerak");
