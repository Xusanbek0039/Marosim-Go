# MarosimGo — Roadmap

| # | Bosqich | Holat |
|---|---|---|
| v1 | Super Admin panel: users, admins, studios, RBAC, JSHSHIR himoyasi, audit | ✅ |
| v2 | Telefon orqali auth (mobil API), profil, API Monitoring, health, OpenAPI | ✅ |
| **A** | **Google OAuth Connection** (shaxsiy Gmail, drive.file, shifrlangan refresh token, panel sahifasi) | ✅ 2026-11-07 |
| B | Drive papkalar: root papka (Picker / ilova yaratgan), `Studio_{uuid}/Ceremony_{uuid}/Videos,Photos`, idempotency, reconciliation | ⏳ tasdiq kutilmoqda |
| — | Studios & Ceremonies API (Ceremony, CeremonyParticipant, `/studios/me/`, `/ceremonies/`, takliflar) | ✅ 2026-11-07 |
| C | Media upload: chunked resumable upload, vaqtinchalik disk, background worker (Celery/Redis qarori) | ⏳ |
| D | Super Admin: Storage dashboard statistikasi, Upload Queue | ⏳ |
| E | Test & Security: real Drive integration rejimi, quota/expired/recovery testlari | qisman (A uchun ✅) |
| — | Media access API (`/me/ceremonies/`, stream, Range) | ⏳ |
| — | Studiya (`frontend-studio/`) va foydalanuvchi (`frontend-user/`) web ilovalari — sodda dizayn | ✅ 2026-11-07 (media sahifalari Phase C dan keyin) |

Qarorlar:
* Studiya/foydalanuvchi uchun alohida sodda web ilovalar quriladi — avval backend API (2026-11-07, foydalanuvchi qarori).
* Scope: faqat `drive.file`; kengroq/restricted scope'ga faqat alohida tasdiq bilan.
