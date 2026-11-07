"use client";

import { ROLE_LABELS } from "@/components/devcenter/role-badge";
import { DevPage, RoleEndpoints } from "@/features/devcenter/views";
import type { ApiRole } from "@/lib/api/types";

export function RoleApis({ role }: { role: ApiRole }) {
  return (
    <DevPage title={`${ROLE_LABELS[role]} APIs`}>
      <RoleEndpoints key={role} role={role} />
    </DevPage>
  );
}
