# To'yxona va studiya bandlik tizimi — arxitektura (V5.0)

Holat: **Phase A (audit + arxitektura) + Phase B (Venue/Hall modellari, a'zoliklar) ✅ 2026-11-07**. C–I — tasdiq kutilmoqda.

## Phase A — mavjud loyiha auditi

| Soha | Mavjud holat | V5.0 uchun xulosa |
|---|---|---|
| DB | Dev: SQLite (`backend/db.sqlite3`, git'da avto-commit qilinadi); prod: `DATABASE_URL` (PostgreSQL), `psycopg` o'rnatilgan. Testlar: SQLite in-memory. Lokal PostgreSQL / Docker **yo'q**. | Phase B ikkala DB'da ishlaydi. Phase C'dagi exclusion constraint faqat PostgreSQL'da ishlaydi → PG test muhiti kerak (pastda, "Ochiq savollar"). |
| Modellar | `BaseModel` (UUID PK + `created_at`/`updated_at`), `SoftDeleteModel` (`deleted_at`). | Yangi modellar ham shu asosda. |
| Rollar | `User.role`: SUPER_ADMIN / ADMIN / STUDIO / USER. ADMIN huquqlari `admin_permissions` (JSON, `permissions_catalog.py` kodlari); adminlarni **faqat SUPER_ADMIN** boshqaradi (`/admins/` — `IsSuperAdmin`). | `VENUE_OWNER` qo'shildi. Admin o'ziga yoki boshqa adminga ruxsat bera olmasligi mavjud dizaynda kafolatlangan. `venue.*` kodlari Phase E'da katalogga qo'shiladi. |
| Biznes a'zoligi | `StudioMembership` OWNER / MANAGER / UPLOADER. Rol darvozasi `User.role == STUDIO`, qaysi studiya — a'zolik (`get_queryset`, begonasi 404). | Xuddi shu pattern: `VenueMembership` OWNER / MANAGER / SCHEDULER / VIEWER + imkoniyatlar matritsasi. |
| Marosim | `Ceremony` (studio, `event_type`, `event_date`…), Drive papka maydoni API orqali yozilmaydi. | Bron marosimga **ixtiyoriy** bog'lanadi; bron hech qachon avtomatik marosim yoki media arxiv ochmaydi. |
| Audit | `AuditLog` (o'zgarmas), `record()`, `snapshot()`/`diff()`. | Venue/hall/a'zolik yozuvlari audit qilinadi. `Decimal` endi string sifatida yoziladi (pul aniq saqlanadi). |
| API kontrakt | Rollar haqiqiy DRF permission class'laridan (`accounts/access.py`); `access_notes`; `contracts/api_access_contract.json`; runtime matritsa har endpointni har rol bilan chaqiradi. | Yangi `IsVenueAccount` o'z `access_grant`iga ega; matritsaga `VENUE_OWNER` chaqiruvchisi qo'shildi. Yangi endpointlar katalogga avtomatik tushadi. |
| Vaqt | `TIME_ZONE = "Asia/Tashkent"`, `USE_TZ = True`. | Intervallar `timestamptz` (UTC) da saqlanadi, kalendar Asia/Tashkent'da hisoblanadi. |
| Frontend | `frontend/` — Super Admin paneli (Next.js, TS, Tailwind, shadcn, Motion). `frontend-studio/`, `frontend-user/` — mavjud. | V5.0'da to'yxonachi/studiya/foydalanuvchi uchun yangi web yo'q — faqat mobil REST API. Panelga faqat minimal rol qo'llovi qo'shildi. |

**Aniqlangan xavflar**
1. **Concurrency testlari SQLite'da isbotlanmaydi.** SQLite yozuvlarni butun DB bo'yicha ketma-ket bajaradi, `SELECT … FOR UPDATE` va exclusion constraint'larni qo'llamaydi. Double-booking himoyasi PostgreSQL'da sinalishi shart.
2. **Parallel sessiya va avto-commit.** Repo fayllari tashqi vosita tomonidan avtomatik commit qilinadi. V4.1 (ceremony ownership) sessiyasi parallel ishlayapti. Umumiy fayllar (kontrakt JSON, `API_ENDPOINTS.md`, `openapi.yaml`) bitta sessiya tomonidan, kelishilgan holda qayta yaratiladi.
3. **Rolning API-dagi enum'i kengaydi.** `RoleEnum`ga `VENUE_OWNER` qo'shildi. Mavjud mobil mijozlar noma'lum enum qiymatiga chidamli bo'lishi kerak (`auth/me` kontraktda "BREAKING" deb belgilangan, aslida faqat kengaytirish).
4. `accounts/0003` migratsiyasini orqaga qaytarib bo'lmaydi, agar bazada `VENUE_OWNER` hisoblar bor bo'lsa (CHECK constraint). Avval ularning rolini o'zgartirish kerak.

## Umumiy arxitektura (C–I uchun dizayn)

```
accounts.User ─* venues.VenueMembership *─ venues.Venue 1─* venues.VenueHall ─┐
                                                       1─* venues.VenueImage   │ 1:1
accounts.User ─* studios.StudioMembership *─ studios.Studio 1─* studios.StudioResource (C) ─┤
                                                                                │
                                           scheduling.Resource (C) ◄────────────┘
                                             1─* scheduling.WorkingHours (haftalik shablon)
                                             1─* scheduling.CalendarEntry (starts_at, ends_at, status)
                                                       ▲ 0..1
                       bookings.BookingRequest (G) ────┘   (+ ixtiyoriy ceremony FK)
venues.VenuePricingRule (D) ─► venue / hall
venues.VenuePublicationRequest (E) ─► venue (tarix + qaror)
```

### Umumiy scheduling engine (Phase C)
* `scheduling.Resource` — band qilinadigan har bir narsa: `kind` = `VENUE_HALL` | `STUDIO_RESOURCE`, `venue_hall` / `studio_resource` FK (CHECK: aniq bittasi to'ldirilgan), `timezone` (`Asia/Tashkent`), `is_active`. Bandlik **resurs** darajasida yuritiladi: zal A bandligi zal B ga ta'sir qilmaydi, studiyaning ikkita operatori mustaqil.
* `CalendarEntry` — `resource`, `starts_at`, `ends_at` (timestamptz), `status` = AVAILABLE / HELD / BOOKED / BLOCKED / CLOSED, `event_type`, `private_note`, `booking` (0..1), `expires_at` (HELD uchun), `created_by`.
  * AVAILABLE — ixtiyoriy "ochiq slot" yozuvi (to'yxonachi bo'sh vaqt e'lon qiladi); oddiy holatda bo'sh vaqt **hisoblanadi**: ish vaqti ichida + band qiluvchi yozuv yo'q.
  * Bir kunda bir nechta mustaqil interval (masalan, 11:00–15:00 va 18:00–23:00).
* **Double booking himoyasi (DB darajasida):** PostgreSQL `ExclusionConstraint` (`btree_gist`): `(resource WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&)` `WHERE status IN ('HELD','BOOKED','BLOCKED','CLOSED')`. Ikki parallel tranzaksiyadan biri constraint xatosini oladi → API `409 Conflict`.
  * Server darajasida: har bir yozish `transaction.atomic()` + resurs qatoriga `SELECT … FOR UPDATE`. Bu SQLite/dev'da ham ishlaydigan qo'shimcha himoya. Shu bilan birga, muddati o'tgan HELD'lar o'sha tranzaksiyada EXPIRED qilinadi (lazy expiry). Shuning uchun constraint `now()` ga bog'liq bo'lmaydi.
  * Migratsiya `BtreeGistExtension` + constraint'ni faqat `connection.vendor == "postgresql"` bo'lsa qo'shadi.
* `WorkingHours` — resurs (yoki venue default) uchun haftalik shablon: `weekday`, `opens_at`, `closes_at`; dam olish kunlari = yozuv yo'q yoki `is_closed`. Maxsus sana yopilishi — `CLOSED` CalendarEntry.
* Kalendar API: DAY / WEEK / MONTH / YEAR overview. YEAR — kunlik agregat (`AVAILABLE/PARTIAL/FULL/CLOSED`), bitta SQL `GROUP BY date(starts_at AT TIME ZONE 'Asia/Tashkent')`.

### Studio (Phase C)
* `StudioResource` — `studio`, `kind` = PHOTOGRAPHER / VIDEOGRAPHER / TEAM / EQUIPMENT, `name`, `members` (StudioMembership M2M), `service_regions` (Region ro'yxati), `is_active`. Har bir StudioResource ↔ bitta `scheduling.Resource`.
* Mavjud `Ceremony` bilan bog'lanish: `BookingRequest.ceremony` (nullable). Ceremony yaratish va Drive papka ochish faqat studiyaning aniq amali bilan bo'ladi, bron tasdiqlanganda avtomatik emas.
* URL'lar mavjud standart bo'yicha: `/studios/me/calendar/`, `/studios/me/availability/blocks/` (spec'dagi `/studio/...` o'rniga), ommaviy qismi — `/studios/search/`, `/studios/{id}/availability/`.

### Dinamik narx (Phase D)
* `VenuePricingRule`: venue, hall (null = butun to'yxona), `rule_type`, `start_date`/`end_date`, `weekday`, `starts_time`/`ends_time` (ixtiyoriy), `amount` (Decimal), `priority`, `is_active`.
* Deterministik tartib: 1) eng aniq turdagi qoida narxni belgilaydi: `SPECIAL_DATE > HOLIDAY > SEASONAL > WEEKEND/WEEKDAY > BASE`. Topilmasa, `hall.base_price` → `venue.base_price`. 2) Bir tur ichida: hall qoidasi > venue qoidasi, so'ng `priority` (katta yutadi), so'ng `created_at`, so'ng `id`. 3) `DISCOUNT` oxirida qo'llanadi (eng yuqori prioritetlisi, foiz yoki summa), narx 0 dan pastga tushmaydi.
* Narxni faqat server hisoblaydi. Bronda `quoted_price`, `confirmed_price`, `currency`, `pricing_snapshot` (JSON: qo'llangan qoidalar ID/turi/summasi) saqlanadi. Qoidalar keyin o'zgarsa, tasdiqlangan bron narxi o'zgarmaydi.

### Public visibility va admin ruxsatlari (Phase E)
* `permissions_catalog`ga: `venue.view_all`, `venue.create`, `venue.edit`, `venue.manage_schedule`, `venue.manage_pricing`, `venue.approve_publication`, `venue.suspend`, `venue.manage_bookings`.
* ADMIN ularni faqat SUPER_ADMIN bergan bo'lsa ishlata oladi: mavjud `HasAdminPermission`, ruxsatlar har so'rovda qayta o'qiladi. Shuning uchun ruxsat bekor qilinsa, keyingi so'rovdanoq kuchga kiradi. Adminlarni faqat SUPER_ADMIN tahrirlaydi, shuning uchun o'z-o'zini ko'tarish mumkin emas.
* Oqim: PRIVATE/REJECTED → (OWNER `publish-request`) → PENDING_APPROVAL → (admin) APPROVED / REJECTED; APPROVED → SUSPENDED (admin). `VenuePublicationRequest` tarixni (kim, qachon, izoh) saqlaydi.
* Ommaga faqat `is_active AND publication_status = APPROVED` venue + `is_active` hall chiqadi. Public serializer'lar alohida: ularda boshqa mijozlarning ismi, telefoni, JSHSHIR-i, marosim tafsilotlari va izohlari umuman bo'lmaydi. Faqat `available` (bool), sana, ommaviy narx va sig'im ko'rsatiladi.

### Qidiruv (Phase F)
* Bitta SQL: approved+active venue ⨝ active hall ⨝ resource, `NOT EXISTS` (band qiluvchi CalendarEntry interval bilan kesishadi) + ish vaqti tekshiruvi; region/district/capacity/price/venue_type filtrlari. Narx Phase D engine'idan olinadi (cheapest/highest sort uchun so'rov ichida annotate, keyinchalik materialized kunlik narx jadvali). Indekslar: GiST `(resource, tstzrange)`, `(publication_status, is_active)`, `(region, district)`, `base_price`.
* Natija ma'lumot uchun. Bron tasdiqlanayotganda bo'shlik qayta tekshiriladi (constraint + lock).

### Bronlar (Phase G)
* `BookingRequest`: requester, resource (hall yoki studio resource), `requested_start/end`, `proposed_price` (server hisoblagan quote), `confirmed_price`, `currency`, `pricing_snapshot`, `status` = REQUESTED / HELD / CONFIRMED / REJECTED / CANCELLED / EXPIRED / COMPLETED, `hold_expires_at`, `ceremony` (ixtiyoriy), `BookingEvent` audit tarixi.
* REQUESTED hech narsani band qilmaydi. HELD/CONFIRMED CalendarEntry (HELD/BOOKED) yaratadi, va exclusion constraint shu yerda ishlaydi. Tasdiqlashni `MANAGE_BOOKINGS` imkoniyatiga ega a'zo (OWNER/MANAGER) qiladi. To'lov qilinmaydi.

## Phase B — ma'lumotlar modeli (amalga oshirildi)

| Model | Asosiy maydonlar | Cheklovlar |
|---|---|---|
| `Venue` | id (UUID), name, description, `venue_type`, address, `region` (14 hudud), district, latitude/longitude (Decimal 9,6), phone_number (E.164, biznes raqami), cover_image (WEBP, EXIF'siz), capacity_min/max, base_price (Decimal 14,2), currency (UZS), is_active, publication_status, created_at/updated_at, deleted_at | `capacity_max ≥ 1`, `capacity_min ≤ capacity_max`, `base_price ≥ 0`, `currency = 'UZS'`, koordinata diapazoni, telefon `+` bilan, publication_status ro'yxati |
| `VenueImage` | venue, image, position | galereya (endpoint keyingi bosqichda) |
| `VenueHall` | id, venue, name, capacity, base_price (null = venue narxi), is_active, deleted_at | to'yxona ichida nom unikal (o'chirilmaganlar orasida), `capacity ≥ 1`, `base_price ≥ 0` |
| `VenueMembership` | venue, user, role (OWNER/MANAGER/SCHEDULER/VIEWER), is_active | `(venue, user)` unikal, rol ro'yxati; servisda: faqat VENUE_OWNER hisoblar; oxirgi faol OWNER olib tashlanmaydi |

**A'zolik → imkoniyatlar** (`apps/venues/models.py: CAPABILITIES`, yagona manba)

| Imkoniyat | OWNER | MANAGER | SCHEDULER | VIEWER |
|---|:-:|:-:|:-:|:-:|
| VIEW | ✓ | ✓ | ✓ | ✓ |
| EDIT_PROFILE | ✓ | ✓ | | |
| MANAGE_HALLS | ✓ | ✓ | | |
| MANAGE_SCHEDULE | ✓ | ✓ | ✓ | |
| MANAGE_PRICING | ✓ | ✓ | | |
| MANAGE_BOOKINGS (tasdiqlash/bekor qilish) | ✓ | ✓ | | |
| REQUEST_PUBLICATION | ✓ | | | |
| MANAGE_MEMBERS | ✓ | | | |

Admin bloklagan to'yxonada (`is_active=false`) a'zolarda faqat VIEW qoladi. Nofaol hisob yoki nofaol a'zolikda hech qanday huquq qolmaydi.

**Ruxsat qatlami:** `IsVenueAccount` (rol darvozasi: faol VENUE_OWNER) → `services.venues_for` (faqat faol a'zolik; begonasi 404) → `services.ensure_capability` (amal). `User.role` faqat hisob turi; bitta hisob bir nechta to'yxonada turli rolda bo'lishi mumkin.

**Endpointlar (Phase B)**: `GET/POST /api/v1/venue-owner/venues/`, `GET/PATCH /api/v1/venue-owner/venues/{id}/`, `GET/POST …/{id}/halls/`, `PATCH …/{id}/halls/{hall_id}/`, `GET/POST …/{id}/members/`, `PATCH …/{id}/members/{membership_id}/` (faqat OWNER — `MANAGE_MEMBERS`; a'zo telefon raqami bo'yicha qo'shiladi, topilmasa bitta umumiy xato, throttle `venue_member_add`; hamkasbga faqat id / ism / telefon ko'rinadi). Yaratuvchi OWNER bo'ladi, standart "Asosiy zal" ochiladi, holat PRIVATE. `is_active`, `publication_status` va `currency` maydonlarini mijoz o'zgartira olmaydi. VENUE_OWNER hisoblarini Super Admin / `users.create` ruxsatli Admin `/api/v1/users/` orqali yaratadi (ommaviy ro'yxatdan o'tish har doim USER yaratadi).

## Qarorlar (foydalanuvchi, 2026-11-07)
1. **PostgreSQL o'rnatiladi** — Phase C concurrency/exclusion constraint testlari shu muhitda (SQLite'da `skip`).
2. **Studiya va to'yxona — alohida hisoblar** (rol darvozasi `User.role` bo'yicha qoladi).
3. **A'zolar endpointi qo'shildi** (`/venue-owner/venues/{id}/members/`).

## Ochiq savollar
1. APPROVED to'yxona profili (nom, manzil, narx) o'zgartirilsa, qayta tasdiq talab qilinsinmi (Phase E)?
2. APPROVED to'yxona profili (nom, manzil, narx) o'zgartirilsa, qayta tasdiq talab qilinsinmi (Phase E)?
