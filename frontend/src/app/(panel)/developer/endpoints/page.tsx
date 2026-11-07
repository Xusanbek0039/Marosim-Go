"use client";

import { DevPage, RoleEndpoints } from "@/features/devcenter/views";

export default function AllEndpointsPage() {
  return (
    <DevPage title="All Endpoints">
      <RoleEndpoints />
    </DevPage>
  );
}
