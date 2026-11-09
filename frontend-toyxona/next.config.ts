import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV !== "production";

/**
 * PANEL_EXPORT=1 (`npm run build:panel`): a static export that Django serves itself on
 * toyxona.marosimgo.uz — one cPanel deploy with the API, same origin, no Node.js. Django then answers
 * /api/v1 and /media directly, so the proxy route handlers and proxy.ts are left out of the build
 * (only .tsx files count as pages) and Django sends the security headers (backend/config/panel.py).
 * Otherwise (dev / a Node host) the route handlers proxy /api/v1 and /media to BACKEND_URL.
 */
const isExport = process.env.PANEL_EXPORT === "1";

// Same-origin only: /api/v1 and /media are proxied to Django server-side.
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
  ...(isExport ? { output: "export" as const, images: { unoptimized: true }, pageExtensions: ["tsx"] } : {}),
  // Django URLs end with "/": never let Next strip it before proxying.
  skipTrailingSlashRedirect: true,
  poweredByHeader: false,
  turbopack: {
    rules: { "*.css": { loaders: ["@tailwindcss/turbopack"], as: "*.css" } },
  },
  ...(isExport ? {} : { headers }),
};

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
