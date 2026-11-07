import type { ApiRole } from "@/lib/api/types";

/** URL slug of each Developer Center role section (`/developer/{slug}`). */
export const ROLE_SLUGS: Record<string, ApiRole> = {
  public: "PUBLIC",
  user: "USER",
  studio: "STUDIO",
  "venue-owner": "VENUE_OWNER",
  admin: "ADMIN",
  "super-admin": "SUPER_ADMIN",
};

export const slugOf = (role: ApiRole) => Object.entries(ROLE_SLUGS).find(([, r]) => r === role)?.[0] ?? "";
