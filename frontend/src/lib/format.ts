import type { Role } from "./api/types";

const dateFmt = new Intl.DateTimeFormat("uz-UZ", { day: "2-digit", month: "2-digit", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("uz-UZ", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});
const numberFmt = new Intl.NumberFormat("uz-UZ");

export const formatDate = (iso?: string | null) => (iso ? dateFmt.format(new Date(iso)) : "—");
export const formatDateTime = (iso?: string | null) => (iso ? dateTimeFmt.format(new Date(iso)) : "—");
export const formatNumber = (n: number) => numberFmt.format(Math.round(n));

export const ROLE_LABELS: Record<Role, string> = {
  SUPER_ADMIN: "Super Admin",
  ADMIN: "Admin",
  STUDIO: "Studiya",
  USER: "Foydalanuvchi",
};

export function initials(first?: string, last?: string) {
  return `${first?.[0] ?? ""}${last?.[0] ?? ""}`.toUpperCase() || "?";
}

/** Deterministic avatar gradient per id. */
const GRADIENTS = [
  "from-blue-600 to-cyan-500",
  "from-indigo-600 to-blue-500",
  "from-cyan-600 to-teal-500",
  "from-sky-600 to-indigo-500",
  "from-blue-700 to-sky-500",
  "from-teal-600 to-cyan-400",
];
export function avatarGradient(id: string) {
  let hash = 0;
  for (const ch of id) hash = (hash * 31 + ch.charCodeAt(0)) | 0;
  return GRADIENTS[Math.abs(hash) % GRADIENTS.length];
}
