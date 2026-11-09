import { BadgeCheckIcon } from "lucide-react";

export function PaidBadge({ verified }: { verified?: boolean }) {
  if (!verified) return null;
  return <span className="inline-flex shrink-0 align-middle text-cyan-600 dark:text-cyan-300" title="Faol pulli obuna" role="img" aria-label="Faol pulli obuna"><BadgeCheckIcon className="inline size-5" aria-hidden /></span>;
}
