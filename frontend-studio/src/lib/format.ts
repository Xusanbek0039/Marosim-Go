import type { AccessStatus, CeremonyStatus, ParticipantType } from "./types";

type Tone = "neutral" | "brand" | "success" | "warning" | "danger";

const pad = (n: number) => String(n).padStart(2, "0");
const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];

export function initials(first?: string, last?: string) {
  return `${first?.[0] ?? ""}${last?.[0] ?? ""}`.toUpperCase() || "?";
}

/** dd.mm.yyyy, hh:mm (local time). */
export function formatDateTime(iso?: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}, ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** "2026-11-21" -> "21 noyabr 2026". Parsed as a calendar date, so no timezone shift. */
export function formatEventDate(value?: string | null) {
  if (!value) return "—";
  const [y, m, d] = value.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return value;
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

/** +998901234567 -> "+998 90 123 45 67"; masked or foreign numbers are shown as given. */
export function formatPhone(e164?: string | null) {
  if (!e164) return "—";
  const m = /^\+998(\d{2})(\d{3})(\d{2})(\d{2})$/.exec(e164);
  return m ? `+998 ${m[1]} ${m[2]} ${m[3]} ${m[4]}` : e164;
}

/** "1500000.00" -> "1 500 000 so'm". */
export function formatMoney(value?: string | number | null) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Math.round(Number(value));
  return `${String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ")} so'm`;
}

export const STATUS_LABELS: Record<CeremonyStatus, string> = {
  DRAFT: "Qoralama",
  UPLOADING: "Yuklanmoqda",
  PROCESSING: "Qayta ishlanmoqda",
  READY: "Tayyor",
  ARCHIVED: "Arxiv",
};

export const STATUS_TONE: Record<CeremonyStatus, Tone> = {
  DRAFT: "neutral",
  UPLOADING: "brand",
  PROCESSING: "brand",
  READY: "success",
  ARCHIVED: "warning",
};

export const PARTICIPANT_LABELS: Record<ParticipantType, string> = {
  BRIDE: "Kelin",
  GROOM: "Kuyov",
  OTHER: "Boshqa",
};

export const ACCESS_LABELS: Record<AccessStatus, string> = {
  INVITED: "Taklif yuborilgan",
  ACTIVE: "Faol",
  DECLINED: "Rad etgan",
  REVOKED: "Bekor qilingan",
};
