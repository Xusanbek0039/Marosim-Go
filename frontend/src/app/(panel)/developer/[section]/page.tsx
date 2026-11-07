import { notFound } from "next/navigation";

import { ROLE_SLUGS } from "@/features/devcenter/roles";

import { RoleApis } from "./role-apis";

/** /developer/{public|user|studio|admin|super-admin} — one role's endpoints, straight from the backend. */
export function generateStaticParams() {
  return Object.keys(ROLE_SLUGS).map((section) => ({ section }));
}

export default async function RoleApisPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  const role = ROLE_SLUGS[section];
  if (!role) notFound();
  return <RoleApis role={role} />;
}
