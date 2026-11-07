import type { ApiRole, EndpointDoc } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/** Display order of the role classification (most open first) — mirrors the backend ROLE_ORDER. */
export const API_ROLES: ApiRole[] = ["PUBLIC", "USER", "STUDIO", "ADMIN", "SUPER_ADMIN"];

export const ROLE_LABELS: Record<ApiRole, string> = {
  PUBLIC: "Public",
  USER: "User",
  STUDIO: "Studio",
  ADMIN: "Admin",
  SUPER_ADMIN: "Super Admin",
};

const ROLE_SHORT: Record<ApiRole, string> = { PUBLIC: "PUB", USER: "USER", STUDIO: "STUDIO", ADMIN: "ADMIN", SUPER_ADMIN: "SA" };

const ROLE_STYLES: Record<ApiRole, string> = {
  PUBLIC: "border-emerald-400/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  USER: "border-sky-400/40 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  STUDIO: "border-cyan-400/40 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300",
  ADMIN: "border-blue-400/40 bg-blue-500/10 text-blue-700 dark:text-blue-300",
  SUPER_ADMIN: "border-violet-400/40 bg-violet-500/10 text-violet-700 dark:text-violet-300",
};

export function RoleBadge({ role, compact, className }: { role: ApiRole; compact?: boolean; className?: string }) {
  return (
    <span
      title={ROLE_LABELS[role]}
      className={cn(
        "inline-flex items-center rounded-md border font-semibold whitespace-nowrap",
        compact ? "px-1 text-[9px] leading-4" : "px-1.5 py-0.5 text-[11px]",
        ROLE_STYLES[role],
        className,
      )}
    >
      {compact ? ROLE_SHORT[role] : ROLE_LABELS[role]}
    </span>
  );
}

export const CONTRACT_LABELS: Record<EndpointDoc["contract_status"], string> = {
  MATCHES_CONTRACT: "Kontraktga mos",
  NOT_IN_CONTRACT: "Kontraktda yo'q",
  CONTRACT_MISMATCH: "Kontraktdan farq qiladi",
  REVIEW_REQUIRED: "Tekshirish talab qilinadi",
};

/** Problems with the *documentation / contract* of an endpoint — separate from its runtime health. */
export function endpointWarnings(e: EndpointDoc): string[] {
  return [
    e.access_status === "REVIEW_REQUIRED" && "REVIEW REQUIRED — ruxsat avtomatik aniqlanmadi",
    e.documentation_status === "MISSING" && `Documentation Missing: ${e.documentation_missing.join(", ")}`,
    e.contract_status !== "MATCHES_CONTRACT" && CONTRACT_LABELS[e.contract_status],
    e.deprecated && "Deprecated",
  ].filter(Boolean) as string[];
}
