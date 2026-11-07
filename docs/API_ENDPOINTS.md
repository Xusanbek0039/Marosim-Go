# API endpointlar

> Avtomatik yaratilgan: `python manage.py export_api_endpoints` (OpenAPI'dan). Qo'lda tahrirlamang.
> Rollar DRF permission class'laridan olinadi (`apps/accounts/access.py`) va
> `tests/test_api_access_contract.py` da har bir rol bilan haqiqiy so'rov orqali tekshiriladi.
> Batafsil: Swagger `/api/v1/docs/`, panel → API Monitoring → Endpointlar.

| Metod | Yo'l | Tavsif | Rollar | Ruxsat kodi (ADMIN) | Auth | Ma'lumot doirasi | Holat |
|---|---|---|---|---|---|---|---|
| GET | `/api/v1/admin/storage/google/callback/` | Google OAuth callback (brauzer redirect) | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/admin/storage/google/connect/` | Google Drive'ni ulashni boshlash | SUPER_ADMIN | — | JWT | — | OK |
| POST | `/api/v1/admin/storage/google/disconnect/` | Google Drive'ni uzish | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/admin/storage/google/status/` | Google Drive ulanish holati | SUPER_ADMIN | — | JWT | — | OK |
| POST | `/api/v1/admin/storage/google/test/` | Ulanishni tekshirish | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/admins/` | Adminlar ro'yxati | SUPER_ADMIN | — | JWT | Faqat ADMIN rolidagi, o'chirilmagan hisoblar (get_queryset). | OK |
| POST | `/api/v1/admins/` | Admin qo'shish | SUPER_ADMIN | — | JWT | Faqat ADMIN rolidagi, o'chirilmagan hisoblar (get_queryset). | OK |
| GET | `/api/v1/admins/permissions/` | Adminlarga beriladigan ruxsatlar ro'yxati | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/admins/{id}/` | Admin ma'lumotlari | SUPER_ADMIN | — | JWT | Faqat ADMIN rolidagi, o'chirilmagan hisoblar (get_queryset). | OK |
| PATCH | `/api/v1/admins/{id}/` | Adminni tahrirlash (ruxsatlar bilan) | SUPER_ADMIN | — | JWT | Faqat ADMIN rolidagi, o'chirilmagan hisoblar (get_queryset). | OK |
| DELETE | `/api/v1/admins/{id}/` | Adminni o'chirish (soft delete) | SUPER_ADMIN | — | JWT | Faqat ADMIN rolidagi, o'chirilmagan hisoblar (get_queryset). | OK |
| GET | `/api/v1/admins/{id}/pinfl/` | Adminning to'liq JSHSHIRi (audit qilinadi) | SUPER_ADMIN | — | JWT | Faqat ADMIN rolidagi, o'chirilmagan hisoblar (get_queryset). | OK |
| POST | `/api/v1/admins/{id}/verify-phone/` | Telefon raqamini qo'lda tasdiqlash | SUPER_ADMIN | — | JWT | Faqat ADMIN rolidagi, o'chirilmagan hisoblar (get_queryset). | OK |
| GET | `/api/v1/auth/csrf/` | CSRF cookie olish (web panel) | PUBLIC | — | NONE | — | OK |
| POST | `/api/v1/auth/login/` | Tizimga kirish (telefon + parol) | PUBLIC | — | NONE | — | OK |
| POST | `/api/v1/auth/logout/` | Tizimdan chiqish | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/auth/me/` | Mening profilim | USER, STUDIO, VENUE_OWNER, ADMIN, SUPER_ADMIN | — | JWT | Faqat chaqiruvchining o'z hisobi (request.user). | OK |
| PATCH | `/api/v1/auth/me/` | Profilni tahrirlash | USER, STUDIO, VENUE_OWNER, ADMIN, SUPER_ADMIN | — | JWT | Faqat chaqiruvchining o'z hisobi (request.user). | OK |
| POST | `/api/v1/auth/refresh/` | Tokenni yangilash (rotation) | PUBLIC | — | NONE | — | OK |
| POST | `/api/v1/auth/register/` | Ro'yxatdan o'tish (telefon + parol) | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/ceremonies/` | Marosimlar ro'yxati | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| POST | `/api/v1/ceremonies/` | Marosim yaratish | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| GET | `/api/v1/ceremonies/{id}/` | Marosim ma'lumotlari | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| PATCH | `/api/v1/ceremonies/{id}/` | Marosimni tahrirlash | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| GET | `/api/v1/ceremonies/{id}/owners/` | Marosim egalari va egalik takliflari | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| POST | `/api/v1/ceremonies/{id}/owners/invite/` | Marosim egasini telefon yoki JSHSHIR orqali taklif qilish | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| GET | `/api/v1/ceremonies/{id}/participants/` | Marosim ishtirokchilari (deprecated — /owners/) | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | Deprecated |
| POST | `/api/v1/ceremonies/{id}/participants/` | Ishtirokchini telefon orqali taklif qilish (deprecated — /owners/invite/) | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | Deprecated |
| DELETE | `/api/v1/ceremonies/{id}/participants/{participant_id}/` | Ishtirokchini olib tashlash (deprecated) | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | Deprecated |
| GET | `/api/v1/dashboard/overview/` | Dashboard statistikasi | ADMIN, SUPER_ADMIN | `dashboard.view` | JWT | — | OK |
| GET | `/api/v1/devcenter/changelog/` | Developer Center: API changelog | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/devcenter/endpoints/` | Developer Center: endpointlar (rol bo'yicha filtr) | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/devcenter/mobile/` | Developer Center: User / Studio mobil API | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/devcenter/overview/` | Developer Center: umumiy ko'rinish | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/health/live/` | Liveness — jarayon ishlayaptimi | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/health/ready/` | Readiness — bog'liqliklar (database, cache) tayyormi | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/me/ceremonies/` | Menga biriktirilgan marosimlar | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| GET | `/api/v1/me/ceremonies/{id}/` | Menga biriktirilgan marosim | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| GET | `/api/v1/me/ceremonies/{id}/invitations/` | Marosim takliflari tarixi | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| POST | `/api/v1/me/ceremonies/{id}/invitations/` | VIEWER yoki OWNER taklifi yuborish (telefon / JSHSHIR) | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| POST | `/api/v1/me/ceremonies/{id}/invitations/{invitation_id}/resend/` | Taklifni qayta yuborish (muddat yangilanadi) | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| POST | `/api/v1/me/ceremonies/{id}/invitations/{invitation_id}/revoke/` | O'zi yuborgan taklifni bekor qilish | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| POST | `/api/v1/me/ceremonies/{id}/leave/` | Marosimdan chiqish (egalik / ko'rish huquqidan voz kechish) | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| GET | `/api/v1/me/ceremonies/{id}/members/` | Marosim egalari va ko'ruvchilari | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| GET | `/api/v1/me/ceremonies/{id}/owner-requests/` | Tasdiq kutayotgan yangi egalar | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| POST | `/api/v1/me/ceremonies/{id}/owner-requests/{request_id}/approve/` | Yangi egani tasdiqlash | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| POST | `/api/v1/me/ceremonies/{id}/owner-requests/{request_id}/reject/` | Yangi egani rad etish | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| POST | `/api/v1/me/ceremonies/{id}/viewers/{access_id}/revoke/` | O'zi bergan ko'rish huquqini bekor qilish | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| GET | `/api/v1/me/invitations/` | Menga kelgan takliflar | USER | — | JWT | Faqat so'rovchining telefoni yoki JSHSHIRiga (hash bo'yicha aniq moslik) yuborilgan, javob kutilayotgan va muddati o'tmagan takliflar; boshqasi 404. | OK |
| GET | `/api/v1/me/invitations/{id}/` | Taklif tafsilotlari | USER | — | JWT | Faqat so'rovchining telefoni yoki JSHSHIRiga (hash bo'yicha aniq moslik) yuborilgan, javob kutilayotgan va muddati o'tmagan takliflar; boshqasi 404. | OK |
| POST | `/api/v1/me/invitations/{id}/accept/` | Taklifni qabul qilish | USER | — | JWT | Faqat so'rovchining telefoni yoki JSHSHIRiga (hash bo'yicha aniq moslik) yuborilgan, javob kutilayotgan va muddati o'tmagan takliflar; boshqasi 404. | OK |
| POST | `/api/v1/me/invitations/{id}/decline/` | Taklifni rad etish | USER | — | JWT | Faqat so'rovchining telefoni yoki JSHSHIRiga (hash bo'yicha aniq moslik) yuborilgan, javob kutilayotgan va muddati o'tmagan takliflar; boshqasi 404. | OK |
| GET | `/api/v1/monitoring/endpoints/` | API endpointlar katalogi (OpenAPI'dan avtomatik) | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/monitoring/logs/` | So'rovlar jurnali | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/monitoring/overview/` | API statistikasi (real so'rovlar asosida) | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/studios/` | Studiyalar ro'yxati | ADMIN, SUPER_ADMIN | `studios.view` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| POST | `/api/v1/studios/` | Studiya qo'shish | ADMIN, SUPER_ADMIN | `studios.create` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| GET | `/api/v1/studios/me/` | Mening studiyalarim | STUDIO | — | JWT | Faqat so'rovchining faol a'zoliklari va ularning studiyalari. | OK |
| GET | `/api/v1/studios/me/ceremonies/` | Mening studiyamning marosimlari | STUDIO | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| GET | `/api/v1/studios/{id}/` | Studiya ma'lumotlari | ADMIN, SUPER_ADMIN | `studios.view` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| PATCH | `/api/v1/studios/{id}/` | Studiyani tahrirlash | ADMIN, SUPER_ADMIN | `studios.update` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| DELETE | `/api/v1/studios/{id}/` | Studiyani o'chirish (soft delete) | ADMIN, SUPER_ADMIN | `studios.delete` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| GET | `/api/v1/users/` | Mijozlar ro'yxati (USER, STUDIO, VENUE_OWNER) | ADMIN, SUPER_ADMIN | `users.view` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| POST | `/api/v1/users/` | Mijoz qo'shish | ADMIN, SUPER_ADMIN | `users.create` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| GET | `/api/v1/users/{id}/` | Mijoz ma'lumotlari | ADMIN, SUPER_ADMIN | `users.view` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| PATCH | `/api/v1/users/{id}/` | Mijozni tahrirlash | ADMIN, SUPER_ADMIN | `users.update` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| DELETE | `/api/v1/users/{id}/` | Mijozni o'chirish (soft delete) | ADMIN, SUPER_ADMIN | `users.delete` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| GET | `/api/v1/users/{id}/pinfl/` | To'liq JSHSHIR (audit qilinadi) | ADMIN, SUPER_ADMIN | `users.view_pinfl` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| POST | `/api/v1/users/{id}/verify-phone/` | Telefon raqamini qo'lda tasdiqlash | ADMIN, SUPER_ADMIN | `users.update` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| GET | `/api/v1/venue-owner/venues/` | Mening to'yxonalarim | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| POST | `/api/v1/venue-owner/venues/` | To'yxona yaratish (PRIVATE holatda) | VENUE_OWNER | — | JWT | — | OK |
| GET | `/api/v1/venue-owner/venues/{id}/` | To'yxona ma'lumotlari (egasi uchun) | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| PATCH | `/api/v1/venue-owner/venues/{id}/` | To'yxonani tahrirlash | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| GET | `/api/v1/venue-owner/venues/{id}/halls/` | To'yxona zallari | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| POST | `/api/v1/venue-owner/venues/{id}/halls/` | Zal qo'shish | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| PATCH | `/api/v1/venue-owner/venues/{id}/halls/{hall_id}/` | Zalni tahrirlash | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |

## Rollar bo'yicha

### PUBLIC (8)

* `GET /api/v1/admin/storage/google/callback/` — Google OAuth callback (brauzer redirect)
* `GET /api/v1/auth/csrf/` — CSRF cookie olish (web panel)
* `POST /api/v1/auth/login/` — Tizimga kirish (telefon + parol)
* `POST /api/v1/auth/logout/` — Tizimdan chiqish
* `POST /api/v1/auth/refresh/` — Tokenni yangilash (rotation)
* `POST /api/v1/auth/register/` — Ro'yxatdan o'tish (telefon + parol)
* `GET /api/v1/health/live/` — Liveness — jarayon ishlayaptimi
* `GET /api/v1/health/ready/` — Readiness — bog'liqliklar (database, cache) tayyormi

### USER (18)

* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/me/ceremonies/` — Menga biriktirilgan marosimlar
* `GET /api/v1/me/ceremonies/{id}/` — Menga biriktirilgan marosim
* `GET /api/v1/me/ceremonies/{id}/invitations/` — Marosim takliflari tarixi
* `POST /api/v1/me/ceremonies/{id}/invitations/` — VIEWER yoki OWNER taklifi yuborish (telefon / JSHSHIR)
* `POST /api/v1/me/ceremonies/{id}/invitations/{invitation_id}/resend/` — Taklifni qayta yuborish (muddat yangilanadi)
* `POST /api/v1/me/ceremonies/{id}/invitations/{invitation_id}/revoke/` — O'zi yuborgan taklifni bekor qilish
* `POST /api/v1/me/ceremonies/{id}/leave/` — Marosimdan chiqish (egalik / ko'rish huquqidan voz kechish)
* `GET /api/v1/me/ceremonies/{id}/members/` — Marosim egalari va ko'ruvchilari
* `GET /api/v1/me/ceremonies/{id}/owner-requests/` — Tasdiq kutayotgan yangi egalar
* `POST /api/v1/me/ceremonies/{id}/owner-requests/{request_id}/approve/` — Yangi egani tasdiqlash
* `POST /api/v1/me/ceremonies/{id}/owner-requests/{request_id}/reject/` — Yangi egani rad etish
* `POST /api/v1/me/ceremonies/{id}/viewers/{access_id}/revoke/` — O'zi bergan ko'rish huquqini bekor qilish
* `GET /api/v1/me/invitations/` — Menga kelgan takliflar
* `GET /api/v1/me/invitations/{id}/` — Taklif tafsilotlari
* `POST /api/v1/me/invitations/{id}/accept/` — Taklifni qabul qilish
* `POST /api/v1/me/invitations/{id}/decline/` — Taklifni rad etish

### STUDIO (13)

* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/ceremonies/` — Marosimlar ro'yxati
* `POST /api/v1/ceremonies/` — Marosim yaratish
* `GET /api/v1/ceremonies/{id}/` — Marosim ma'lumotlari
* `PATCH /api/v1/ceremonies/{id}/` — Marosimni tahrirlash
* `GET /api/v1/ceremonies/{id}/owners/` — Marosim egalari va egalik takliflari
* `POST /api/v1/ceremonies/{id}/owners/invite/` — Marosim egasini telefon yoki JSHSHIR orqali taklif qilish
* `GET /api/v1/ceremonies/{id}/participants/` — Marosim ishtirokchilari (deprecated — /owners/)
* `POST /api/v1/ceremonies/{id}/participants/` — Ishtirokchini telefon orqali taklif qilish (deprecated — /owners/invite/)
* `DELETE /api/v1/ceremonies/{id}/participants/{participant_id}/` — Ishtirokchini olib tashlash (deprecated)
* `GET /api/v1/studios/me/` — Mening studiyalarim
* `GET /api/v1/studios/me/ceremonies/` — Mening studiyamning marosimlari

### VENUE_OWNER (9)

* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/venue-owner/venues/` — Mening to'yxonalarim
* `POST /api/v1/venue-owner/venues/` — To'yxona yaratish (PRIVATE holatda)
* `GET /api/v1/venue-owner/venues/{id}/` — To'yxona ma'lumotlari (egasi uchun)
* `PATCH /api/v1/venue-owner/venues/{id}/` — To'yxonani tahrirlash
* `GET /api/v1/venue-owner/venues/{id}/halls/` — To'yxona zallari
* `POST /api/v1/venue-owner/venues/{id}/halls/` — Zal qo'shish
* `PATCH /api/v1/venue-owner/venues/{id}/halls/{hall_id}/` — Zalni tahrirlash

### ADMIN (15)

* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/dashboard/overview/` — Dashboard statistikasi
* `GET /api/v1/studios/` — Studiyalar ro'yxati
* `POST /api/v1/studios/` — Studiya qo'shish
* `GET /api/v1/studios/{id}/` — Studiya ma'lumotlari
* `PATCH /api/v1/studios/{id}/` — Studiyani tahrirlash
* `DELETE /api/v1/studios/{id}/` — Studiyani o'chirish (soft delete)
* `GET /api/v1/users/` — Mijozlar ro'yxati (USER, STUDIO, VENUE_OWNER)
* `POST /api/v1/users/` — Mijoz qo'shish
* `GET /api/v1/users/{id}/` — Mijoz ma'lumotlari
* `PATCH /api/v1/users/{id}/` — Mijozni tahrirlash
* `DELETE /api/v1/users/{id}/` — Mijozni o'chirish (soft delete)
* `GET /api/v1/users/{id}/pinfl/` — To'liq JSHSHIR (audit qilinadi)
* `POST /api/v1/users/{id}/verify-phone/` — Telefon raqamini qo'lda tasdiqlash

### SUPER_ADMIN (43)

* `GET /api/v1/admin/storage/google/connect/` — Google Drive'ni ulashni boshlash
* `POST /api/v1/admin/storage/google/disconnect/` — Google Drive'ni uzish
* `GET /api/v1/admin/storage/google/status/` — Google Drive ulanish holati
* `POST /api/v1/admin/storage/google/test/` — Ulanishni tekshirish
* `GET /api/v1/admins/` — Adminlar ro'yxati
* `POST /api/v1/admins/` — Admin qo'shish
* `GET /api/v1/admins/permissions/` — Adminlarga beriladigan ruxsatlar ro'yxati
* `GET /api/v1/admins/{id}/` — Admin ma'lumotlari
* `PATCH /api/v1/admins/{id}/` — Adminni tahrirlash (ruxsatlar bilan)
* `DELETE /api/v1/admins/{id}/` — Adminni o'chirish (soft delete)
* `GET /api/v1/admins/{id}/pinfl/` — Adminning to'liq JSHSHIRi (audit qilinadi)
* `POST /api/v1/admins/{id}/verify-phone/` — Telefon raqamini qo'lda tasdiqlash
* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/ceremonies/` — Marosimlar ro'yxati
* `POST /api/v1/ceremonies/` — Marosim yaratish
* `GET /api/v1/ceremonies/{id}/` — Marosim ma'lumotlari
* `PATCH /api/v1/ceremonies/{id}/` — Marosimni tahrirlash
* `GET /api/v1/ceremonies/{id}/owners/` — Marosim egalari va egalik takliflari
* `POST /api/v1/ceremonies/{id}/owners/invite/` — Marosim egasini telefon yoki JSHSHIR orqali taklif qilish
* `GET /api/v1/ceremonies/{id}/participants/` — Marosim ishtirokchilari (deprecated — /owners/)
* `POST /api/v1/ceremonies/{id}/participants/` — Ishtirokchini telefon orqali taklif qilish (deprecated — /owners/invite/)
* `DELETE /api/v1/ceremonies/{id}/participants/{participant_id}/` — Ishtirokchini olib tashlash (deprecated)
* `GET /api/v1/dashboard/overview/` — Dashboard statistikasi
* `GET /api/v1/devcenter/changelog/` — Developer Center: API changelog
* `GET /api/v1/devcenter/endpoints/` — Developer Center: endpointlar (rol bo'yicha filtr)
* `GET /api/v1/devcenter/mobile/` — Developer Center: User / Studio mobil API
* `GET /api/v1/devcenter/overview/` — Developer Center: umumiy ko'rinish
* `GET /api/v1/monitoring/endpoints/` — API endpointlar katalogi (OpenAPI'dan avtomatik)
* `GET /api/v1/monitoring/logs/` — So'rovlar jurnali
* `GET /api/v1/monitoring/overview/` — API statistikasi (real so'rovlar asosida)
* `GET /api/v1/studios/` — Studiyalar ro'yxati
* `POST /api/v1/studios/` — Studiya qo'shish
* `GET /api/v1/studios/{id}/` — Studiya ma'lumotlari
* `PATCH /api/v1/studios/{id}/` — Studiyani tahrirlash
* `DELETE /api/v1/studios/{id}/` — Studiyani o'chirish (soft delete)
* `GET /api/v1/users/` — Mijozlar ro'yxati (USER, STUDIO, VENUE_OWNER)
* `POST /api/v1/users/` — Mijoz qo'shish
* `GET /api/v1/users/{id}/` — Mijoz ma'lumotlari
* `PATCH /api/v1/users/{id}/` — Mijozni tahrirlash
* `DELETE /api/v1/users/{id}/` — Mijozni o'chirish (soft delete)
* `GET /api/v1/users/{id}/pinfl/` — To'liq JSHSHIR (audit qilinadi)
* `POST /api/v1/users/{id}/verify-phone/` — Telefon raqamini qo'lda tasdiqlash

## Qo'shimcha shartlar

* `GET /api/v1/admin/storage/google/callback/`
  * JWT talab qilinmaydi (Google brauzer redirect'i), lekin faqat ulashni boshlagan faol SUPER_ADMIN uchun yakunlanadi: bir martalik `state` + brauzerga bog'lovchi httpOnly cookie
* `GET /api/v1/admins/{id}/pinfl/`
  * Har bir ko'rish audit qilinadi (PINFL_REVEAL)
* `POST /api/v1/auth/login/`
  * Web (cookie) rejimida X-CSRFToken talab qilinadi
  * Ketma-ket xatolardan so'ng hisob vaqtincha bloklanadi (429 account_locked)
* `POST /api/v1/auth/logout/`
  * Refresh token bo'lsa blacklistga qo'shiladi; web rejimida CSRF talab qilinadi
* `PATCH /api/v1/auth/me/`
  * Faqat first_name, last_name, profile_picture, address o'zgaradi
* `POST /api/v1/auth/refresh/`
  * Access token kerak emas, lekin amaldagi refresh token talab qilinadi (mobil: body, web: cookie+CSRF)
  * Ishlatilgan refresh tokenni qayta yuborish barcha sessiyalarni bekor qiladi
* `POST /api/v1/auth/register/`
  * Yaratilgan hisob roli har doim USER
  * Tokenlar faqat `X-Client: mobile` uchun qaytariladi
  * Bot himoyasi yoqilgan bo'lsa bot-token sarlavhasi talab qilinadi
* `POST /api/v1/ceremonies/`
  * STUDIO a'zoligi OWNER yoki MANAGER bo'lishi shart (UPLOADER — faqat ko'rish).
  * SUPER_ADMIN studio_id ni ko'rsatishi shart.
* `PATCH /api/v1/ceremonies/{id}/`
  * STUDIO a'zoligi OWNER yoki MANAGER bo'lishi shart (UPLOADER — faqat ko'rish).
  * Holat o'tishlari cheklangan.
* `POST /api/v1/ceremonies/{id}/owners/invite/`
  * STUDIO a'zoligi OWNER yoki MANAGER bo'lishi shart (UPLOADER — faqat ko'rish).
  * Marosimda egalar bo'lsa, yangi ega ularning tasdig'idan keyin ochiladi.
  * JSHSHIR orqali faqat egalar bor bo'lganda (birinchi egalar — telefon orqali).
  * Javob oluvchining akkaunti bor-yo'qligiga bog'liq emas; telefon/JSHSHIR faqat maskalangan qaytadi.
* `GET /api/v1/ceremonies/{id}/participants/`
  * Deprecated: /owners/ ishlating.
  * POST: STUDIO a'zoligi OWNER yoki MANAGER bo'lishi shart (UPLOADER — faqat ko'rish).
* `POST /api/v1/ceremonies/{id}/participants/`
  * Deprecated: /owners/ ishlating.
  * POST: STUDIO a'zoligi OWNER yoki MANAGER bo'lishi shart (UPLOADER — faqat ko'rish).
* `DELETE /api/v1/ceremonies/{id}/participants/{participant_id}/`
  * Deprecated.
  * Javob kutilayotgan taklif: studiya OWNER/MANAGER bekor qiladi.
  * Tasdiqlangan egani faqat SUPER_ADMIN olib tashlaydi.
* `GET /api/v1/dashboard/overview/`
  * `recent_profiles` faqat `users.view` ruxsati bo'lsa to'ldiriladi, aks holda bo'sh
  * ADMIN profillari `recent_profiles` da faqat SUPER_ADMIN uchun ko'rinadi
* `GET /api/v1/me/ceremonies/{id}/invitations/`
  * Faqat marosimning ACCEPTED egasi (CEREMONY_OWNER); ko'ruvchi — 403.
  * POST VIEWER: darhol taklif; POST OWNER: qabul qilingach boshqa egalar tasdiqlaydi.
  * JSHSHIR — faqat identifikator, autentifikatsiya emas.
  * Javob oluvchining akkaunti bor-yo'qligiga bog'liq emas; telefon/JSHSHIR faqat maskalangan qaytadi.
* `POST /api/v1/me/ceremonies/{id}/invitations/`
  * Faqat marosimning ACCEPTED egasi (CEREMONY_OWNER); ko'ruvchi — 403.
  * POST VIEWER: darhol taklif; POST OWNER: qabul qilingach boshqa egalar tasdiqlaydi.
  * JSHSHIR — faqat identifikator, autentifikatsiya emas.
  * Javob oluvchining akkaunti bor-yo'qligiga bog'liq emas; telefon/JSHSHIR faqat maskalangan qaytadi.
* `POST /api/v1/me/ceremonies/{id}/invitations/{invitation_id}/resend/`
  * Faqat marosimning ACCEPTED egasi (CEREMONY_OWNER); ko'ruvchi — 403.
  * Faqat taklifni o'zi yuborgan ega.
* `POST /api/v1/me/ceremonies/{id}/invitations/{invitation_id}/revoke/`
  * Faqat marosimning ACCEPTED egasi (CEREMONY_OWNER); ko'ruvchi — 403.
  * Faqat taklifni o'zi yuborgan ega.
* `POST /api/v1/me/ceremonies/{id}/leave/`
  * Ega yoki ko'ruvchi o'z huquqidan voz kechadi.
* `GET /api/v1/me/ceremonies/{id}/members/`
  * Faqat marosimning ACCEPTED egasi (CEREMONY_OWNER); ko'ruvchi — 403.
* `GET /api/v1/me/ceremonies/{id}/owner-requests/`
  * Faqat marosimning ACCEPTED egasi (CEREMONY_OWNER); ko'ruvchi — 403.
* `POST /api/v1/me/ceremonies/{id}/owner-requests/{request_id}/approve/`
  * Faqat marosimning ACCEPTED egasi (CEREMONY_OWNER); ko'ruvchi — 403.
  * Faqat so'rov ochilganda ACCEPTED bo'lgan va hozir ham ega bo'lganlar.
* `POST /api/v1/me/ceremonies/{id}/owner-requests/{request_id}/reject/`
  * Faqat marosimning ACCEPTED egasi (CEREMONY_OWNER); ko'ruvchi — 403.
  * Faqat so'rov ochilganda ACCEPTED bo'lgan va hozir ham ega bo'lganlar.
* `POST /api/v1/me/ceremonies/{id}/viewers/{access_id}/revoke/`
  * Faqat marosimning ACCEPTED egasi (CEREMONY_OWNER); ko'ruvchi — 403.
  * Faqat ko'rish huquqini o'zi bergan ega.
* `POST /api/v1/me/invitations/{id}/accept/`
  * OWNER taklifini qabul qilish uchun telefon tasdiqlangan bo'lishi shart.
  * Taklif qabul qilinmaguncha hech qanday kirish huquqi berilmaydi.
  * Muddati o'tgan — 410.
* `DELETE /api/v1/users/{id}/`
  * Faol studiyaning mas'ul shaxsini o'chirib bo'lmaydi (409 conflict)
* `GET /api/v1/users/{id}/pinfl/`
  * Har bir ko'rish audit qilinadi (PINFL_REVEAL)
  * Throttle: pinfl_reveal
* `POST /api/v1/venue-owner/venues/`
  * Yaratuvchi OWNER a'zo bo'ladi; standart 'Asosiy zal' ochiladi.
  * publication_status=PRIVATE, is_active — faqat admin o'zgartiradi.
* `PATCH /api/v1/venue-owner/venues/{id}/`
  * A'zolik roli `EDIT_PROFILE` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `GET /api/v1/venue-owner/venues/{id}/halls/`
  * POST: A'zolik roli `MANAGE_HALLS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `POST /api/v1/venue-owner/venues/{id}/halls/`
  * POST: A'zolik roli `MANAGE_HALLS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `PATCH /api/v1/venue-owner/venues/{id}/halls/{hall_id}/`
  * A'zolik roli `MANAGE_HALLS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.

## Rejalashtirilgan (PLANNED — hali ishlamaydi)

> `apps/devcenter/planned.py`. Yuqoridagi jadval — faqat haqiqatda ishlaydigan endpointlar.
> CEREMONY_OWNER / CEREMONY_VIEWER — global rol emas, marosimga xos huquq.

| Bosqich | Metod | Yo'l | Tavsif | Kim | Shart |
|---|---|---|---|---|---|
| D | POST | `/api/v1/ceremonies/{id}/media/uploads/` | Resumable media upload sessiyasi | STUDIO | Studiya a'zoligi OWNER/MANAGER/UPLOADER |
| D | GET | `/api/v1/ceremonies/{id}/media/` | Yuklangan fayllar va holati | STUDIO | — |
| E | GET | `/api/v1/me/ceremonies/{id}/media/` | Media galereya | CEREMONY_OWNER, CEREMONY_VIEWER | USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi) |
| E | GET | `/api/v1/me/ceremonies/{id}/media/{media_id}/thumbnail/` | Kichik rasm | CEREMONY_OWNER, CEREMONY_VIEWER | USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi); Drive fayli hech qachon public qilinmaydi |
| E | GET | `/api/v1/me/ceremonies/{id}/media/{media_id}/preview/` | Ko'rib chiqish | CEREMONY_OWNER, CEREMONY_VIEWER | USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi); Drive fayli hech qachon public qilinmaydi |
| E | GET | `/api/v1/me/ceremonies/{id}/media/{media_id}/stream/` | Video oqimi (Range) | CEREMONY_OWNER, CEREMONY_VIEWER | USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi); Drive fayli hech qachon public qilinmaydi |
| E | GET | `/api/v1/me/ceremonies/{id}/media/{media_id}/download/` | Asl faylni yuklab olish | CEREMONY_OWNER, CEREMONY_VIEWER | USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi); Drive fayli hech qachon public qilinmaydi |
| F | GET | `/api/v1/admin/ceremonies/` | Barcha marosimlar monitoringi | SUPER_ADMIN | — |
| F | GET | `/api/v1/admin/ceremonies/{id}/` | Marosim: egalar, takliflar, ko'ruvchilar, media, tarix | SUPER_ADMIN | Maxfiy maydonlar faqat audit qilinadigan alohida amal orqali |
