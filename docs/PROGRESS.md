# Progress

## 2026-11-07 (kech) — Admin panelda To'yxonalar, venues.* ruxsatlari, galereya, +998 telefon, UI tuzatishlari ✅

* **Ruxsatlar:** `venues.view / create / update / delete / publish` — Super Admin adminlarga beradi/oladi (Adminlar → "N ta ruxsat"); har so'rovda qayta tekshiriladi.
* **Admin panel → To'yxonalar** (`/venues`, Studiyalar yonida): ro'yxat (holat, ommaga chiqish, hudud filtrlari), yaratish (egasi — "To'yxona" rolidagi foydalanuvchi), tahrirlash, bloklash, o'chirish, ommaga chiqish holati (`venues.publish`), zallar, galereya, jamoa. API: `/api/v1/admin/venues/…`.
* **Galereya:** 20 tagacha rasm, har biri 5 MB (JPG/PNG/WEBP → WEBP, EXIF yo'q, 1920 px); egasi (`frontend-toyxona` → Rasmlar) va admin paneli; chegara qulf ostida.
* **Telefon:** barcha formalarda `+998` qotirilgan maydon, faqat 9 raqam; backend faqat UZ (o'zgarmagan). Ikki marta prefiks qo'shish xatosi brauzer testida topilib tuzatildi.
* **UI tuzatishlari:** (1) "Yangi foydalanuvchi" oynasi scroll bo'lmasdi — Radix scroll-lock tashqi o'rovchini bloklardi; scroll endi oynaning o'zida. (2) Studiya/foydalanuvchi/to'yxona ilovalaridagi modal va galereya ko'rish oynasi karta ichida "qamalib" qolardi (transform/backdrop-filter) — portal orqali `body`ga. (3) Studiya ro'yxatida har marosimda "Video yuklash" tugmasi (to'g'ridan-to'g'ri yuklash bo'limiga).
* **Tekshiruv:** backend 1384 passed (SQLite + PostgreSQL); 4 ta frontend tsc/eslint/build; ko'rinadigan Chrome'da to'liq ssenariy (admin → ruxsat → to'yxona + galereya; studiya → Drive'ga yuklash; mijoz → galereya va ko'rish oynasi; to'yxona → Rasmlar).
* **Demo hisoblar (dev DB):** `+998900000001…05`, parol `Demo12345!` (Super Admin, Admin, Studiya, To'yxonachi, Mijoz).

## 2026-11-07 (kech) — V4.1 Phase E: studiya yuklash UI, foydalanuvchi galereyasi, muddatli ulashish ✅

* **Studiya** (`frontend-studio`, marosim sahifasi): drag & drop, bir vaqtda 2 fayl, bo'laklab to'g'ridan-to'g'ri Google Drive'ga, progress, bekor qilish, uzilsa davom etish.
* **Drive papkasi:** `Studio_<nom>/Mijoz_****<oxirgi 4>_<id6>/{Videos,Photos}`, to'liq JSHSHIR yozilmaydi.
* **Foydalanuvchi** (`frontend-user`, marosim sahifasi): video/rasm galereyasi, ko'rish oynasi; ega uchun yuklab olish; "Kimlar ko'ra oladi" paneli (telefon/JSHSHIR, 24 soat · 3 kun · 1 hafta · 1 oy, N/5, qolgan vaqt, bekor qilish).
* **Backend:** `/me/ceremonies/{id}/media/` (list, thumbnail, stream, download), `access_duration`, `expires_at`, 5 kishilik chegara, `MEDIA_DOWNLOAD` audit; migratsiyalar `ceremonies/0005`, `audit/0007`.
* **Jonli topilgan bug:** Google yakuniy javobga CORS faqat sessiya brauzer Origin bilan ochilganda qo'yadi → server allowlist'dagi Origin'ni uzatadi.
* **Testlar:** 1251 passed (SQLite va PostgreSQL); ruff, spectacular, tsc, eslint, next build toza; haqiqiy Drive bilan e2e o'tdi.
* **Tekshirilmagan:** UI haqiqiy brauzerda bosib ko'rilmadi (API va Google CORS jonli tekshirildi).

## 2026-11-07 (kech) — V5.0: PostgreSQL + `frontend-toyxona` + frontend kutubxonalari tiklandi ✅

* **PostgreSQL 17** o'rnatildi, `marosimgo` rol/baza, `btree_gist`; dev ma'lumotlari ko'chirildi; `.env` → PG.
* **Bug:** venue sxemasi bazaga bog'liq edi (`PositiveIntegerField` diapazoni) → `MAX_CAPACITY=100 000`, test, kontrakt yangilandi.
* **`frontend-toyxona/`** (3003): to'yxonalar ro'yxati/yaratish, profil, muqova, zallar, jamoa, jadval to'ri (Phase C'da jonlanadi).
* **Tiklandi:** `.gitignore`dagi `lib/` sabab yo'qolgan `frontend-studio/src/lib`, `frontend-user/src/lib`.
* **Testlar:** backend 1186 passed (SQLite) / 1186 passed (PostgreSQL); ruff toza; `spectacular --validate` toza;
  3 ta frontend: `tsc`, `eslint`, `next build` toza.
* **Keyingi:** Phase C (scheduling engine) — tasdiq kutilmoqda. Batafsil: [VENUE_AVAILABILITY.md](VENUE_AVAILABILITY.md).

## 2026-11-07 — V4.1 Ceremony Ownership: Phase D (Google Drive media upload) ✅

Batafsil: [STORAGE_ARCHITECTURE.md §6](STORAGE_ARCHITECTURE.md).

* Arxitektura: mobil ilova baytlarni **to'g'ridan-to'g'ri Google Drive resumable sessiyaga** yuboradi; backend
  sessiyani ochadi va yakunda faylni Drive'dan qayta o'qib tekshiradi. Disk / Celery / Redis kerak bo'lmadi.
* Yangi `apps/media`: `CeremonyMedia` (PHOTO/VIDEO; UPLOADING → READY / FAILED / CANCELLED / EXPIRED), servislar,
  `manage.py expire_media_uploads`. `apps/storage`: `DriveFolder` (idempotent papka daraxti), `folders.py`,
  gateway: `start_resumable_upload`, `upload_status`, `cancel_upload`, `file_metadata`, `find_child_folder`.
* Endpointlar (studiya: istalgan faol a'zo — OWNER/MANAGER/UPLOADER, SUPER_ADMIN):
  `GET /ceremonies/{id}/media/`, `POST …/media/uploads/`, `GET …/uploads/{media_id}/` (jonli progress),
  `POST …/uploads/{media_id}/complete/`, `POST …/uploads/{media_id}/cancel/`.
* Xavfsizlik: OAuth token mijozga berilmaydi; session URI shifrlangan, faqat yuklovchiga; Drive ID'lar API'da yo'q;
  fayl ID'si sessiyadan olinadi; papka/marker/hajm/tur/md5 tekshiruvi, mos kelmasa fayl o'chiriladi; Drive nomlarida PII yo'q.
* Migratsiyalar: `storage/0002_drive_folder`, `media/0001_initial`, `audit/0006_media_upload_failed`.
* Developer Center: Studio Mobile "Media yuklash / jarayoni / davom ettirish" endi AVAILABLE; `planned.py` dan D olib tashlandi.

**Testlar**: to'liq to'plam yashil (venues bilan). Yangi `tests/test_media_upload.py` — 18 (soxta Drive:
papka daraxti, idempotentlik, o'chirilgan papka, rollar/cross-studio, validatsiya, ombor yo'q, jonli progress,
yakunlash, 6 xil soxtalashtirish, muddat, bekor qilish, akkaunt almashishi), `tests/test_drive_gateway_upload.py` — 9
(haqiqiy gateway HTTP tahlili, `requests` stub). Mutatsiya: 4 qoida ataylab buzildi — hammasi ushlandi.
**Jonli Drive bilan tekshirilmagan** — Google akkaunt ulanishi kerak (pastda).

**Keyingi**: Phase E (foydalanuvchi media API: galereya, thumbnail, stream, download) — tasdiq kutilmoqda.

## 2026-11-07 — V4.1 Ceremony Ownership: Phase C (xavfsiz taklif tizimi) ✅

Batafsil: [CEREMONY_OWNERSHIP.md](CEREMONY_OWNERSHIP.md#phase-c--xavfsiz-taklif-tizimi-endpointlar).

* Oqimlar `apps/ceremonies/invitations.py` (yaratish, qabul/rad, egalar tasdig'i, revoke/resend, leave) — qoidalar faqat
  `ownership.py` dan; har holat o'zgarishi compare-and-set (parallel qabul/ovoz — bitta g'olib).
* 13 yangi endpoint: studiya `/ceremonies/{id}/owners/` (+`invite/`); ega `/me/ceremonies/{id}/members|invitations|owner-requests|viewers/…|leave/`;
  `/me/invitations/{id}/`. `/me/ceremonies/`, `/me/invitations/` yangi modelga o'tdi (`access_role` qo'shildi, v1 maydonlari saqlandi).
* v1 `/ceremonies/{id}/participants/` — deprecated alias (yangi modelga yozadi, raqam endi maskalangan).
  Accept javobi: `{status, access_role, ceremony}`.
* Xavfsizlik: OWNER — doim tasdiqlangan telefon; tasdiqlanmagan raqamga kelgan taklifda marosim tafsilotlari yashiriladi;
  JSHSHIR birinchi egalikka yaramaydi; studiya ACCEPTED egani olib tashlay olmaydi; ega faqat o'zi berganini bekor qiladi;
  muddati o'tgan — 410 (EXPIRED saqlanadi); limitlar `CEREMONY_MAX_PENDING_INVITATIONS`, `CEREMONY_MAX_INVITATION_SENDS`;
  throttle `invitation_respond`. `manage.py expire_ceremony_invitations`.
* Migratsiya: `ceremonies/0004_backfill_late_participants` (data). ENUM_NAME_OVERRIDES — ceremony enumlari.
* Kontrakt revision 5 (breaking yo'q), `API_ENDPOINTS.md`, `openapi.yaml` qayta yaratildi (venues sessiyasi bilan kelishilgan holda bir marta).

**Testlar**: 1073 passed (to'liq to'plam, venues bilan). Yangi `tests/test_ceremony_invitations.py` — 25;
v1 testlari yangi qoidalarga moslandi (maskalangan raqam, OWNER uchun tasdiqlangan telefon, kuyov — kelin tasdig'i,
studiya ACCEPTED egani o'chira olmaydi). Mutatsiya tekshiruvi: 7 ta ruxsat qoidasi ataylab buzilganda hammasi ushlandi.
`ruff`, `makemigrations --check`, `api_contract`, `spectacular --validate --fail-on-warn` toza.

**Keyingi**: Phase D (Google Drive media upload) — tasdiq kutilmoqda.

## 2026-11-07 — V5.0 Venue & Studio Availability: Phase A (audit) + Phase B (Venue/Hall, a'zoliklar) ✅

Batafsil: [VENUE_AVAILABILITY.md](VENUE_AVAILABILITY.md).

**Phase A — audit va DB arxitekturasi**
* Mavjud pattern'lar qayta ishlatildi: `BaseModel`/`SoftDeleteModel`, rol darvozasi + a'zolik (`StudioMembership` kabi), `access_grant` kontrakti, audit.
* C–I dizayni: umumiy `scheduling.Resource` (hall / studio resource), `CalendarEntry` + PostgreSQL exclusion constraint
  (`btree_gist`, `tstzrange &&`) + `SELECT … FOR UPDATE`, deterministik narx tartibi, publication workflow, SQL availability search.
* Xavflar: lokal PostgreSQL/Docker yo'q (SQLite'da concurrency isbotlanmaydi); parallel V4.1 sessiyasi va avto-commit.

**Phase B — modellar, a'zoliklar, ruxsatlar**
* `User.Role.VENUE_OWNER` (+ `CLIENT_ROLES`, `/users/` filtri, `access.ROLE_ORDER`). Migratsiya `accounts/0003_venue_owner_role`.
* `apps/venues`: `Venue`, `VenueImage`, `VenueHall`, `VenueMembership` (OWNER/MANAGER/SCHEDULER/VIEWER) + `CAPABILITIES` matritsasi.
  Migratsiya `venues/0001_initial`. DB cheklovlari: sig'im, narx ≥ 0, faqat UZS, koordinatalar, E.164, zal nomi unikal, a'zolik unikal.
* Servislar: `create_venue` (OWNER a'zolik + "Asosiy zal", PRIVATE), `add_member`/`update_member` (faqat VENUE_OWNER hisoblar,
  oxirgi OWNER himoyasi, venue qatori lock), `venues_for`/`ensure_capability` (blocked venue — faqat o'qish).
* Endpointlar: `GET/POST /venue-owner/venues/`, `GET/PATCH /venue-owner/venues/{id}/`, `GET/POST …/halls/`, `PATCH …/halls/{hall_id}/`,
  `GET/POST …/members/`, `PATCH …/members/{membership_id}/` (faqat OWNER; telefon bo'yicha, umumiy xato, throttle `venue_member_add`).
* Audit: `Decimal` qiymatlar endi string sifatida yoziladi (avval JSON xatosi bo'lardi).
* Panel (minimal, buzilmasligi uchun): `VENUE_OWNER` rol turi, badge, foydalanuvchi filtri va formasi (avval tahrirlash rolni USER'ga tushirib yuborardi),
  Developer Center rol bo'limi `/developer/venue-owner`.

**Testlar**: `tests/test_venues.py` — 41 (yaratish, egalik, cross-venue/hall izolyatsiyasi, a'zolik imkoniyatlari, bloklangan venue,
admin maydonlari himoyasi, boshqa rollar 403, shaxsiy ma'lumot yo'qligi, DB constraint'lar, a'zolik servislari va API).
To'liq to'plam: **1108 passed**. Kontrakt: revision 4 + 6 (79 operatsiya), `API_ENDPOINTS.md`, `openapi.yaml` qayta yaratildi (0 warning).
Kontrakt runtime matritsasiga `VENUE_OWNER` chaqiruvchisi qo'shildi. `ruff`, `makemigrations --check`, `tsc`, `eslint` toza.
Migratsiyalar dev DB nusxasida oldinga/orqaga/oldinga tekshirildi.

Qarorlar: PostgreSQL o'rnatiladi; studiya va to'yxona — alohida hisoblar; a'zolar endpointi — ha.

**Keyingi**: Phase C (umumiy scheduling engine) — PostgreSQL o'rnatilgach, tasdiq bilan.

## 2026-11-07 — V4.1 Ceremony Ownership: Phase A (audit) + Phase B (modellar, ruxsatlar) ✅

Batafsil: [CEREMONY_OWNERSHIP.md](CEREMONY_OWNERSHIP.md).

**Phase A — audit**
* Mavjud: `Ceremony` + v1 `CeremonyParticipant` (studiya telefon orqali BRIDE/GROOM/OTHER taklif qiladi, ACTIVE = to'liq kirish).
  Yo'q edi: OWNER/VIEWER, ko'p egalar tasdig'i, JSHSHIR orqali taklif, muddat, ko'ruvchilarga ulashish.
* Xavf: JSHSHIR ro'yxatdan o'tishda tekshirilmaydi → faqat identifikator; OTP yo'q → OWNER uchun tasdiqlangan telefon har doim shart;
  v1'da studiya egalar roziligisiz yangi "ega" qo'sha olardi.

**Phase B — DB va ruxsatlar**
* Modellar: `CeremonyInvitation` (Fernet + HMAC identifikator, maskalangan hint, muddat, inviter_kind),
  `CeremonyOwnership` (BRIDE/GROOM/FAMILY_OWNER/OTHER_OWNER; PENDING→ACCEPTED/REJECTED/REVOKED),
  `CeremonyOwnershipApproval` (yangi egani mavjud egalar tasdiqlaydi), `CeremonyViewerAccess`.
  `Ceremony.cover_image`, marosim turlari kengaytirildi.
* DB cheklovlari: takroriy PENDING taklif, takroriy faol egalik/ko'ruvchi, ikkinchi kelin/kuyov, studiyadan VIEWER taklifi,
  owner_type ⇔ rol, ACCEPTED ⇒ user / accepted_at.
* Ruxsat qatlami `apps/ceremonies/ownership.py` + DRF `IsCeremonyMember` / `IsCeremonyOwner` (object-level).
* Migratsiyalar: `ceremonies/0002_ownership_model`, `ceremonies/0003_backfill_ownership_from_participants`
  (v1 → yangi model, idempotent, qaytariladigan; dev DB: 1 ACTIVE kuyov → ACCEPTED ega), `audit/0005_ceremony_ownership_actions`.
* Sozlamalar: `CEREMONY_OWNER_REQUIRE_VERIFIED_PHONE=true`, `CEREMONY_INVITATION_TTL_DAYS=14` (`.env.example`).
* `apps/devcenter/planned.py` — rejalashtirilgan endpointlar (C–F) haqiqiylaridan alohida; `API_ENDPOINTS.md` da alohida bo'lim.
* Mavjud endpointlar o'zgarmadi (v1 oqimi ishlashda davom etadi). Kontrakt: faqat `event_type` enum kengaygani
  (schema_fingerprint, breaking emas) — `api_contract --write`. `openapi.yaml` qayta yaratildi.

**Testlar**: 756 passed (oldin 728; `tests/test_ceremony_ownership.py` — 27, `test_devcenter.py` — planned≠live).
`ruff`, `makemigrations --check`, `api_contract`, `spectacular --validate --fail-on-warn` toza.
Migratsiyalar dev DB nusxasida oldinga/orqaga/oldinga tekshirildi.

**Keyingi**: Phase C (xavfsiz taklif tizimi) — tasdiq kutilmoqda.

## 2026-11-07 — Studios & Ceremonies API + studiya va foydalanuvchi web ilovalari ✅

**Backend (`apps/ceremonies`, `apps/studios`)**
* `Studio.description`; `StudioMembership` rollari OWNER / MANAGER / UPLOADER. Data migration: har bir
  studiyaning mas'ul shaxsi OWNER a'zo bo'ldi (dev DB: 4/4). Panelda egasi almashsa a'zolik sinxronlanadi.
* `Ceremony` (DRAFT → READY → ARCHIVED; UPLOADING/PROCESSING — media pipeline uchun) va
  `CeremonyParticipant` (BRIDE / GROOM / OTHER; INVITED → ACTIVE / DECLINED / REVOKED).
* Telefon orqali taklif: javob raqam ro'yxatdan o'tganmi-yo'qligini bildirmaydi; ism faqat qabul qilingach
  ko'rinadi; marosim faqat taklif egasi o'zi qabul qilganda ochiladi. Bitta kelin/kuyov — DB constraint.
* `CEREMONY_INVITE_REQUIRE_VERIFIED_PHONE` — production'da yoqiq (OTP kelguncha qabul qilish faqat
  tasdiqlangan telefon bilan), DEBUG'da o'chiq.
* Endpointlar: `/studios/me/`, `/studios/me/ceremonies/`, `/ceremonies/` (CRUD, ADMIN kira olmaydi),
  `/ceremonies/{id}/participants/` (+DELETE), `/me/ceremonies/`, `/me/invitations/` (+accept/decline).
* Kontrakt: `access_grant` / `access_notes`, OWNERSHIP_TESTS ro'yxatga olindi, `api_contract --write`.

**Frontend**
* `frontend-studio/` (port 3001): marosimlar ro'yxati/filtr, yaratish, tahrirlash, holat, ishtirokchi taklifi.
* `frontend-user/` (port 3002): ro'yxatdan o'tish, takliflarni qabul/rad, mening marosimlarim, profil.
* Har ilova o'z cookie prefiksi bilan (`mgs_` / `mgu_`): localhost'da bitta brauzerda admin, studiya va
  foydalanuvchi sessiyalari bir-biriga aralashmaydi; boshqa ilova cookie'lari backend'ga yuborilmaydi.

**Testlar**: backend to'liq to'plam yashil (ceremonies: 27 yangi test). Jonli E2E (bitta brauzer):
studiya marosim yaratdi → kelinni taklif qildi → kelin qabul qildi → ikkala sessiya saqlandi.

**Keyingi**: media upload (Phase C) va `/me/ceremonies/{id}/media/`.

## 2026-11-07 — API Developer Center: Phase 3 (backend) + Phase 4 (UI) ✅

**Phase 3 — backend** (`apps/devcenter`, faqat SUPER_ADMIN, faqat o'qish, SSRF yuzasi yo'q)
* `GET /api/v1/devcenter/overview/` — operatsiyalar, rollar, hujjat/kontrakt/holat statistikasi, oxirgi o'zgarish.
* `GET /api/v1/devcenter/endpoints/?role=&version=&method=` — rol bo'yicha katalog + 24 soatlik real trafik.
* `GET /api/v1/devcenter/mobile/` — User / Studio Mobile funksiyalari real `operation_id` larga bog'langan
  (`apps/devcenter/mobile.py`); API'si yo'q funksiyalar alohida `PLANNED` (rasmlar, videolar, media upload…).
* `GET /api/v1/devcenter/changelog/` — `contracts/api_changelog.json`. `manage.py api_contract --write [--note]`
  har bir kontrakt o'zgarishini avtomatik yozadi; `breaking` (o'chirilgan / kirish o'zgargan) va
  `schema_changed` alohida belgilanadi.

**Phase 4 — UI** (`frontend/`)
* Sidebar: yig'iladigan **Developer Center** guruhi — API Overview, All Endpoints, User / Studio / Admin /
  Super Admin / Public APIs, Mobile API, API Monitoring, API Changelog.
* **API Monitoring → Endpointlar**: rol tablari (Barchasi · Public · User · Studio · Admin · Super Admin, sonlari bilan),
  ro'yxatda rol belgilari, tafsilotda "Kirish siyosati" (rollar, ADMIN ruxsat kodlari, ma'lumot doirasi,
  shartlar, REVIEW / Documentation Missing / kontrakt ogohlantirishlari).
* Kod namunalari: cURL, JavaScript, Python, **Kotlin/Retrofit, Swift/URLSession, Dart/Dio** — Copy bilan.
* Endpoint ro'yxati frontendda hardcode qilinmagan — hammasi backend API'dan.

**Testlar**: backend 728 passed (`tests/test_devcenter.py` qo'shildi: SUPER_ADMIN-only, rol guruhlari,
mobil xarita faqat mavjud va rol chaqira oladigan operatsiyalarga ishora qiladi, changelog = kontrakt).
`tsc`, `eslint`, `next build` toza. Jonli tekshiruv (vaqtinchalik DB nusxasi + Chrome headless): 6 ta Developer
Center sahifasi, Monitoring rol filtri (Studio = 11), Kotlin namunasi, 390px ekran — konsolda xato yo'q.

**Keyingi**: Phase 5 (API Testing Console) — tasdiq kutilmoqda.

## 2026-11-07 — API Developer Center: Phase 1 (audit) + Phase 2 (rol kontrakti) ✅

**Phase 1 — inventarizatsiya** ([API_INVENTORY.md](API_INVENTORY.md), [API_ENDPOINTS.md](API_ENDPOINTS.md))
* 36 operatsiya: PUBLIC 8 · USER 2 · STUDIO 2 · ADMIN 14 (granular kod bilan) · SUPER_ADMIN 28.
* Kamchiliklar: `/auth/me/` rollari bo'sh ko'rsatilardi; noma'lum permission class jimgina "istalgan
  foydalanuvchi" bo'lardi; ownership/shartlar hujjatlanmagan; 16 operatsiyada `summary` yo'q; CI yo'q.
* STUDIO roli uchun faqat auth + profil mavjud; ceremony/media API'lari — PLANNED.

**Phase 2 — rol kontrakti**
* `apps/accounts/access.py`: rollar faqat haqiqiy DRF permission class'laridan (`access_grant`, `&`/`|`,
  `AllowAny`/`IsAuthenticated`) aniqlanadi; aniqlab bo'lmasa `REVIEW_REQUIRED` (rol taxmin qilinmaydi).
* `access_notes` (`AccessNote`): ownership scope va qo'shimcha shartlar view yonida e'lon qilinadi.
* OpenAPI: `x-allowed-roles`, `x-auth-type`, `x-required-permissions`, `x-ownership-scope`,
  `x-access-conditions`, `x-access-status`, `x-access-policy`, `x-documentation`, `x-api-version`
  (`x-access` saqlangan).
* Katalog (`/monitoring/endpoints/`) yangi maydonlar + `contract_status`; `documentation_status`
  ("Documentation Missing") alohida, traffic `status` alohida.
* `contracts/api_access_contract.json` + `manage.py api_contract [--write]`; `export_api_endpoints`
  rollar bo'yicha guruhlaydi.
* Users/Admins/Studios/Dashboard uchun `summary` qo'shildi. Endpoint URL, method va javoblar o'zgarmadi.
* CI: `.github/workflows/backend-ci.yml` (ruff, schema validate, api_contract, pytest).

**Testlar**: 504 passed (oldin 186; yangi `test_api_access_contract.py` — 318). Runtime matritsa: 36 × 6
chaqiruvchi. Mutatsiya tekshiruvi: `HasAdminPermission` ataylab buzilganda 12 ta test fail bo'ldi.
`spectacular --validate --fail-on-warn` toza.

**Ochiq masalalar**
* `docs/openapi.yaml` qayta yaratilmadi — parallel sessiyaning tugallanmagan `studios` o'zgarishlari
  ichiga tushib qolmasligi uchun. Ular tugagach: `python manage.py spectacular --validate --fail-on-warn --file ../docs/openapi.yaml`.
* Studios/Ceremonies yangi endpointlari qo'shilganda `api_contract --write` qilinishi kerak (aks holda CI fail).

**Keyingi**: Phase 3 (Developer Center backend: rol bo'limlari, mobile guruhlar, changelog) — tasdiq kutilmoqda.

## 2026-11-07 — Phase A: Google OAuth Connection ✅

**Qilindi**
* `apps/storage`: OAuth Authorization Code Flow + PKCE, `access_type=offline`, `prompt=consent`.
* Bir martalik, 10 daqiqalik, hash'langan `state` + httpOnly binding cookie (brauzerga bog'lash).
* Callback JWT'siz (Google redirect), lekin faqat ulashni boshlagan faol SUPER_ADMIN uchun yakunlanadi.
* Refresh token — alohida jadvalda, alohida Fernet kalit (`GOOGLE_TOKEN_ENCRYPTION_KEY`) bilan shifrlangan.
* Endpointlar: `connect`, `callback`, `status`, `test`, `disconnect` (`/api/v1/admin/storage/google/`).
* `RECONNECT_REQUIRED` (`invalid_grant`), Drive xatolari kodlarga map qilinadi (quota, permission, API disabled…).
* `credentials/google_oauth_client.json` xavfsiz o'qiladi; `google_oauth_check`, `storage_selftest` komandalar.
* Panel: **Google Drive** bo'limi — holat, akkaunt, scopes, Connect / Test / Disconnect, qayta ulash ogohlantirishi.
* Audit: `STORAGE_CONNECT`, `STORAGE_CONNECT_FAILED`, `STORAGE_DISCONNECT`. API katalog/Swagger'ga avtomatik qo'shildi.
* Log: `?code=&state=` runserver log'ida redaktsiya qilinadi.

**Xavfsizlik tuzatishlari**
* Git'da kuzatilgan `backend/.env` va Google client secret JSON aniqlandi. JSON push qilinmagan commitdan
  olib tashlandi; `.env` kuzatuvdan chiqarildi; `.gitignore` ga sir qoidalari qo'shildi.
* `.env` dagi noto'g'ri `PINFL_ENCRYPTION_KEYS` (500 xato) — yangi to'g'ri kalit; o'qib bo'lmaydigan 26 ta dev JSHSHIR tozalandi.

**Testlar**: 186 passed (Phase A: 44 yangi). Jonli: haqiqiy Google consent sahifasi MarosimGo uchun ochildi (xatosiz).

**Ochiq masalalar**
* Haqiqiy akkaunt ulanishi va `storage_selftest` — egasi tomonidan bajariladi (Google login talab qiladi).
* Picker + mavjud papka (`drive.file`) — Phase B'da jonli tasdiqlanadi.
* GitHub'dagi eski `.env` sirlari tarixda qolgan — rotatsiya qilingan; tarixni tozalash (ixtiyoriy) egasining qarori.

**Keyingi**: Phase B (Drive Folder Management) — tasdiq kutilmoqda.
