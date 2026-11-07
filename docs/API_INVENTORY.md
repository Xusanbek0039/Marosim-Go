# API inventarizatsiyasi va rol kontrakti (Developer Center — Phase 1–2)

> Holat: 2026-11-07. To'liq, avtomatik yangilanadigan jadval — [API_ENDPOINTS.md](API_ENDPOINTS.md)
> (`python manage.py export_api_endpoints`). Ko'rib chiqilgan kontrakt —
> [`backend/contracts/api_access_contract.json`](../backend/contracts/api_access_contract.json).

## 1. Audit natijasi (Phase 1)

| Qism | Topilgan holat |
|---|---|
| Routing | `config/urls.py` → `/api/v1/` (`config/api_v1.py`): `DefaultRouter` (users, admins, studios) + auth, dashboard, monitoring, admin/storage, health |
| View turlari | 3 ta `ModelViewSet` (`UserViewSet`, `AdminViewSet`, `StudioViewSet`), qolganlari `APIView` / `ListAPIView` |
| Autentifikatsiya | `CookieJWTAuthentication`: mobil `Authorization: Bearer`, web httpOnly cookie + `X-CSRFToken`. SimpleJWT, refresh rotation + blacklist |
| Default permission | `IsAuthenticated` (settings) |
| Permission class'lar | `AllowAny`, `IsAuthenticated`, `IsSuperAdmin`, `HasAdminPermission` (granular kodlar: `permissions_catalog.py`) |
| Rollar | `SUPER_ADMIN`, `ADMIN`, `STUDIO`, `USER` (`accounts.Role`) + hujjatda `PUBLIC` (auth talab qilmaydi) |
| StudioMembership | Model bor (OWNER/MANAGER/OPERATOR/VIDEOGRAPHER), **API yo'q** |
| OpenAPI | drf-spectacular 0.30, `MarosimAutoSchema` (`x-access`, standart xato javoblari) |
| Monitoring | `RequestLog` middleware, `/monitoring/overview|logs|endpoints/` (katalog OpenAPI'dan avtomatik) |
| Testlar | 186 ta (Phase 2 dan oldin) |

**Operatsiyalar: 36** — PUBLIC 8 · USER 2 · STUDIO 2 · ADMIN 14 (ruxsat kodi bilan) · SUPER_ADMIN 28.

### Aniqlangan kamchiliklar va qarorlar

| # | Kamchilik | Hal qilinishi |
|---|---|---|
| 1 | `/auth/me/` `roles: []` deb ko'rsatilardi — aslida 4 ta rol ham kiradi | `IsAuthenticated` → `USER, STUDIO, ADMIN, SUPER_ADMIN` |
| 2 | Noma'lum permission class jimgina "istalgan foydalanuvchi" deb talqin qilinardi | `REVIEW_REQUIRED`, rollar bo'sh, `auth_type=UNKNOWN` |
| 3 | `&` / `\|` kompozitsiyalari va object-level tekshiruv hisobga olinmasdi | Kombinatsiya qilinadi; `has_object_permission` bo'lsa ownership hujjati majburiy |
| 4 | Ma'lumot doirasi (queryset filtrlari) va qo'shimcha shartlar hujjatlashtirilmagan | `access_notes` (view yonida) + har biri uchun test |
| 5 | 16 ta operatsiyada `summary` yo'q edi | `extend_schema_view` bilan to'ldirildi; endi `MISSING` → test fail |
| 6 | Rol hujjati va haqiqiy permission o'rtasida avtomatik tekshiruv yo'q edi | Runtime matritsa (36 × 6 chaqiruvchi) + kontrakt snapshot |
| 7 | CI yo'q edi | `.github/workflows/backend-ci.yml` |

### Alohida e'tibor talab qiladigan endpointlar

| Endpoint | Rol | Izoh |
|---|---|---|
| `GET /admin/storage/google/callback/` | PUBLIC | JWT yo'q (Google redirect). Faqat ulashni boshlagan faol SUPER_ADMIN uchun yakunlanadi: bir martalik `state` + httpOnly binding cookie |
| `POST /auth/refresh/`, `/auth/logout/` | PUBLIC | Access token kerak emas, refresh token kerak (mobil: body, web: cookie + CSRF) |
| `GET /dashboard/overview/` | ADMIN (`dashboard.view`), SUPER_ADMIN | `recent_profiles` faqat `users.view` bilan to'ladi; ADMIN profillari faqat SUPER_ADMIN'ga |
| `/users/*` | ADMIN (kod), SUPER_ADMIN | Faqat USER/STUDIO hisoblar; ADMIN/SUPER_ADMIN → 404 |
| `/admins/*` | SUPER_ADMIN | ADMIN hech qachon (barcha kodlar bilan ham) kira olmaydi |

### Mobil ilova qamrovi (mavjud ↔ rejalashtirilgan)

| Bo'lim | Mavjud (ishlaydi) | Hali yo'q (PLANNED — katalogga real endpoint sifatida kiritilmaydi) |
|---|---|---|
| USER | register, login, refresh, logout, me (GET/PATCH) | my ceremonies, ceremony details, photos, videos |
| STUDIO | login, refresh, logout, me | studio profile, ceremonies CRUD, bride/groom biriktirish, media upload/progress/retry, media management |

STUDIO roli uchun hozircha faqat auth + profil mavjud: `/studios/*` — bu **panel** (ADMIN/SUPER_ADMIN) API'si,
STUDIO roli unga kira olmaydi.

## 2. Rol kontrakti (Phase 2)

### Manba

```
DRF permission_classes ──► apps/accounts/access.py::resolve(view, method) ──► AccessPolicy
                                                        │
              view.access_notes (ownership, conditions) ┘
AccessPolicy ──► MarosimAutoSchema ──► OpenAPI x-* ──► catalog.build() ──► panel / docs / contract
```

Rollar faqat permission class'lardan chiqadi. Hech qachon URL yoki nomdan taxmin qilinmaydi.

### OpenAPI kengaytmalari (har bir operatsiyada)

| Kalit | Ma'nosi |
|---|---|
| `x-allowed-roles` | `PUBLIC` yoki `USER/STUDIO/ADMIN/SUPER_ADMIN` dan to'plam |
| `x-auth-type` | `NONE` · `JWT` · `UNKNOWN` |
| `x-required-permissions` | ADMIN uchun talab qilinadigan granular kodlar (SUPER_ADMIN'da hammasi bor) |
| `x-ownership-scope` | Ma'lumot doirasi (queryset / object-level) |
| `x-access-conditions` | Qo'shimcha shartlar (CSRF, audit, throttle, biznes qoidalari) |
| `x-access-status` | `DERIVED` yoki `REVIEW_REQUIRED` (+ `x-access-policy.review_reasons`) |
| `x-access-policy` | To'liq siyosat (yuqoridagilar + `role_requirements`, `permission_classes`) |
| `x-documentation` | `DOCUMENTED` / `MISSING` + yetishmayotgan qismlar |
| `x-api-version` | `v1` |
| `x-access` | Eski qisqa shakl (mavjud mijozlar uchun saqlangan) |

Bu metadata permission'ni **almashtirmaydi** — faqat uni tasvirlaydi.

### Holatlar alohida

| Tushuncha | Qayerdan | Ma'nosi |
|---|---|---|
| `access_status` | resolver | Rol avtomatik aniqlandimi (`DERIVED`) yoki odam tekshirishi kerakmi |
| `contract_status` | snapshot | `MATCHES_CONTRACT` · `NOT_IN_CONTRACT` · `CONTRACT_MISMATCH` · `REVIEW_REQUIRED` |
| `documentation_status` | schema | `DOCUMENTED` / `MISSING` |
| `status` (traffic) | RequestLog | `idle` / `healthy` / `degraded` / `failing` — ishlayotganini faqat shu ko'rsatadi |
| `deprecated` | schema | OpenAPI `deprecated` |

### CI'da nima fail bo'ladi (`tests/test_api_access_contract.py`)

1. **Runtime matritsa:** har bir operatsiya anonim, USER, STUDIO, ADMIN (kodsiz), ADMIN (kerakli kod bilan),
   SUPER_ADMIN sifatida chaqiriladi. DRF permission qatlamining qarori `x-allowed-roles` bilan solishtiriladi.
   Yangi endpoint avtomatik qo'shiladi. (Mutatsiya tekshiruvi: `HasAdminPermission` buzilganda 12 ta test fail bo'ldi.)
2. **Snapshot:** jonli metadata + schema fingerprint `contracts/api_access_contract.json` ga teng bo'lishi shart.
3. **Gigiyena:** `REVIEW_REQUIRED` yo'q, har bir operatsiya `DOCUMENTED`, autentifikatsiyali endpoint PUBLIC emas.
4. **Ownership:** `ownership_scope` e'lon qilgan har bir operatsiya `OWNERSHIP_TESTS` dagi test bilan tasdiqlangan.

## 3. Yangi endpoint qo'shish standarti

1. Permission class'ni aniq yozing. Yangi custom class → `access_grant(view)` metodini qo'shing:
   ```python
   def access_grant(self, view):
       from apps.accounts.access import Grant
       return Grant(frozenset({"STUDIO"}))  # ADMIN kod bilan: requirements={"ADMIN": frozenset({"x.view"})}
   ```
   `access_grant` bo'lmasa endpoint `REVIEW_REQUIRED` bo'ladi va CI fail bo'ladi.
2. Ma'lumot doirasi / object-level qoida bo'lsa — view'da:
   ```python
   access_notes = {"*": AccessNote(ownership="..."), "create": AccessNote(conditions=("...",))}
   ```
   (kalit: `"*"`, action nomi yoki kichik harfli HTTP metod) va `OWNERSHIP_TESTS` ga test qo'shing.
3. `@extend_schema(summary=..., request=..., responses=...)` — serializer bilan.
4. `python manage.py api_contract --write`, `python manage.py export_api_endpoints` → diff'ni ko'rib chiqing
   (bu API changelog yozuvi uchun asos).
5. URL / method / schema'ni buzadigan o'zgarish → yangi versiya (`/api/v2/`), eskisi `deprecated`.
