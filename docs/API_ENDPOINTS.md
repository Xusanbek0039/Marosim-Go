# API endpointlar

> Avtomatik yaratilgan: `python manage.py export_api_endpoints` (OpenAPI'dan). Qo'lda tahrirlamang.
> Batafsil: Swagger `/api/v1/docs/`, panel → API Monitoring → Endpointlar.

| Metod | Yo'l | Tavsif | Kirish |
|---|---|---|---|
| GET | `/api/v1/admin/storage/google/callback/` | Google OAuth callback (brauzer redirect) | Ochiq (public) |
| GET | `/api/v1/admin/storage/google/connect/` | Google Drive'ni ulashni boshlash | Faqat SUPER_ADMIN |
| POST | `/api/v1/admin/storage/google/disconnect/` | Google Drive'ni uzish | Faqat SUPER_ADMIN |
| GET | `/api/v1/admin/storage/google/status/` | Google Drive ulanish holati | Faqat SUPER_ADMIN |
| POST | `/api/v1/admin/storage/google/test/` | Ulanishni tekshirish | Faqat SUPER_ADMIN |
| GET | `/api/v1/admins/` |  | Faqat SUPER_ADMIN |
| POST | `/api/v1/admins/` |  | Faqat SUPER_ADMIN |
| GET | `/api/v1/admins/permissions/` | Adminlarga beriladigan ruxsatlar ro'yxati | Faqat SUPER_ADMIN |
| GET | `/api/v1/admins/{id}/` |  | Faqat SUPER_ADMIN |
| PATCH | `/api/v1/admins/{id}/` |  | Faqat SUPER_ADMIN |
| DELETE | `/api/v1/admins/{id}/` |  | Faqat SUPER_ADMIN |
| GET | `/api/v1/admins/{id}/pinfl/` | Adminning to'liq JSHSHIRi (audit qilinadi) | Faqat SUPER_ADMIN |
| GET | `/api/v1/auth/csrf/` | CSRF cookie olish (web panel) | Ochiq (public) |
| POST | `/api/v1/auth/login/` | Tizimga kirish (telefon + parol) | Ochiq (public) |
| POST | `/api/v1/auth/logout/` | Tizimdan chiqish | Ochiq (public) |
| GET | `/api/v1/auth/me/` | Mening profilim | Har qanday tizimga kirgan foydalanuvchi |
| PATCH | `/api/v1/auth/me/` | Profilni tahrirlash | Har qanday tizimga kirgan foydalanuvchi |
| POST | `/api/v1/auth/refresh/` | Tokenni yangilash (rotation) | Ochiq (public) |
| POST | `/api/v1/auth/register/` | Ro'yxatdan o'tish (telefon + parol) | Ochiq (public) |
| GET | `/api/v1/dashboard/overview/` |  | SUPER_ADMIN yoki `dashboard.view` ruxsatli ADMIN |
| GET | `/api/v1/health/live/` | Liveness — jarayon ishlayaptimi | Ochiq (public) |
| GET | `/api/v1/health/ready/` | Readiness — bog'liqliklar (database, cache) tayyormi | Ochiq (public) |
| GET | `/api/v1/monitoring/endpoints/` | API endpointlar katalogi (OpenAPI'dan avtomatik) | Faqat SUPER_ADMIN |
| GET | `/api/v1/monitoring/logs/` | So'rovlar jurnali | Faqat SUPER_ADMIN |
| GET | `/api/v1/monitoring/overview/` | API statistikasi (real so'rovlar asosida) | Faqat SUPER_ADMIN |
| GET | `/api/v1/studios/` |  | SUPER_ADMIN yoki `studios.view` ruxsatli ADMIN |
| POST | `/api/v1/studios/` |  | SUPER_ADMIN yoki `studios.create` ruxsatli ADMIN |
| GET | `/api/v1/studios/{id}/` |  | SUPER_ADMIN yoki `studios.view` ruxsatli ADMIN |
| PATCH | `/api/v1/studios/{id}/` |  | SUPER_ADMIN yoki `studios.update` ruxsatli ADMIN |
| DELETE | `/api/v1/studios/{id}/` |  | SUPER_ADMIN yoki `studios.delete` ruxsatli ADMIN |
| GET | `/api/v1/users/` |  | SUPER_ADMIN yoki `users.view` ruxsatli ADMIN |
| POST | `/api/v1/users/` |  | SUPER_ADMIN yoki `users.create` ruxsatli ADMIN |
| GET | `/api/v1/users/{id}/` |  | SUPER_ADMIN yoki `users.view` ruxsatli ADMIN |
| PATCH | `/api/v1/users/{id}/` |  | SUPER_ADMIN yoki `users.update` ruxsatli ADMIN |
| DELETE | `/api/v1/users/{id}/` |  | SUPER_ADMIN yoki `users.delete` ruxsatli ADMIN |
| GET | `/api/v1/users/{id}/pinfl/` | To'liq JSHSHIR (audit qilinadi) | SUPER_ADMIN yoki `users.view_pinfl` ruxsatli ADMIN |
