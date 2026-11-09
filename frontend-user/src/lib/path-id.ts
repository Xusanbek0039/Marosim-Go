"use client";

import { useParams, usePathname } from "next/navigation";

/**
 * The static export (served by Django) has one page per dynamic route, exported under the
 * placeholder id "_": the real id then comes from the browser URL (``/<section>/<id>``).
 */
export function usePathId(): string {
  const { id } = useParams<{ id: string }>();
  const pathname = usePathname();
  if (id && id !== "_") return id;
  const fromUrl = pathname.split("/")[2] ?? "";
  return fromUrl === "_" ? "" : decodeURIComponent(fromUrl);
}
