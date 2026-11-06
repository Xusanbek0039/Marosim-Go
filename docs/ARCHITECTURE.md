# MarosimGo — Arxitektura rejasi (1-bosqich)

> Holat: **loyiha qoralamasi, tasdiqlanishi kutilmoqda.** Implementatsiya preview tasdiqlangandan keyin boshlanadi.
> Vizual konsept: **C — “Liquid Control”**.

---

## 0. Mavjud holat tahlili

| Narsa | Holat |
|---|---|
| Repo | `README.md`, `LICENSE`, `.gitignore` dan iborat, kod yo‘q |
| Referens video | Repoda **yo‘q** — foydalanuvchidan so‘raladi |
| Node.js | v24.22.0 (LTS) ✅ |
| Python | 3.12.0 ✅ |
| PostgreSQL | O‘rnatilmagan ❌ |
| Docker | O‘rnatilmagan ❌ |

Repo ildizi = prompt’dagi `marosimgo/` papkasi (alohida ichki papka yaratilmaydi).

---

## 1. Loyiha strukturasi

```
Marosim-Go/
├── backend/                      # Django + DRF — butun biznes logika va REST API
│   ├── config/                   # settings (base/dev/prod), urls, wsgi/asgi
│   ├── apps/
│   │   ├── core/                 # umumiy: pagination, xatolar, permissionlar, shifrlash, upload validatorlar
│   │   ├── accounts/             # User modeli, rollar, auth (JWT + cookie), users/admins API
│   │   ├── studios/              # Studio, StudioMembership (kelajak uchun)
│   │   ├── audit/                # AuditLog modeli + yozuvchi servis
│   │   └── dashboard/            # overview agregatsiyasi
│   ├── tests/                    # pytest + pytest-django
│   ├── manage.py
│   └── requirements/ (base.txt, dev.txt)
├── frontend/                     # Next.js (App Router) — faqat Super Admin web panel
│   ├── src/app/
│   │   ├── (auth)/login/
│   │   └── (panel)/ dashboard · users · admins · studios · settings
│   ├── src/components/ui/        # shadcn/ui (Liquid Control mavzusida)
│   ├── src/components/layout/    # Sidebar, Topbar, PageTransition, ThemeToggle
│   ├── src/features/<module>/    # api.ts (TanStack Query hooklar), schema.ts (Zod), komponentlar
│   ├── src/lib/                  # api-client, query-client, utils
│   ├── src/motion/               # motion tokens + umumiy variants
│   └── middleware.ts             # sessiya bo‘lmasa /login ga yo‘naltirish
├── docs/                         # ARCHITECTURE.md, API.md, MOTION.md
├── .env.example
└── README.md
```

**Qoida:** frontendda biznes logika yo‘q. U faqat Django API’ni chaqiradi. Kelajakdagi mobil ilova ham xuddi shu `/api/v1/` endpointlardan foydalanadi.

---

## 2. Database schema

```
┌──────────────────────────── accounts_user ────────────────────────────┐
│ id               UUID PK                                              │
│ email            varchar(254) UNIQUE (case-insensitive) — login       │
│ password         varchar(128) — Argon2 hash                           │
│ first_name       varchar(100)                                         │
│ last_name        varchar(100)                                         │
│ pinfl_encrypted  text NULL      — Fernet (AES-128-CBC + HMAC) shifr   │
│ pinfl_hash       char(64) UNIQUE NULL — HMAC-SHA256 (unikallik/qidiruv)│
│ pinfl_last4      char(4) NULL   — maskalash uchun                     │
│ profile_picture  varchar (ImageField) NULL                            │
│ address          varchar(255)                                         │
│ role             varchar(20) — SUPER_ADMIN | ADMIN | STUDIO | USER    │
│ is_active        bool default true                                    │
│ is_staff         bool  (faqat Django admin uchun)                     │
│ last_login       timestamptz NULL                                     │
│ deleted_at       timestamptz NULL  — soft delete                      │
│ created_at       timestamptz                                          │
│ updated_at       timestamptz                                          │
│ INDEX(role, is_active), INDEX(created_at)                             │
└───────────────────────────────────────────────────────────────────────┘
            ▲ responsible_user (FK, PROTECT)          ▲ user (FK)
            │                                         │
┌────── studios_studio ──────┐        ┌──── studios_membership (kelajak) ────┐
│ id               UUID PK   │◄───────│ id UUID PK                            │
│ name             varchar   │ studio │ studio  FK → studio (CASCADE)         │
│ profile_picture  image NULL│        │ user    FK → user (PROTECT)           │
│ address          varchar   │        │ role    OWNER|MANAGER|OPERATOR|       │
│ responsible_user FK → user │        │         VIDEOGRAPHER                  │
│ is_active        bool      │        │ is_active, created_at, updated_at     │
│ deleted_at       NULL      │        │ UNIQUE(studio, user)                  │
│ created_at, updated_at     │        └───────────────────────────────────────┘
└────────────────────────────┘

┌──────────────────────── audit_auditlog ────────────────────────┐
│ id UUID PK · actor FK → user NULL · action (CREATE/UPDATE/     │
│ DEACTIVATE/DELETE/LOGIN/LOGIN_FAILED/LOGOUT/PINFL_REVEAL)      │
│ target_type · target_id · changes JSONB (sezgir maydonlar      │
│ "[REDACTED]") · ip_address · user_agent · created_at           │
│ INDEX(target_type, target_id), INDEX(actor, created_at)        │
└────────────────────────────────────────────────────────────────┘
```

**Qarorlar:**
- **Studio — tashkilot**, JSHSHIR esa `responsible_user` (jismoniy shaxs, `STUDIO` roli) da saqlanadi.
- `StudioMembership` jadvali hozir yaratiladi (bir studiyaga ko‘p xodim), lekin uning API’si keyingi bosqichga qoldiriladi.
- **JSHSHIR himoyasi:** `cryptography.MultiFernet` bilan shifrlanadi (kalitlar `PINFL_ENCRYPTION_KEYS` env’dan, rotatsiya qo‘llab-quvvatlanadi). Unikallik va aniq qidiruv uchun alohida kalit bilan HMAC hash. API’da standart ko‘rinish: `**********0471` (faqat oxirgi 4 raqam — boshidagi raqamlar jins va tug‘ilgan sanani oshkor qiladi). To‘liq qiymat faqat `SUPER_ADMIN` uchun alohida endpoint orqali va audit logga yozilib beriladi. Logging filter JSHSHIR’ni loglardan kesadi.
- **Super Admin** faqat `python manage.py createsuperadmin` buyrug‘i orqali yaratiladi — API orqali hech qachon.

---

## 3. API dizayni (`/api/v1/`)

### Umumiy kelishuvlar
- **Pagination:** `?page=2&page_size=20` (maks. 100) → `{ count, next, previous, results }`
- **Search:** `?search=` (ism, familiya, email, manzil; studiyada nom). JSHSHIR bo‘yicha qidiruv: `?pinfl=` — hash orqali aniq moslik.
- **Filter:** `?is_active=true`, `?role=STUDIO`, `?created_after=2026-11-01`
- **Sort:** `?ordering=-created_at` (ruxsat etilgan maydonlar ro‘yxati bilan)
- **Xato formati (har doim bir xil):**
  ```json
  { "error": { "code": "validation_error", "message": "Ma'lumotlar noto'g'ri",
               "details": { "pinfl": ["JSHSHIR 14 ta raqamdan iborat bo'lishi kerak"] } } }
  ```
- **OpenAPI:** `/api/v1/schema/`, Swagger UI: `/api/v1/docs/` (drf-spectacular)

### Endpointlar
| Metod | Yo‘l | Kim | Izoh |
|---|---|---|---|
| POST | `/auth/login/` | hamma (throttle 5/min) | email + parol. Web: httpOnly cookie; mobil: body’da token |
| POST | `/auth/refresh/` | refresh egasi | rotatsiya + eski refresh blacklist |
| POST | `/auth/logout/` | login qilgan | refresh blacklist + cookie tozalash |
| GET | `/auth/me/` | login qilgan | joriy profil |
| GET/POST | `/users/` | SUPER_ADMIN | `USER` va `STUDIO` rollari |
| GET/PATCH/DELETE | `/users/{id}/` | SUPER_ADMIN | DELETE = soft delete |
| GET | `/users/{id}/pinfl/` | SUPER_ADMIN | **taklif:** to‘liq JSHSHIR, audit qilinadi |
| GET/POST | `/admins/` | SUPER_ADMIN | `ADMIN` roli |
| GET/PATCH/DELETE | `/admins/{id}/` | SUPER_ADMIN | |
| GET/POST | `/studios/` | SUPER_ADMIN | `multipart/form-data` (rasm) |
| GET/PATCH/DELETE | `/studios/{id}/` | SUPER_ADMIN | |
| GET | `/dashboard/overview/` | SUPER_ADMIN | hisoblagichlar + oxirgi 5 profil |

**O‘chirish strategiyasi:**
- `PATCH {is_active:false}` — **deactivate** (qaytariladigan, sessiyalar bekor qilinadi).
- `DELETE` — **soft delete**: `deleted_at` o‘rnatiladi, `is_active=false`, ro‘yxatlardan yashiriladi, ma’lumot bazada qoladi. Hard delete API’da yo‘q.
- Mas’ul shaxsi bo‘lgan faol studiya bor foydalanuvchini o‘chirishga urinish → `409 conflict`.

**Rol cheklovlari:** Super Admin o‘zini o‘chira/deaktiv qila olmaydi; `role` ni `SUPER_ADMIN` ga o‘zgartirib bo‘lmaydi; `/users/` orqali `ADMIN` yaratib bo‘lmaydi (faqat `/admins/`).

---

## 4. Xavfsizlik

| Talab | Yechim |
|---|---|
| JWT | `djangorestframework-simplejwt`: access 10 daqiqa, refresh 7 kun, `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION` |
| Web auth | Tokenlar **httpOnly, Secure, SameSite=Lax** cookie’da; refresh cookie faqat `/api/v1/auth/` path’ida. localStorage’da hech narsa yo‘q |
| CSRF | Cookie orqali kelgan so‘rovlar uchun Django CSRF (double-submit `X-CSRFToken`) |
| Mobil (kelajak) | Xuddi shu endpointlar, `Authorization: Bearer` sarlavhasi; login’da `X-Client: mobile` → token body’da |
| Same-origin | Next.js `rewrites` orqali `/api/v1/*` → Django proksi qilinadi, shuning uchun cookie’lar first-party |
| CORS | `django-cors-headers` — faqat `CORS_ALLOWED_ORIGINS` env ro‘yxati |
| Rate limiting | DRF throttling: login 5/min/IP, umumiy 300/min/user |
| RBAC | `IsSuperAdmin` permission har bir boshqaruv view’da; testlar bilan isbotlanadi |
| Parol | Argon2 hasher + Django password validators |
| Rasm yuklash | ≤5 MB, faqat JPEG/PNG/WEBP, Pillow `verify()` + qayta kodlash (EXIF tozalanadi), UUID fayl nomi |
| Secrets | Faqat env (`django-environ`); `.env.example` da faqat namunalar |
| Audit | Har bir create/update/deactivate/delete/login/PINFL ko‘rish → `AuditLog` |
| Headerlar | HSTS, `X-Content-Type-Options`, CSP (Next.js), `Referrer-Policy` |

---

## 5. UI strukturasi (Liquid Control)

```
/login                     — glass karta, email + parol
/(panel) layout            — Sidebar (yig‘iladi: 260px ↔ 76px) + Topbar + PageTransition
  /dashboard               — 4 ta stat karta (animated counter) · oxirgi profillar · rollar taqsimoti
  /users                   — toolbar (search/filter/sort) · jadval · pagination · detail drawer · qo‘shish/tahrirlash modali
  /admins                  — karta grid / jadval · tasdiqlash modali
  /studios                 — karta grid · rasm yuklash bilan forma modali
  /settings                — profil, parol, mavzu
Har bir bo‘limda: Skeleton · Empty state · Error state (qayta urinish) · Toast (sonner)
Mobil kenglikda: sidebar → sheet (hamburger)
```

**Design tokenlar:** Primary `#2563EB`, Accent `#06B6D4`, Dark bg `#0F172A`, Light bg `#F8FAFC`, shrift Plus Jakarta Sans. Glass: `bg-white/5 dark` / `bg-white/70 light`, `backdrop-blur-xl`, `border-white/10`, radius 22–28px, soft glow `0 0 40px -10px rgb(6 182 212 / .5)`.

---

## 6. Motion tizimi (`src/motion/tokens.ts`)

| Token | Qiymat | Qayerda |
|---|---|---|
| `duration.fast` | 120 ms | tugma bosilishi, hover |
| `duration.base` | 220 ms | sahifa o‘tishi, toast |
| `duration.slow` | 360 ms | modal, drawer |
| `ease.standard` | `[0.2, 0.8, 0.2, 1]` | umumiy |
| `ease.exit` | `[0.4, 0, 1, 1]` | chiqish |
| `spring.sidebar` | stiffness 320, damping 32 | sidebar kengligi |
| `counter` | 900 ms, easeOut | statistik raqamlar |

Variantlar: `page` (fade + y:8), `modal` (scale .96→1 + fade, overlay blur), `drawer` (x:100%→0), `cardHover` (y:-3 + glow), `press` (scale .97), `stagger` (ro‘yxat elementlari 40 ms), `shake` (forma xatosi). Mavzu almashinuvi: View Transitions API bilan doiraviy ochilish, qo‘llab-quvvatlanmasa rang transition.
**Reduced motion:** `useReducedMotion()` + `MotionConfig reducedMotion="user"` — harakat o‘chadi, faqat opacity qoladi.

---

## 7. Testlar va tekshiruvlar

- Backend: `pytest` — har bir endpoint uchun rollar matritsasi (anonim / USER / STUDIO / ADMIN / SUPER_ADMIN), JSHSHIR validatsiya/maskalash/shifrlash, soft delete, token rotatsiyasi, upload validatsiya. `ruff` lint.
- Frontend: `tsc --noEmit`, `eslint`, `next build`; asosiy formalar uchun Zod sxema testlari (vitest).
