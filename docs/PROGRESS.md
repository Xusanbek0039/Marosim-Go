# Progress

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
