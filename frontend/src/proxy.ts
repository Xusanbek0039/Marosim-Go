import { NextResponse, type NextRequest } from "next/server";

/**
 * Optimistic route guard only — real authorization is enforced by Django on every API call.
 * `mg_session` is a non-secret marker the backend sets next to the httpOnly JWT cookies.
 */
const SESSION_HINT = "mg_session";

export function proxy(request: NextRequest) {
  const hasSession = request.cookies.get(SESSION_HINT)?.value === "1";
  if (!hasSession) {
    const login = new URL("/login", request.url);
    const next = request.nextUrl.pathname + request.nextUrl.search;
    if (next !== "/") login.searchParams.set("next", next);
    return NextResponse.redirect(login);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/dashboard/:path*", "/users/:path*", "/admins/:path*", "/studios/:path*", "/monitoring/:path*", "/settings/:path*"],
};
