import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE } from "@/lib/cookies";

/** Optimistic guard only — Django authorizes every API call. */
const PUBLIC = ["/login"];

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hasSession = request.cookies.get(SESSION_COOKIE)?.value === "1";
  const isPublic = PUBLIC.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (!hasSession && !isPublic) {
    const login = new URL("/login", request.url);
    if (pathname !== "/") login.searchParams.set("next", pathname + search);
    return NextResponse.redirect(login);
  }
  return NextResponse.next();
}

export const config = {
  // Everything except the API/media proxies, Next internals and static files.
  matcher: ["/((?!api/|media/|_next/|brand/|icon.png|apple-icon.png|favicon.ico).*)"],
};
