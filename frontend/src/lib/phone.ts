import { z } from "zod";

/**
 * Light client-side check only — the API normalizes to E.164 and is the source of truth.
 * Accepts "+998 90 123 45 67", "998901234567" or "901234567".
 */
export const PHONE_HINT = "Masalan: +998 90 123 45 67";

export const phoneSchema = z
  .string()
  .trim()
  .min(1, "Telefon raqamni kiriting")
  .refine((v) => /^\+?[\d\s()-]{9,20}$/.test(v) && digits(v).length >= 9 && digits(v).length <= 12, "Telefon raqam noto'g'ri");

export const optionalPhoneSchema = z
  .string()
  .trim()
  .refine((v) => v === "" || (digits(v).length >= 9 && digits(v).length <= 12), "Telefon raqam noto'g'ri");

function digits(value: string) {
  return value.replace(/\D/g, "");
}
