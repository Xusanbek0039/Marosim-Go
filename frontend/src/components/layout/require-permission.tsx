"use client";

import { LockIcon } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useMe } from "@/features/auth/hooks";

import { canSee, firstAllowedPath, type NavItem } from "./nav";

/** UI-level guard (the API enforces the same rule server-side). */
export function RequirePermission({ requires, children }: { requires: NavItem["requires"]; children: React.ReactNode }) {
  const { data: me } = useMe();
  if (!me) return null;
  if (canSee(me, { requires })) return <>{children}</>;
  return (
    <div className="glass mx-auto mt-10 flex max-w-md flex-col items-center gap-4 rounded-3xl p-8 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-amber-500/14 text-amber-600 dark:text-amber-300">
        <LockIcon className="size-6" aria-hidden />
      </div>
      <h1 className="text-xl font-extrabold">Ruxsat yo&apos;q</h1>
      <p className="text-sm text-muted-foreground">
        Bu bo&apos;limni ko&apos;rish uchun ruxsatingiz yo&apos;q. Kerak bo&apos;lsa, Super Admin bilan bog&apos;laning.
      </p>
      <Button asChild>
        <Link href={firstAllowedPath(me)}>Ruxsat berilgan bo&apos;limga o&apos;tish</Link>
      </Button>
    </div>
  );
}
