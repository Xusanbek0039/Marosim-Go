import "server-only";

import type { NextRequest } from "next/server";

/**
 * Streams a request to the Django backend and the response back, unchanged.
 * Keeps auth cookies first-party (same origin as the panel) and preserves
 * trailing slashes, multipart bodies and multiple Set-Cookie headers.
 */
const BACKEND_URL = (process.env.BACKEND_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

/** Upload ceiling enforced before anything reaches Django (backend allows 6 MB). */
const MAX_BODY_BYTES = 8 * 1024 * 1024;
/** Portfolio reels (vertical videos): backend `STUDIO_REEL_MAX_MB` = 100, plus multipart overhead. */
const MAX_REEL_BODY_BYTES = 110 * 1024 * 1024;
const REEL_UPLOAD = /^\/api\/v1\/studios\/me\/[0-9a-f-]{36}\/reels\/$/i;

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

export async function forwardToBackend(request: NextRequest): Promise<Response> {
  const { pathname, search } = request.nextUrl;
  const target = `${BACKEND_URL}${pathname}${search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });
  const forwardedFor = request.headers.get("x-forwarded-for");
  headers.set("x-forwarded-for", forwardedFor ?? "127.0.0.1");
  headers.set("x-forwarded-proto", request.nextUrl.protocol.replace(":", ""));
  headers.set("x-forwarded-host", request.headers.get("host") ?? "");

  // WSGI servers need a Content-Length, so the (size-capped) body is buffered, not streamed.
  let body: ArrayBuffer | undefined;
  if (!["GET", "HEAD"].includes(request.method)) {
    const limit = REEL_UPLOAD.test(pathname) ? MAX_REEL_BODY_BYTES : MAX_BODY_BYTES;
    const declared = Number(request.headers.get("content-length") ?? 0);
    if (declared > limit) return tooLarge();
    body = await request.arrayBuffer();
    if (body.byteLength > limit) return tooLarge();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    return Response.json(
      { error: { code: "backend_unavailable", message: "Server vaqtincha mavjud emas.", details: null } },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    // fetch already decoded the body, so the original encoding/length no longer apply
    if (lower === "set-cookie" || lower === "content-encoding" || lower === "content-length") return;
    if (!HOP_BY_HOP.has(lower)) responseHeaders.set(key, value);
  });
  for (const cookie of upstream.headers.getSetCookie()) {
    responseHeaders.append("set-cookie", cookie);
  }

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

function tooLarge() {
  return Response.json(
    { error: { code: "payload_too_large", message: "Yuborilayotgan fayl juda katta.", details: null } },
    { status: 413 },
  );
}
