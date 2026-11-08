import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV !== "production";

/**
 * PANEL_EXPORT=1 (`npm run build:panel`): a static export that Django serves itself at
 * api.marosimgo.uz — one deploy for the API and the Super Admin panel, same origin, no Node.js.
 * Otherwise (dev / a Node host) /api/v1 and /media are proxied to BACKEND_URL by rewrites.
 */
const isExport = process.env.PANEL_EXPORT === "1";
const BACKEND_URL = (process.env.BACKEND_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

// The panel only talks to its own origin, so the browser never needs to reach another host.
// (In the static export Django sends the same policy — see backend/config/panel.py.)
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self'${isDev ? " ws: wss:" : ""}`,
  "frame-ancestors 'none'",
  "form-action 'self'",
  "base-uri 'self'",
  "object-src 'none'",
].join("; ");

const nextConfig: NextConfig = {
  ...(isExport ? { output: "export" as const, images: { unoptimized: true } } : {}),
  // Partial prerendering cannot run in a static export.
  ...(isExport ? {} : { cacheComponents: true, partialPrefetching: true }),
  // Django URLs end with "/": never let Next strip it before proxying.
  skipTrailingSlashRedirect: true,
  poweredByHeader: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  ...(isExport ? {} : { rewrites, headers }),
};

async function rewrites() {
  return [
    { source: "/api/v1/:path*", destination: `${BACKEND_URL}/api/v1/:path*` },
    { source: "/media/:path*", destination: `${BACKEND_URL}/media/:path*` },
  ];
}

async function headers() {
  return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
        ],
      },
    ];
}

export default nextConfig;
