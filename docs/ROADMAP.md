# MarosimGo — Roadmap

| # | Bosqich | Holat |
|---|---|---|
| v1 | Super Admin panel: users, admins, studios, RBAC, JSHSHIR himoyasi, audit | ✅ |
| v2 | Telefon orqali auth (mobil API), profil, API Monitoring, health, OpenAPI | ✅ |
| **A** | **Google OAuth Connection** (shaxsiy Gmail, drive.file, shifrlangan refresh token, panel sahifasi) | ✅ 2026-11-07 |
| B | Drive papkalar: root papka (Picker / ilova yaratgan), `Studio_{uuid}/Ceremony_{uuid}/Videos,Photos`, idempotency, reconciliation | ✅ 2026-11-07 (V4.1-D: ilova yaratgan root + idempotent daraxt; Picker — ochiq) |
| — | Studios & Ceremonies API (Ceremony, CeremonyParticipant, `/studios/me/`, `/ceremonies/`, takliflar) | ✅ 2026-11-07 |
| C | Media upload: chunked resumable upload, vaqtinchalik disk, background worker (Celery/Redis qarori) | ✅ 2026-11-07 (V4.1-D: to'g'ridan-to'g'ri Drive resumable sessiya — disk/worker kerak emas) |
| D | Super Admin: Storage dashboard statistikasi, Upload Queue | ⏳ |
| E | Test & Security: real Drive integration rejimi, quota/expired/recovery testlari | qisman (A uchun ✅) |
| — | Media access API (`/me/ceremonies/`, stream, Range) | ⏳ |
| — | Studiya (`frontend-studio/`) va foydalanuvchi (`frontend-user/`) web ilovalari — sodda dizayn | ✅ 2026-11-07 (media sahifalari Phase C dan keyin) |

## V4.1 — Marosim egaligi, takliflar va shaxsiy media ([CEREMONY_OWNERSHIP.md](CEREMONY_OWNERSHIP.md))

| # | Bosqich | Holat |
|---|---|---|
| A | Mavjud loyiha auditi va DB munosabatlari dizayni | ✅ 2026-11-07 |
| B | Ownership modellari (`CeremonyInvitation`, `CeremonyOwnership`, `CeremonyOwnershipApproval`, `CeremonyViewerAccess`), migratsiyalar + v1 backfill, ruxsat qatlami (`ownership.py`) | ✅ 2026-11-07 |
| C | Xavfsiz taklif tizimi: telefon/JSHSHIR, qabul/rad, egalar tasdig'i, qayta yuborish, muddat, bekor qilish; v1 endpointlarini ko'chirish | ✅ 2026-11-07 |
| D | Google Drive media upload (studiya): resumable sessiya, papka daraxti, yakunda Drive'dan tekshiruv | ✅ 2026-11-07 |
| E | Foydalanuvchi media API (galereya, thumbnail, stream/Range, download — faqat ega), muddatli ulashish (24 soat / 3 kun / 1 hafta / 1 oy, har ega 5 kishigacha), studiya yuklash UI, foydalanuvchi galereyasi | ✅ 2026-11-07 |
| F | Super Admin: marosimlar monitoringi + API Developer Center (CEREMONY_OWNER / CEREMONY_VIEWER guruhlari) | ⏳ |
| G | Xavfsizlik / integratsiya testlari, hujjatlar | ⏳ (B uchun ✅) |

Qarorlar:
* Studiya/foydalanuvchi uchun alohida sodda web ilovalar quriladi — avval backend API (2026-11-07, foydalanuvchi qarori).
* Scope: faqat `drive.file`; kengroq/restricted scope'ga faqat alohida tasdiq bilan.
* V4.1: studiya/foydalanuvchi uchun yangi web frontend yaratilmaydi — faqat mobil REST API (2026-11-07).
* V4.1: spec'dagi `ceremony_type`/`ceremony_date` mavjud `event_type`/`event_date` maydonlari bilan beriladi (API buzilmaydi);
  studiya yo'llari mavjud `/api/v1/ceremonies/…` standartida qoladi (`/studio/ceremonies/` emas).
* V4.1-E: Drive papkasi `Studio_<nom>/Mijoz_****<JSHSHIR oxirgi 4>_<id6>/{Videos,Photos}` (to'liq JSHSHIR hech qachon); har ega 5 tagacha ko'ruvchi; ko'ruvchi faqat ko'radi (2026-11-07, foydalanuvchi qarori).
* V4.1: OWNER huquqi faqat tasdiqlangan telefon bilan (`CEREMONY_OWNER_REQUIRE_VERIFIED_PHONE`, DEBUG'da ham); JSHSHIR — faqat identifikator.

## So'rovlar va yordam (2026-11-09)

| # | Bosqich | Holat |
|---|---|---|
| 1 | Media o'chirish so'rovlari: studiya → Admin/Super Admin tasdig'i, Drive savati, `requests.*` ruxsatlari, "So'rovlar" sahifasi | ✅ 2026-11-09 |
| 2 | Yordam (support) xatlari: Admin, To'yxona, Studiya, User panellari; umumiy navbat; `support.*` ruxsatlari; Super Admin to'liq kuzatuv | ⏳ tasdiq kutilmoqda |

## V5.0 — To'yxona va studiya bandlik tizimi ([VENUE_AVAILABILITY.md](VENUE_AVAILABILITY.md))

| # | Bosqich | Holat |
|---|---|---|
| A | Loyiha auditi va DB arxitekturasi | ✅ 2026-11-07 |
| B | `VENUE_OWNER` roli, `Venue` / `VenueHall` / `VenueImage` / `VenueMembership`, ruxsat qatlami, `/venue-owner/venues/` (+halls, members) | ✅ 2026-11-07 |
| B+ | PostgreSQL 17 (dev), `frontend-toyxona/` kabineti (to'yxonalar, zallar, jamoa, jadval to'ri) | ✅ 2026-11-07 |
| C | Umumiy scheduling engine (Resource, CalendarEntry, ish vaqti, exclusion constraint), StudioResource | ⏳ tasdiq kutilmoqda |
| D | Dinamik narx (`VenuePricingRule`, snapshot) | ⏳ |
| E | Public visibility, `venue.*` admin ruxsatlari, approval oqimi | ⏳ |
| F | Sana bo'yicha qidiruv (venue + studiya) + `frontend-user`: qidiruv, to'yxona/studiya sahifasi, online kalkulyator | ⏳ |
| G | Bron so'rovlari, hold muddati, concurrency himoyasi | ⏳ |
| H | Super Admin UI (kalendarlar, bronlar, narxlar, approval) | ⏳ |
| I | API Developer Center (VENUE_OWNER bo'limi) va to'liq testlar | ⏳ |

Qarorlar (V5.0):
* `User.role` = hisob turi (rol darvozasi); to'yxona ichidagi huquqlar — `VenueMembership` imkoniyatlari (2026-11-07).
* Bandlik zal (`VenueHall`) / studiya resursi darajasida; har bir venue standart zal bilan yaratiladi.
* Studiya URL'lari mavjud standartda: `/studios/me/calendar/` (spec'dagi `/studio/calendar/` o'rniga).
* Pul — `Decimal(14,2)`, faqat UZS, API'da string.
* Studiya va to'yxona uchun alohida hisoblar; PostgreSQL Phase C'dan oldin o'rnatiladi; a'zolar endpointi qo'shildi (2026-11-07, foydalanuvchi qarori).
* APPROVED to'yxonaning ommaviy profili o'zgarsa — qayta PENDING_APPROVAL (Phase E, 2026-11-07, foydalanuvchi qarori).
* To'yxonachi uchun alohida web kabinet `frontend-toyxona/` (oldingi "faqat mobil API" qarori o'rniga); foydalanuvchiga qidiruv + kalkulyator `frontend-user/` da (2026-11-07 kech, foydalanuvchi qarori).
* Dev DB — lokal PostgreSQL 17 (`marosimgo`), SQLite faqat zaxira / testlar uchun.
