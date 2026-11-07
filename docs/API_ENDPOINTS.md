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
| GET | `/api/v1/auth/me/` | Mening profilim | USER, STUDIO, ADMIN, SUPER_ADMIN | — | JWT | Faqat chaqiruvchining o'z hisobi (request.user). | OK |
| PATCH | `/api/v1/auth/me/` | Profilni tahrirlash | USER, STUDIO, ADMIN, SUPER_ADMIN | — | JWT | Faqat chaqiruvchining o'z hisobi (request.user). | OK |
| POST | `/api/v1/auth/refresh/` | Tokenni yangilash (rotation) | PUBLIC | — | NONE | — | OK |
| POST | `/api/v1/auth/register/` | Ro'yxatdan o'tish (telefon + parol) | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/ceremonies/` | Marosimlar ro'yxati | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| POST | `/api/v1/ceremonies/` | Marosim yaratish | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| GET | `/api/v1/ceremonies/{id}/` | Marosim ma'lumotlari | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| PATCH | `/api/v1/ceremonies/{id}/` | Marosimni tahrirlash | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| GET | `/api/v1/ceremonies/{id}/participants/` | Marosim ishtirokchilari | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| POST | `/api/v1/ceremonies/{id}/participants/` | Ishtirokchini telefon orqali taklif qilish | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| DELETE | `/api/v1/ceremonies/{id}/participants/{participant_id}/` | Ishtirokchini olib tashlash (kirish bekor qilinadi) | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| GET | `/api/v1/dashboard/overview/` | Dashboard statistikasi | ADMIN, SUPER_ADMIN | `dashboard.view` | JWT | — | OK |
| GET | `/api/v1/devcenter/changelog/` | Developer Center: API changelog | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/devcenter/endpoints/` | Developer Center: endpointlar (rol bo'yicha filtr) | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/devcenter/mobile/` | Developer Center: User / Studio mobil API | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/devcenter/overview/` | Developer Center: umumiy ko'rinish | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/health/live/` | Liveness — jarayon ishlayaptimi | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/health/ready/` | Readiness — bog'liqliklar (database, cache) tayyormi | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/me/ceremonies/` | Menga biriktirilgan marosimlar | USER | — | JWT | Faqat so'rovchi ACTIVE ishtirokchi bo'lgan, DRAFT bo'lmagan marosimlar. | OK |
| GET | `/api/v1/me/ceremonies/{id}/` | Menga biriktirilgan marosim | USER | — | JWT | Faqat so'rovchi ACTIVE ishtirokchi bo'lgan, DRAFT bo'lmagan marosimlar. | OK |
| GET | `/api/v1/me/invitations/` | Menga kelgan takliflar | USER | — | JWT | Faqat so'rovchining telefon raqamiga yuborilgan takliflar. | OK |
| POST | `/api/v1/me/invitations/{id}/accept/` | Taklifni qabul qilish | USER | — | JWT | Faqat so'rovchining telefon raqamiga yuborilgan takliflar. | OK |
| POST | `/api/v1/me/invitations/{id}/decline/` | Taklifni rad etish | USER | — | JWT | Faqat so'rovchining telefon raqamiga yuborilgan takliflar. | OK |
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
| GET | `/api/v1/users/` | Mijozlar ro'yxati (USER, STUDIO) | ADMIN, SUPER_ADMIN | `users.view` | JWT | Faqat USER va STUDIO rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| POST | `/api/v1/users/` | Mijoz qo'shish | ADMIN, SUPER_ADMIN | `users.create` | JWT | Faqat USER va STUDIO rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| GET | `/api/v1/users/{id}/` | Mijoz ma'lumotlari | ADMIN, SUPER_ADMIN | `users.view` | JWT | Faqat USER va STUDIO rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| PATCH | `/api/v1/users/{id}/` | Mijozni tahrirlash | ADMIN, SUPER_ADMIN | `users.update` | JWT | Faqat USER va STUDIO rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| DELETE | `/api/v1/users/{id}/` | Mijozni o'chirish (soft delete) | ADMIN, SUPER_ADMIN | `users.delete` | JWT | Faqat USER va STUDIO rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| GET | `/api/v1/users/{id}/pinfl/` | To'liq JSHSHIR (audit qilinadi) | ADMIN, SUPER_ADMIN | `users.view_pinfl` | JWT | Faqat USER va STUDIO rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| POST | `/api/v1/users/{id}/verify-phone/` | Telefon raqamini qo'lda tasdiqlash | ADMIN, SUPER_ADMIN | `users.update` | JWT | Faqat USER va STUDIO rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |

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

### USER (7)

* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/me/ceremonies/` — Menga biriktirilgan marosimlar
* `GET /api/v1/me/ceremonies/{id}/` — Menga biriktirilgan marosim
* `GET /api/v1/me/invitations/` — Menga kelgan takliflar
* `POST /api/v1/me/invitations/{id}/accept/` — Taklifni qabul qilish
* `POST /api/v1/me/invitations/{id}/decline/` — Taklifni rad etish

### STUDIO (11)

* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/ceremonies/` — Marosimlar ro'yxati
* `POST /api/v1/ceremonies/` — Marosim yaratish
* `GET /api/v1/ceremonies/{id}/` — Marosim ma'lumotlari
* `PATCH /api/v1/ceremonies/{id}/` — Marosimni tahrirlash
* `GET /api/v1/ceremonies/{id}/participants/` — Marosim ishtirokchilari
* `POST /api/v1/ceremonies/{id}/participants/` — Ishtirokchini telefon orqali taklif qilish
* `DELETE /api/v1/ceremonies/{id}/participants/{participant_id}/` — Ishtirokchini olib tashlash (kirish bekor qilinadi)
* `GET /api/v1/studios/me/` — Mening studiyalarim
* `GET /api/v1/studios/me/ceremonies/` — Mening studiyamning marosimlari

### ADMIN (15)

* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/dashboard/overview/` — Dashboard statistikasi
* `GET /api/v1/studios/` — Studiyalar ro'yxati
* `POST /api/v1/studios/` — Studiya qo'shish
* `GET /api/v1/studios/{id}/` — Studiya ma'lumotlari
* `PATCH /api/v1/studios/{id}/` — Studiyani tahrirlash
* `DELETE /api/v1/studios/{id}/` — Studiyani o'chirish (soft delete)
* `GET /api/v1/users/` — Mijozlar ro'yxati (USER, STUDIO)
* `POST /api/v1/users/` — Mijoz qo'shish
* `GET /api/v1/users/{id}/` — Mijoz ma'lumotlari
* `PATCH /api/v1/users/{id}/` — Mijozni tahrirlash
* `DELETE /api/v1/users/{id}/` — Mijozni o'chirish (soft delete)
* `GET /api/v1/users/{id}/pinfl/` — To'liq JSHSHIR (audit qilinadi)
* `POST /api/v1/users/{id}/verify-phone/` — Telefon raqamini qo'lda tasdiqlash

### SUPER_ADMIN (41)

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
* `GET /api/v1/ceremonies/{id}/participants/` — Marosim ishtirokchilari
* `POST /api/v1/ceremonies/{id}/participants/` — Ishtirokchini telefon orqali taklif qilish
* `DELETE /api/v1/ceremonies/{id}/participants/{participant_id}/` — Ishtirokchini olib tashlash (kirish bekor qilinadi)
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
* `GET /api/v1/users/` — Mijozlar ro'yxati (USER, STUDIO)
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
* `GET /api/v1/ceremonies/{id}/participants/`
  * POST: STUDIO a'zoligi OWNER yoki MANAGER bo'lishi shart (UPLOADER — faqat ko'rish).
* `POST /api/v1/ceremonies/{id}/participants/`
  * POST: STUDIO a'zoligi OWNER yoki MANAGER bo'lishi shart (UPLOADER — faqat ko'rish).
* `DELETE /api/v1/ceremonies/{id}/participants/{participant_id}/`
  * STUDIO a'zoligi OWNER yoki MANAGER bo'lishi shart (UPLOADER — faqat ko'rish).
* `GET /api/v1/dashboard/overview/`
  * `recent_profiles` faqat `users.view` ruxsati bo'lsa to'ldiriladi, aks holda bo'sh
  * ADMIN profillari `recent_profiles` da faqat SUPER_ADMIN uchun ko'rinadi
* `DELETE /api/v1/users/{id}/`
  * Faol studiyaning mas'ul shaxsini o'chirib bo'lmaydi (409 conflict)
* `GET /api/v1/users/{id}/pinfl/`
  * Har bir ko'rish audit qilinadi (PINFL_REVEAL)
  * Throttle: pinfl_reveal

## Rejalashtirilgan (PLANNED — hali ishlamaydi)

> `apps/devcenter/planned.py`. Yuqoridagi jadval — faqat haqiqatda ishlaydigan endpointlar.
> CEREMONY_OWNER / CEREMONY_VIEWER — global rol emas, marosimga xos huquq.

| Bosqich | Metod | Yo'l | Tavsif | Kim | Shart |
|---|---|---|---|---|---|
| C | POST | `/api/v1/ceremonies/{id}/owners/invite/` | Marosim egasini telefon / JSHSHIR orqali taklif qilish | STUDIO, SUPER_ADMIN | Studiya a'zoligi OWNER/MANAGER (UPLOADER — faqat yuklash); egalar bor bo'lsa — ularning tasdig'i kerak |
| C | GET | `/api/v1/ceremonies/{id}/owners/` | Egalar va egalik takliflari holati | STUDIO, SUPER_ADMIN | — |
| C | GET | `/api/v1/me/invitations/{id}/` | Taklif tafsilotlari | USER | — |
| C | GET | `/api/v1/me/ceremonies/{id}/members/` | Egalar va ko'ruvchilar | CEREMONY_OWNER | — |
| C | POST | `/api/v1/me/ceremonies/{id}/invitations/` | VIEWER yoki OWNER taklifi yuborish | CEREMONY_OWNER | USER roli + marosimda ACCEPTED ownership; OWNER taklifi boshqa egalar tasdig'idan o'tadi |
| C | GET | `/api/v1/me/ceremonies/{id}/invitations/` | Takliflar tarixi | CEREMONY_OWNER | — |
| C | POST | `/api/v1/me/ceremonies/{id}/invitations/{invitation_id}/revoke/` | O'zi yuborgan taklifni bekor qilish | CEREMONY_OWNER | Faqat taklifni yuborgan ega |
| C | POST | `/api/v1/me/ceremonies/{id}/invitations/{invitation_id}/resend/` | Taklifni qayta yuborish (muddat yangilanadi) | CEREMONY_OWNER | Faqat taklifni yuborgan ega |
| C | POST | `/api/v1/me/ceremonies/{id}/viewers/{access_id}/revoke/` | O'zi bergan ko'rish huquqini bekor qilish | CEREMONY_OWNER | Faqat huquqni bergan ega; boshqa egalar emas |
| C | POST | `/api/v1/me/ceremonies/{id}/leave/` | Marosimdan chiqish | CEREMONY_OWNER, CEREMONY_VIEWER | — |
| C | GET | `/api/v1/me/ceremonies/{id}/owner-requests/` | Tasdiq kutayotgan yangi egalar | CEREMONY_OWNER | — |
| C | POST | `/api/v1/me/ceremonies/{id}/owner-requests/{request_id}/approve/` | Yangi egani tasdiqlash | CEREMONY_OWNER | Faqat so'rov ochilganda ACCEPTED bo'lgan va hali ega bo'lgan egalar |
| C | POST | `/api/v1/me/ceremonies/{id}/owner-requests/{request_id}/reject/` | Yangi egani rad etish | CEREMONY_OWNER | Faqat so'rov ochilganda ACCEPTED bo'lgan va hali ega bo'lgan egalar |
| D | POST | `/api/v1/ceremonies/{id}/media/uploads/` | Resumable media upload sessiyasi | STUDIO | Studiya a'zoligi OWNER/MANAGER/UPLOADER |
| D | GET | `/api/v1/ceremonies/{id}/media/` | Yuklangan fayllar va holati | STUDIO | — |
| E | GET | `/api/v1/me/ceremonies/{id}/media/` | Media galereya | CEREMONY_OWNER, CEREMONY_VIEWER | USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi) |
| E | GET | `/api/v1/me/ceremonies/{id}/media/{media_id}/thumbnail/` | Kichik rasm | CEREMONY_OWNER, CEREMONY_VIEWER | USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi); Drive fayli hech qachon public qilinmaydi |
| E | GET | `/api/v1/me/ceremonies/{id}/media/{media_id}/preview/` | Ko'rib chiqish | CEREMONY_OWNER, CEREMONY_VIEWER | USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi); Drive fayli hech qachon public qilinmaydi |
| E | GET | `/api/v1/me/ceremonies/{id}/media/{media_id}/stream/` | Video oqimi (Range) | CEREMONY_OWNER, CEREMONY_VIEWER | USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi); Drive fayli hech qachon public qilinmaydi |
| E | GET | `/api/v1/me/ceremonies/{id}/media/{media_id}/download/` | Asl faylni yuklab olish | CEREMONY_OWNER, CEREMONY_VIEWER | USER roli + ACCEPTED ownership yoki viewer access (har so'rovda qayta tekshiriladi); Drive fayli hech qachon public qilinmaydi |
| F | GET | `/api/v1/admin/ceremonies/` | Barcha marosimlar monitoringi | SUPER_ADMIN | — |
| F | GET | `/api/v1/admin/ceremonies/{id}/` | Marosim: egalar, takliflar, ko'ruvchilar, media, tarix | SUPER_ADMIN | Maxfiy maydonlar faqat audit qilinadigan alohida amal orqali |
