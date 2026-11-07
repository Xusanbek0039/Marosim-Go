"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";

import { Shell } from "@/components/shell";
import { Skeleton } from "@/components/ui";
import { APP } from "@/lib/app-config";
import { useLogout, useMe } from "@/lib/auth";

/** UI-level role gate (Django enforces the real rule on every call). */
function RoleGate({ children }: { children: React.ReactNode }) {
  const { data: me, isPending } = useMe();
  const logout = useLogout();
  const router = useRouter();
  const wrongRole = me && me.role !== APP.role;

  useEffect(() => {
    if (!wrongRole) return;
    toast.error(APP.wrongAppMessage);
    logout.mutate(undefined, { onSettled: () => router.replace("/login") });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once per wrong-role detection
  }, [wrongRole]);

  if (isPending || wrongRole) {
    return (
      <div className="flex flex-col gap-4" aria-busy="true">
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-40 w-full rounded-3xl" />
        <Skeleton className="h-40 w-full rounded-3xl" />
      </div>
    );
  }
  return <>{children}</>;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <Shell nav={[...APP.nav]}>
      <RoleGate>{children}</RoleGate>
    </Shell>
  );
}
