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

## V4.1 — Marosim egaligi, takliflar va shaxsiy media ([CEREMONY_OWNERSHIP.md](CEREMONY_OWNERSHIP.md))

| # | Bosqich | Holat |
|---|---|---|
| A | Mavjud loyiha auditi va DB munosabatlari dizayni | ✅ 2026-11-07 |
| B | Ownership modellari (`CeremonyInvitation`, `CeremonyOwnership`, `CeremonyOwnershipApproval`, `CeremonyViewerAccess`), migratsiyalar + v1 backfill, ruxsat qatlami (`ownership.py`) | ✅ 2026-11-07 |
| C | Xavfsiz taklif tizimi: telefon/JSHSHIR, qabul/rad, egalar tasdig'i, qayta yuborish, muddat, bekor qilish; v1 endpointlarini ko'chirish | ⏳ tasdiq kutilmoqda |
| D | Google Drive media upload (studiya) | ⏳ |
| E | Foydalanuvchi media API: galereya, thumbnail/preview/stream/download — har so'rovda object-level tekshiruv | ⏳ |
| F | Super Admin: marosimlar monitoringi + API Developer Center (CEREMONY_OWNER / CEREMONY_VIEWER guruhlari) | ⏳ |
| G | Xavfsizlik / integratsiya testlari, hujjatlar | ⏳ (B uchun ✅) |

Qarorlar:
* Studiya/foydalanuvchi uchun alohida sodda web ilovalar quriladi — avval backend API (2026-11-07, foydalanuvchi qarori).
* Scope: faqat `drive.file`; kengroq/restricted scope'ga faqat alohida tasdiq bilan.
* V4.1: studiya/foydalanuvchi uchun yangi web frontend yaratilmaydi — faqat mobil REST API (2026-11-07).
* V4.1: spec'dagi `ceremony_type`/`ceremony_date` mavjud `event_type`/`event_date` maydonlari bilan beriladi (API buzilmaydi);
  studiya yo'llari mavjud `/api/v1/ceremonies/…` standartida qoladi (`/studio/ceremonies/` emas).
* V4.1: OWNER huquqi faqat tasdiqlangan telefon bilan (`CEREMONY_OWNER_REQUIRE_VERIFIED_PHONE`, DEBUG'da ham); JSHSHIR — faqat identifikator.
