import type { Role } from "./api/types";

const numberFmt = new Intl.NumberFormat("uz-UZ");
const pad = (n: number) => String(n).padStart(2, "0");

/** dd.mm.yyyy — the format used across Uzbekistan (Intl's "uz" locale yields ISO dates). */
export const formatDate = (iso?: string | null) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
};
export const formatDateTime = (iso?: string | null) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${formatDate(iso)}, ${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
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
