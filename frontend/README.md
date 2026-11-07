# MarosimGo — Super Admin web panel

Next.js 16 (App Router) client for the Django API. Setup, commands and architecture: see the
[root README](../README.md) and [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

| Path | What |
|---|---|
| `src/app/(panel)/*` | Dashboard, Foydalanuvchilar, Adminlar, Studiyalar, Sozlamalar |
| `src/app/api/v1/[...path]`, `src/app/media/[...path]` | Same-origin proxy to Django (`BACKEND_URL`) |
| `src/proxy.ts` | Optimistic route guard (real checks are server-side in Django) |
| `src/lib/api/` | Typed fetch client: CSRF, single-flight token refresh, unified errors |
| `src/features/` | TanStack Query hooks + feature components (people, studios) |
| `src/motion/tokens.ts` | The single motion token system (durations, easings, springs, variants) |
| `src/components/motion/` | Animated modal, drawer, confirm dialog, counters, page transition |
