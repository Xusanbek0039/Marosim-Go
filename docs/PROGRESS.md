# Progress

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
