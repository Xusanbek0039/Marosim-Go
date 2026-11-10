# API endpointlar

> Avtomatik yaratilgan: `python manage.py export_api_endpoints` (OpenAPI'dan). Qo'lda tahrirlamang.
> Rollar DRF permission class'laridan olinadi (`apps/accounts/access.py`) va
> `tests/test_api_access_contract.py` da har bir rol bilan haqiqiy so'rov orqali tekshiriladi.
> Batafsil: Swagger `/api/v1/docs/`, panel → API Monitoring → Endpointlar.

| Metod | Yo'l | Tavsif | Rollar | Ruxsat kodi (ADMIN) | Auth | Ma'lumot doirasi | Holat |
|---|---|---|---|---|---|---|---|
| GET | `/api/v1/admin/media-deletion-requests/` | Media o'chirish so'rovlari | ADMIN, SUPER_ADMIN | `requests.view` | JWT | Barcha studiyalarning so'rovlari (faqat ruxsati borlar). | OK |
| GET | `/api/v1/admin/media-deletion-requests/summary/` | Kutilayotgan so'rovlar soni (menyu belgisi uchun) | ADMIN, SUPER_ADMIN | `requests.view` | JWT | Barcha studiyalarning so'rovlari (faqat ruxsati borlar). | OK |
| GET | `/api/v1/admin/media-deletion-requests/{id}/` | O'chirish so'rovi tafsiloti | ADMIN, SUPER_ADMIN | `requests.view` | JWT | Barcha studiyalarning so'rovlari (faqat ruxsati borlar). | OK |
| POST | `/api/v1/admin/media-deletion-requests/{id}/approve/` | Tasdiqlash: fayl Drive savatiga o'tadi va ilovadan o'chadi | ADMIN, SUPER_ADMIN | `requests.media_delete` | JWT | Barcha studiyalarning so'rovlari (faqat ruxsati borlar). | OK |
| POST | `/api/v1/admin/media-deletion-requests/{id}/reject/` | Rad etish (fayl qoladi) | ADMIN, SUPER_ADMIN | `requests.media_delete` | JWT | Barcha studiyalarning so'rovlari (faqat ruxsati borlar). | OK |
| GET | `/api/v1/admin/platform-policy/` | Rollar imkoniyatlarini ko'rish | ADMIN, SUPER_ADMIN | `platform.view` | JWT | — | OK |
| PATCH | `/api/v1/admin/platform-policy/` | Rollar imkoniyatlarini yoqish / o'chirish | ADMIN, SUPER_ADMIN | `platform.manage` | JWT | — | OK |
| GET | `/api/v1/admin/reviews/` | Barcha sharhlar (moderatsiya) | ADMIN, SUPER_ADMIN | `reviews.view` | JWT | Barcha to'yxona va studiya sharhlari (yashirilganlari ham). | OK |
| GET | `/api/v1/admin/reviews/{id}/` | Sharh tafsiloti | ADMIN, SUPER_ADMIN | `reviews.view` | JWT | Barcha to'yxona va studiya sharhlari (yashirilganlari ham). | OK |
| PATCH | `/api/v1/admin/reviews/{id}/` | Sharhni yashirish / ko'rsatish | ADMIN, SUPER_ADMIN | `reviews.moderate` | JWT | Barcha to'yxona va studiya sharhlari (yashirilganlari ham). | OK |
| DELETE | `/api/v1/admin/reviews/{id}/` | Sharhni o'chirish | ADMIN, SUPER_ADMIN | `reviews.moderate` | JWT | Barcha to'yxona va studiya sharhlari (yashirilganlari ham). | OK |
| GET | `/api/v1/admin/storage/google/callback/` | Google OAuth callback (brauzer redirect) | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/admin/storage/google/connect/` | Google Drive'ni ulashni boshlash | SUPER_ADMIN | — | JWT | — | OK |
| POST | `/api/v1/admin/storage/google/disconnect/` | Google Drive'ni uzish | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/admin/storage/google/status/` | Google Drive ulanish holati | SUPER_ADMIN | — | JWT | — | OK |
| POST | `/api/v1/admin/storage/google/test/` | Ulanishni tekshirish | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/admin/subscription-plans/` | Tariflar (barchasi) | ADMIN, SUPER_ADMIN | `subscriptions.view` | JWT | — | OK |
| POST | `/api/v1/admin/subscription-plans/` | Tarif qo'shish | ADMIN, SUPER_ADMIN | `subscriptions.plans` | JWT | — | OK |
| PATCH | `/api/v1/admin/subscription-plans/{id}/` | Tarif narxi / muddati / limitini o'zgartirish | ADMIN, SUPER_ADMIN | `subscriptions.plans` | JWT | — | OK |
| GET | `/api/v1/admin/subscription-settings/` | To'lov ma'lumotlari (mijozga ko'rsatiladi) | ADMIN, SUPER_ADMIN | `subscriptions.view` | JWT | — | OK |
| PATCH | `/api/v1/admin/subscription-settings/` | To'lov ma'lumotlarini o'zgartirish | ADMIN, SUPER_ADMIN | `subscriptions.plans` | JWT | — | OK |
| GET | `/api/v1/admin/subscriptions/` | Obunalar va to'lovlar | ADMIN, SUPER_ADMIN | `subscriptions.view` | JWT | Barcha foydalanuvchilarning obunalari (faqat ruxsati borlar). | OK |
| POST | `/api/v1/admin/subscriptions/` | Foydalanuvchiga obuna berish (to'lov qayd etiladi) | ADMIN, SUPER_ADMIN | `subscriptions.create` | JWT | Barcha foydalanuvchilarning obunalari (faqat ruxsati borlar). | OK |
| GET | `/api/v1/admin/subscriptions/summary/` | Obunalar statistikasi (so'rovlar, faollar, tushum) | ADMIN, SUPER_ADMIN | `subscriptions.view` | JWT | Barcha foydalanuvchilarning obunalari (faqat ruxsati borlar). | OK |
| GET | `/api/v1/admin/subscriptions/{id}/` | Obuna tafsiloti | ADMIN, SUPER_ADMIN | `subscriptions.view` | JWT | Barcha foydalanuvchilarning obunalari (faqat ruxsati borlar). | OK |
| POST | `/api/v1/admin/subscriptions/{id}/approve/` | To'lovni qayd etib tasdiqlash | ADMIN, SUPER_ADMIN | `subscriptions.update` | JWT | Barcha foydalanuvchilarning obunalari (faqat ruxsati borlar). | OK |
| POST | `/api/v1/admin/subscriptions/{id}/cancel/` | Obunani bekor qilish | ADMIN, SUPER_ADMIN | `subscriptions.update` | JWT | Barcha foydalanuvchilarning obunalari (faqat ruxsati borlar). | OK |
| POST | `/api/v1/admin/subscriptions/{id}/reject/` | So'rovni rad etish | ADMIN, SUPER_ADMIN | `subscriptions.update` | JWT | Barcha foydalanuvchilarning obunalari (faqat ruxsati borlar). | OK |
| GET | `/api/v1/admin/support/applications/` | Hamkorlik arizalari (studiya / to'yxona) | ADMIN, SUPER_ADMIN | `support.view` | JWT | Barcha arizalar (support.view ruxsati bor adminlar va SUPER_ADMIN). | OK |
| GET | `/api/v1/admin/support/applications/summary/` | Yangi arizalar soni | ADMIN, SUPER_ADMIN | `support.view` | JWT | Barcha arizalar (support.view ruxsati bor adminlar va SUPER_ADMIN). | OK |
| GET | `/api/v1/admin/support/applications/{id}/` | Ariza tafsiloti | ADMIN, SUPER_ADMIN | `support.view` | JWT | Barcha arizalar (support.view ruxsati bor adminlar va SUPER_ADMIN). | OK |
| PATCH | `/api/v1/admin/support/applications/{id}/` | Ariza holati va izohi | ADMIN, SUPER_ADMIN | `support.view` | JWT | Barcha arizalar (support.view ruxsati bor adminlar va SUPER_ADMIN). | OK |
| GET | `/api/v1/admin/support/tickets/` | Kelgan yordam xatlari | ADMIN, SUPER_ADMIN | `support.view` | JWT | SUPER_ADMIN — barchasi; ADMIN (support.view) — foydalanuvchi / studiya / to'yxona xatlari; support.monitor bilan — adminlarning Super Admin'ga xatlari ham (faqat o'qish). | OK |
| GET | `/api/v1/admin/support/tickets/summary/` | Javob kutayotgan xatlar soni (javob bera oladiganlari) | ADMIN, SUPER_ADMIN | `support.view` | JWT | SUPER_ADMIN — barchasi; ADMIN (support.view) — foydalanuvchi / studiya / to'yxona xatlari; support.monitor bilan — adminlarning Super Admin'ga xatlari ham (faqat o'qish). | OK |
| GET | `/api/v1/admin/support/tickets/{id}/` | Yordam xati (yozishmalar, kim javob bergani) | ADMIN, SUPER_ADMIN | `support.view` | JWT | SUPER_ADMIN — barchasi; ADMIN (support.view) — foydalanuvchi / studiya / to'yxona xatlari; support.monitor bilan — adminlarning Super Admin'ga xatlari ham (faqat o'qish). | OK |
| POST | `/api/v1/admin/support/tickets/{id}/close/` | Xatni yopish | ADMIN, SUPER_ADMIN | `support.view` | JWT | SUPER_ADMIN — barchasi; ADMIN (support.view) — foydalanuvchi / studiya / to'yxona xatlari; support.monitor bilan — adminlarning Super Admin'ga xatlari ham (faqat o'qish). | OK |
| POST | `/api/v1/admin/support/tickets/{id}/messages/` | Javob yozish | ADMIN, SUPER_ADMIN | `support.view` | JWT | SUPER_ADMIN — barchasi; ADMIN (support.view) — foydalanuvchi / studiya / to'yxona xatlari; support.monitor bilan — adminlarning Super Admin'ga xatlari ham (faqat o'qish). | OK |
| GET | `/api/v1/admin/venues/` | To'yxonalar ro'yxati (panel) | ADMIN, SUPER_ADMIN | `venues.view` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| POST | `/api/v1/admin/venues/` | To'yxona qo'shish (egasi bilan) | ADMIN, SUPER_ADMIN | `venues.create` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| GET | `/api/v1/admin/venues/{id}/` | To'yxona ma'lumotlari (panel) | ADMIN, SUPER_ADMIN | `venues.view` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| PATCH | `/api/v1/admin/venues/{id}/` | To'yxonani tahrirlash / bloklash / holat | ADMIN, SUPER_ADMIN | `venues.update` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| DELETE | `/api/v1/admin/venues/{id}/` | To'yxonani o'chirish (soft delete) | ADMIN, SUPER_ADMIN | `venues.delete` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| GET | `/api/v1/admin/venues/{id}/bookings/` | Bronlar va so'rovlar (panel) | ADMIN, SUPER_ADMIN | `venues.view` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| POST | `/api/v1/admin/venues/{id}/bookings/` | Jadvalga yozuv qo'shish (panel) | ADMIN, SUPER_ADMIN | `venues.schedule` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| PATCH | `/api/v1/admin/venues/{id}/bookings/{booking_id}/` | Yozuv tafsilotlarini tahrirlash (panel) | ADMIN, SUPER_ADMIN | `venues.schedule` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| POST | `/api/v1/admin/venues/{id}/bookings/{booking_id}/cancel/` | Yozuvni bekor qilish (panel) | ADMIN, SUPER_ADMIN | `venues.schedule` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| POST | `/api/v1/admin/venues/{id}/bookings/{booking_id}/confirm/` | So'rovni tasdiqlash (panel) | ADMIN, SUPER_ADMIN | `venues.schedule` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| POST | `/api/v1/admin/venues/{id}/bookings/{booking_id}/reject/` | So'rovni rad etish (panel) | ADMIN, SUPER_ADMIN | `venues.schedule` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| GET | `/api/v1/admin/venues/{id}/calendar/` | To'yxona jadvali: zallar, smenalar va yozuvlar (panel) | ADMIN, SUPER_ADMIN | `venues.view` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| POST | `/api/v1/admin/venues/{id}/halls/` | Zal qo'shish (panel) | ADMIN, SUPER_ADMIN | `venues.update` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| PATCH | `/api/v1/admin/venues/{id}/halls/{hall_id}/` | Zalni tahrirlash (panel) | ADMIN, SUPER_ADMIN | `venues.update` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| GET | `/api/v1/admin/venues/{id}/halls/{hall_id}/sessions/` | Zal smenalari (panel) | ADMIN, SUPER_ADMIN | `venues.view` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| POST | `/api/v1/admin/venues/{id}/halls/{hall_id}/sessions/` | Zalga smena qo'shish (panel) | ADMIN, SUPER_ADMIN | `venues.schedule` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| PATCH | `/api/v1/admin/venues/{id}/halls/{hall_id}/sessions/{session_id}/` | Smenani tahrirlash / o'chirish-yoqish (panel) | ADMIN, SUPER_ADMIN | `venues.schedule` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| POST | `/api/v1/admin/venues/{id}/images/` | Galereyaga rasm qo'shish (panel) | ADMIN, SUPER_ADMIN | `venues.update` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
| DELETE | `/api/v1/admin/venues/{id}/images/{image_id}/` | Galereyadan rasmni o'chirish (panel) | ADMIN, SUPER_ADMIN | `venues.update` | JWT | Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi. | OK |
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
| GET | `/api/v1/ceremonies/{ceremony_id}/media/` | Marosimning yuklangan fayllari va holati | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyaning marosimi (boshqasi 404); SUPER_ADMIN: barchasi. | OK |
| POST | `/api/v1/ceremonies/{ceremony_id}/media/uploads/` | Media yuklashni boshlash (Google Drive resumable sessiya) | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyaning marosimi (boshqasi 404); SUPER_ADMIN: barchasi. | OK |
| GET | `/api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/` | Yuklash holati (Google'dan jonli progress) | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyaning marosimi (boshqasi 404); SUPER_ADMIN: barchasi. | OK |
| DELETE | `/api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/` | Tugallanmagan yuklashni ro'yxatdan o'chirish | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyaning marosimi (boshqasi 404); SUPER_ADMIN: barchasi. | OK |
| POST | `/api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/cancel/` | Yuklashni bekor qilish | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyaning marosimi (boshqasi 404); SUPER_ADMIN: barchasi. | OK |
| POST | `/api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/complete/` | Yuklashni yakunlash va tekshirish | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyaning marosimi (boshqasi 404); SUPER_ADMIN: barchasi. | OK |
| POST | `/api/v1/ceremonies/{ceremony_id}/media/{media_id}/delete-request/` | Tayyor faylni o'chirishni so'rash (admin tasdiqlaydi) | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyaning marosimi (boshqasi 404); SUPER_ADMIN: barchasi. | OK |
| POST | `/api/v1/ceremonies/{ceremony_id}/media/{media_id}/delete-request/cancel/` | O'chirish so'rovini qaytarib olish | STUDIO, SUPER_ADMIN | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyaning marosimi (boshqasi 404); SUPER_ADMIN: barchasi. | OK |
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
| GET | `/api/v1/me/ceremonies/{ceremony_id}/media/` | Marosim rasm va videolari | USER | — | JWT | Faqat so'rovchi ACCEPTED egasi yoki muddati tugamagan ko'ruvchisi bo'lgan marosimning READY fayllari; boshqasi 404. Huquq har so'rovda qayta tekshiriladi. | OK |
| GET | `/api/v1/me/ceremonies/{ceremony_id}/media/{media_id}/download/` | Faylni yuklab olish (faqat obunasi faol ega, logosiz original) | USER | — | JWT | Faqat so'rovchi ACCEPTED egasi yoki muddati tugamagan ko'ruvchisi bo'lgan marosimning READY fayllari; boshqasi 404. Huquq har so'rovda qayta tekshiriladi. | OK |
| GET | `/api/v1/me/ceremonies/{ceremony_id}/media/{media_id}/stream/` | Faylni ko'rish (oqim, Range) | USER | — | JWT | Faqat so'rovchi ACCEPTED egasi yoki muddati tugamagan ko'ruvchisi bo'lgan marosimning READY fayllari; boshqasi 404. Huquq har so'rovda qayta tekshiriladi. | OK |
| GET | `/api/v1/me/ceremonies/{ceremony_id}/media/{media_id}/thumbnail/` | Kichik rasm (preview) | USER | — | JWT | Faqat so'rovchi ACCEPTED egasi yoki muddati tugamagan ko'ruvchisi bo'lgan marosimning READY fayllari; boshqasi 404. Huquq har so'rovda qayta tekshiriladi. | OK |
| GET | `/api/v1/me/ceremonies/{id}/` | Menga biriktirilgan marosim | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
| PATCH | `/api/v1/me/ceremonies/{id}/folder/` | Papka nomini o'zgartirish (faqat o'zim uchun) | USER | — | JWT | Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi. | OK |
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
| GET | `/api/v1/me/studio-chats/` | Studiyalar bilan suhbatlarim | USER | — | JWT | Faqat so'rovchining o'z suhbatlari. | OK |
| GET | `/api/v1/me/studio-chats/{studio_id}/` | Studiya bilan suhbat (xabarlar) | USER | — | JWT | Faqat so'rovchining o'z suhbatlari. | OK |
| POST | `/api/v1/me/studio-chats/{studio_id}/` | Studiyaga xabar yozish | USER | — | JWT | Faqat so'rovchining o'z suhbatlari. | OK |
| GET | `/api/v1/me/subscriptions/` | Mening obuna so'rovlarim va obunalarim | USER, STUDIO, VENUE_OWNER | — | JWT | Faqat so'rovchining o'z obunalari; boshqasiniki 404. | OK |
| POST | `/api/v1/me/subscriptions/` | Obuna so'rovi yuborish (to'lov admin tomonidan tasdiqlanadi) | USER, STUDIO, VENUE_OWNER | — | JWT | — | OK |
| GET | `/api/v1/me/subscriptions/status/` | Obuna holati, limitlar, tariflar va to'lov ma'lumotlari | USER, STUDIO, VENUE_OWNER | — | JWT | — | OK |
| GET | `/api/v1/me/subscriptions/targets/` | Galichka sotib olish mumkin bo'lgan o'z bizneslarim | USER, STUDIO, VENUE_OWNER | — | JWT | Faqat so'rovchining o'z obunalari; boshqasiniki 404. | OK |
| POST | `/api/v1/me/subscriptions/{id}/cancel/` | Kutilayotgan so'rovni bekor qilish | USER, STUDIO, VENUE_OWNER | — | JWT | Faqat so'rovchining o'z obunalari; boshqasiniki 404. | OK |
| GET | `/api/v1/me/venue-bookings/` | Mening to'yxona bronlarim | USER | — | JWT | Faqat so'rovchining o'z bronlari; boshqasiniki 404. | OK |
| POST | `/api/v1/me/venue-bookings/` | To'yxona smenasiga bron so'rovi yuborish | USER | — | JWT | — | OK |
| GET | `/api/v1/me/venue-bookings/{id}/` | Bron tafsiloti | USER | — | JWT | Faqat so'rovchining o'z bronlari; boshqasiniki 404. | OK |
| POST | `/api/v1/me/venue-bookings/{id}/cancel/` | Bron / so'rovni bekor qilish | USER | — | JWT | Faqat so'rovchining o'z bronlari; boshqasiniki 404. | OK |
| GET | `/api/v1/monitoring/endpoints/` | API endpointlar katalogi (OpenAPI'dan avtomatik) | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/monitoring/logs/` | So'rovlar jurnali | SUPER_ADMIN | — | JWT | — | OK |
| GET | `/api/v1/monitoring/overview/` | API statistikasi (real so'rovlar asosida) | SUPER_ADMIN | — | JWT | — | OK |
| POST | `/api/v1/public/partner-applications/` | Hamkorlik arizasi (studiya / to'yxona) — landing sahifadan | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/public/partner-applications/challenge/` | Bot tekshiruvi uchun bir martalik topshiriq (proof-of-work) | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/public/studios/` | Studiyalar (ommaviy katalog, reyting bo'yicha) | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/public/studios/{id}/` | Studiya (ommaviy profil, portfolio va reels) | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/public/studios/{id}/schedule/` | Studiya grafigi: band, dam olish va bo'sh kunlar | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/public/studios/{studio_id}/portfolio/{item_id}/comments/` | Portfolio ishining izohlari | PUBLIC | — | NONE | — | OK |
| POST | `/api/v1/public/studios/{studio_id}/portfolio/{item_id}/comments/` | Izoh yozish | USER | — | JWT | — | OK |
| DELETE | `/api/v1/public/studios/{studio_id}/portfolio/{item_id}/comments/{comment_id}/` | O'z izohimni o'chirish | USER | — | JWT | Faqat so'rovchining o'z izohi; boshqasi 404. | OK |
| GET | `/api/v1/public/studios/{studio_id}/portfolio/{item_id}/file/{part}/` | Portfolio fayli (rasm, reels videosi yoki muqovasi) | PUBLIC | — | NONE | — | OK |
| PUT | `/api/v1/public/studios/{studio_id}/portfolio/{item_id}/reaction/` | Portfolio ishiga like / dislike | USER | — | JWT | Faqat so'rovchining o'z bahosi. | OK |
| DELETE | `/api/v1/public/studios/{studio_id}/portfolio/{item_id}/reaction/` | Like / dislike'ni olib tashlash | USER | — | JWT | Faqat so'rovchining o'z bahosi. | OK |
| POST | `/api/v1/public/studios/{target_id}/like/` | Like bosish | USER | — | JWT | Faqat so'rovchining o'z sharhi / like'i; boshqalarniki o'zgarmaydi. | OK |
| DELETE | `/api/v1/public/studios/{target_id}/like/` | Like'ni olib tashlash | USER | — | JWT | Faqat so'rovchining o'z sharhi / like'i; boshqalarniki o'zgarmaydi. | OK |
| GET | `/api/v1/public/studios/{target_id}/reviews/` | Sharhlar, reyting va like soni | PUBLIC | — | NONE | — | OK |
| PUT | `/api/v1/public/studios/{target_id}/reviews/mine/` | Baho va izoh qoldirish / yangilash | USER | — | JWT | Faqat so'rovchining o'z sharhi / like'i; boshqalarniki o'zgarmaydi. | OK |
| DELETE | `/api/v1/public/studios/{target_id}/reviews/mine/` | O'z sharhimni o'chirish | USER | — | JWT | Faqat so'rovchining o'z sharhi / like'i; boshqalarniki o'zgarmaydi. | OK |
| GET | `/api/v1/studios/` | Studiyalar ro'yxati | ADMIN, SUPER_ADMIN | `studios.view` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| POST | `/api/v1/studios/` | Studiya qo'shish | ADMIN, SUPER_ADMIN | `studios.create` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| GET | `/api/v1/studios/me/` | Mening studiyalarim | STUDIO | — | JWT | Faqat so'rovchining faol a'zoliklari va ularning studiyalari. | OK |
| GET | `/api/v1/studios/me/ceremonies/` | Mening studiyamning marosimlari | STUDIO | — | JWT | STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi. | OK |
| GET | `/api/v1/studios/me/{studio_id}/chats/` | Mijozlar bilan suhbatlar | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| GET | `/api/v1/studios/me/{studio_id}/chats/{conversation_id}/` | Mijoz bilan suhbat (xabarlar) | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| POST | `/api/v1/studios/me/{studio_id}/chats/{conversation_id}/` | Mijozga javob yozish | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| GET | `/api/v1/studios/me/{studio_id}/images/` | Studiya portfoliosi (rasmlar va reels, like / izoh soni bilan) | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| POST | `/api/v1/studios/me/{studio_id}/images/` | Portfolioga rasm qo'shish | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| PATCH | `/api/v1/studios/me/{studio_id}/images/{image_id}/` | Portfolio ishining izohini (caption) o'zgartirish | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| DELETE | `/api/v1/studios/me/{studio_id}/images/{image_id}/` | Portfoliodan rasm / videoni o'chirish | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| GET | `/api/v1/studios/me/{studio_id}/images/{image_id}/comments/` | Portfolio ishiga yozilgan izohlar | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| DELETE | `/api/v1/studios/me/{studio_id}/images/{image_id}/comments/{comment_id}/` | Izohni o'chirish (studiya moderatsiyasi) | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| POST | `/api/v1/studios/me/{studio_id}/reels/` | Portfolioga reels (vertikal video) qo'shish | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| GET | `/api/v1/studios/me/{studio_id}/schedule/` | Studiya grafigi (marosimlar, band va dam olish kunlari) | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| PATCH | `/api/v1/studios/me/{studio_id}/schedule/` | Haftalik dam olish kunlari | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| PUT | `/api/v1/studios/me/{studio_id}/schedule/days/{day}/` | Kunni band / dam olish deb belgilash (status=null — tozalash) | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| GET | `/api/v1/studios/me/{studio_id}/storage/` | Portfolio joyi (ishlatilgan / ajratilgan) | STUDIO | — | JWT | Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404. | OK |
| GET | `/api/v1/studios/{id}/` | Studiya ma'lumotlari | ADMIN, SUPER_ADMIN | `studios.view` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| PATCH | `/api/v1/studios/{id}/` | Studiyani tahrirlash | ADMIN, SUPER_ADMIN | `studios.update` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| DELETE | `/api/v1/studios/{id}/` | Studiyani o'chirish (soft delete) | ADMIN, SUPER_ADMIN | `studios.delete` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| GET | `/api/v1/studios/{id}/calendar/` | Studiya jadvali: oraliqdagi marosimlar (panel) | ADMIN, SUPER_ADMIN | `studios.view` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| POST | `/api/v1/studios/{id}/images/` | Portfolioga rasm qo'shish (panel) | ADMIN, SUPER_ADMIN | `studios.update` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| DELETE | `/api/v1/studios/{id}/images/{image_id}/` | Portfoliodan rasmni o'chirish (panel) | ADMIN, SUPER_ADMIN | `studios.update` | JWT | Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi. | OK |
| GET | `/api/v1/subscriptions/plans/` | Obuna tariflari | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/support/tickets/` | Mening yordam xatlarim | USER, STUDIO, VENUE_OWNER, ADMIN | — | JWT | Faqat o'zi yozgan xatlar (boshqalarniki 404). | OK |
| POST | `/api/v1/support/tickets/` | Yordam xati yuborish | USER, STUDIO, VENUE_OWNER, ADMIN | — | JWT | Faqat o'zi yozgan xatlar (boshqalarniki 404). | OK |
| GET | `/api/v1/support/tickets/summary/` | Xatlarim soni (javob kelganlar — menyu belgisi uchun) | USER, STUDIO, VENUE_OWNER, ADMIN | — | JWT | Faqat o'zi yozgan xatlar (boshqalarniki 404). | OK |
| GET | `/api/v1/support/tickets/{id}/` | Yordam xati (yozishmalar bilan) | USER, STUDIO, VENUE_OWNER, ADMIN | — | JWT | Faqat o'zi yozgan xatlar (boshqalarniki 404). | OK |
| POST | `/api/v1/support/tickets/{id}/close/` | Xatni yopish (muammo hal bo'ldi) | USER, STUDIO, VENUE_OWNER, ADMIN | — | JWT | Faqat o'zi yozgan xatlar (boshqalarniki 404). | OK |
| POST | `/api/v1/support/tickets/{id}/messages/` | Xatga qo'shimcha yozish (yopilgan xat qayta ochiladi) | USER, STUDIO, VENUE_OWNER, ADMIN | — | JWT | Faqat o'zi yozgan xatlar (boshqalarniki 404). | OK |
| GET | `/api/v1/users/` | Mijozlar ro'yxati (USER, STUDIO, VENUE_OWNER) | ADMIN, SUPER_ADMIN | `users.view` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| POST | `/api/v1/users/` | Mijoz qo'shish | ADMIN, SUPER_ADMIN | `users.create` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| GET | `/api/v1/users/{id}/` | Mijoz ma'lumotlari | ADMIN, SUPER_ADMIN | `users.view` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| PATCH | `/api/v1/users/{id}/` | Mijozni tahrirlash | ADMIN, SUPER_ADMIN | `users.update` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| DELETE | `/api/v1/users/{id}/` | Mijozni o'chirish (soft delete) | ADMIN, SUPER_ADMIN | `users.delete` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| GET | `/api/v1/users/{id}/features/` | Hisob imkoniyatlari (shu profil uchun) | ADMIN, SUPER_ADMIN | `platform.view` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| PATCH | `/api/v1/users/{id}/features/` | Hisob imkoniyatlarini yoqish / o'chirish | ADMIN, SUPER_ADMIN | `platform.manage` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| GET | `/api/v1/users/{id}/folders/` | Foydalanuvchining marosim papkalari | ADMIN, SUPER_ADMIN | `users.view` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| PATCH | `/api/v1/users/{id}/folders/{ceremony_id}/` | Foydalanuvchi papkasi nomini o'zgartirish | ADMIN, SUPER_ADMIN | `users.update` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| GET | `/api/v1/users/{id}/pinfl/` | To'liq JSHSHIR (audit qilinadi) | ADMIN, SUPER_ADMIN | `users.view_pinfl` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| POST | `/api/v1/users/{id}/verify-phone/` | Telefon raqamini qo'lda tasdiqlash | ADMIN, SUPER_ADMIN | `users.update` | JWT | Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404). | OK |
| GET | `/api/v1/venue-owner/venues/` | Mening to'yxonalarim | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| POST | `/api/v1/venue-owner/venues/` | To'yxona yaratish (PRIVATE holatda) | VENUE_OWNER | — | JWT | — | OK |
| GET | `/api/v1/venue-owner/venues/{id}/` | To'yxona ma'lumotlari (egasi uchun) | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| PATCH | `/api/v1/venue-owner/venues/{id}/` | To'yxonani tahrirlash | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| GET | `/api/v1/venue-owner/venues/{id}/bookings/` | Bronlar va so'rovlar | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| POST | `/api/v1/venue-owner/venues/{id}/bookings/` | Jadvalga yozuv qo'shish (o'z mijozi yoki yopiq smena) | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| PATCH | `/api/v1/venue-owner/venues/{id}/bookings/{booking_id}/` | Yozuv tafsilotlarini tahrirlash | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| POST | `/api/v1/venue-owner/venues/{id}/bookings/{booking_id}/cancel/` | Yozuvni bekor qilish (smena bo'shaydi) | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| POST | `/api/v1/venue-owner/venues/{id}/bookings/{booking_id}/confirm/` | So'rovni tasdiqlash (smena band bo'ladi) | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| POST | `/api/v1/venue-owner/venues/{id}/bookings/{booking_id}/reject/` | So'rovni rad etish | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| GET | `/api/v1/venue-owner/venues/{id}/calendar/` | Jadval: zallar, smenalar va shu oraliqdagi barcha yozuvlar | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| GET | `/api/v1/venue-owner/venues/{id}/halls/` | To'yxona zallari | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| POST | `/api/v1/venue-owner/venues/{id}/halls/` | Zal qo'shish | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| PATCH | `/api/v1/venue-owner/venues/{id}/halls/{hall_id}/` | Zalni tahrirlash | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| GET | `/api/v1/venue-owner/venues/{id}/halls/{hall_id}/sessions/` | Zal smenalari | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| POST | `/api/v1/venue-owner/venues/{id}/halls/{hall_id}/sessions/` | Zalga smena qo'shish | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| PATCH | `/api/v1/venue-owner/venues/{id}/halls/{hall_id}/sessions/{session_id}/` | Smenani tahrirlash / o'chirish-yoqish | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| GET | `/api/v1/venue-owner/venues/{id}/images/` | Galereya rasmlari | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| POST | `/api/v1/venue-owner/venues/{id}/images/` | Galereyaga rasm qo'shish | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| DELETE | `/api/v1/venue-owner/venues/{id}/images/{image_id}/` | Galereyadan rasmni o'chirish | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| GET | `/api/v1/venue-owner/venues/{id}/members/` | To'yxona a'zolari | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| POST | `/api/v1/venue-owner/venues/{id}/members/` | A'zo qo'shish (telefon raqam bo'yicha) | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| PATCH | `/api/v1/venue-owner/venues/{id}/members/{membership_id}/` | A'zoning rolini / faolligini o'zgartirish | VENUE_OWNER | — | JWT | Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404. | OK |
| GET | `/api/v1/venues/` | To'yxonalar katalogi (reyting va like bo'yicha) | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/venues/search/` | Sana bo'yicha bo'sh to'yxonalarni qidirish | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/venues/{id}/` | To'yxona (ommaviy ma'lumot, zallar va smenalar) | PUBLIC | — | NONE | — | OK |
| GET | `/api/v1/venues/{id}/availability/` | To'yxona bo'sh smenalari (kalendar) | PUBLIC | — | NONE | — | OK |
| POST | `/api/v1/venues/{target_id}/like/` | Like bosish | USER | — | JWT | Faqat so'rovchining o'z sharhi / like'i; boshqalarniki o'zgarmaydi. | OK |
| DELETE | `/api/v1/venues/{target_id}/like/` | Like'ni olib tashlash | USER | — | JWT | Faqat so'rovchining o'z sharhi / like'i; boshqalarniki o'zgarmaydi. | OK |
| GET | `/api/v1/venues/{target_id}/reviews/` | Sharhlar, reyting va like soni | PUBLIC | — | NONE | — | OK |
| PUT | `/api/v1/venues/{target_id}/reviews/mine/` | Baho va izoh qoldirish / yangilash | USER | — | JWT | Faqat so'rovchining o'z sharhi / like'i; boshqalarniki o'zgarmaydi. | OK |
| DELETE | `/api/v1/venues/{target_id}/reviews/mine/` | O'z sharhimni o'chirish | USER | — | JWT | Faqat so'rovchining o'z sharhi / like'i; boshqalarniki o'zgarmaydi. | OK |

## Rollar bo'yicha

### PUBLIC (22)

* `GET /api/v1/admin/storage/google/callback/` — Google OAuth callback (brauzer redirect)
* `GET /api/v1/auth/csrf/` — CSRF cookie olish (web panel)
* `POST /api/v1/auth/login/` — Tizimga kirish (telefon + parol)
* `POST /api/v1/auth/logout/` — Tizimdan chiqish
* `POST /api/v1/auth/refresh/` — Tokenni yangilash (rotation)
* `POST /api/v1/auth/register/` — Ro'yxatdan o'tish (telefon + parol)
* `GET /api/v1/health/live/` — Liveness — jarayon ishlayaptimi
* `GET /api/v1/health/ready/` — Readiness — bog'liqliklar (database, cache) tayyormi
* `POST /api/v1/public/partner-applications/` — Hamkorlik arizasi (studiya / to'yxona) — landing sahifadan
* `GET /api/v1/public/partner-applications/challenge/` — Bot tekshiruvi uchun bir martalik topshiriq (proof-of-work)
* `GET /api/v1/public/studios/` — Studiyalar (ommaviy katalog, reyting bo'yicha)
* `GET /api/v1/public/studios/{id}/` — Studiya (ommaviy profil, portfolio va reels)
* `GET /api/v1/public/studios/{id}/schedule/` — Studiya grafigi: band, dam olish va bo'sh kunlar
* `GET /api/v1/public/studios/{studio_id}/portfolio/{item_id}/comments/` — Portfolio ishining izohlari
* `GET /api/v1/public/studios/{studio_id}/portfolio/{item_id}/file/{part}/` — Portfolio fayli (rasm, reels videosi yoki muqovasi)
* `GET /api/v1/public/studios/{target_id}/reviews/` — Sharhlar, reyting va like soni
* `GET /api/v1/subscriptions/plans/` — Obuna tariflari
* `GET /api/v1/venues/` — To'yxonalar katalogi (reyting va like bo'yicha)
* `GET /api/v1/venues/search/` — Sana bo'yicha bo'sh to'yxonalarni qidirish
* `GET /api/v1/venues/{id}/` — To'yxona (ommaviy ma'lumot, zallar va smenalar)
* `GET /api/v1/venues/{id}/availability/` — To'yxona bo'sh smenalari (kalendar)
* `GET /api/v1/venues/{target_id}/reviews/` — Sharhlar, reyting va like soni

### USER (53)

* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/me/ceremonies/` — Menga biriktirilgan marosimlar
* `GET /api/v1/me/ceremonies/{ceremony_id}/media/` — Marosim rasm va videolari
* `GET /api/v1/me/ceremonies/{ceremony_id}/media/{media_id}/download/` — Faylni yuklab olish (faqat obunasi faol ega, logosiz original)
* `GET /api/v1/me/ceremonies/{ceremony_id}/media/{media_id}/stream/` — Faylni ko'rish (oqim, Range)
* `GET /api/v1/me/ceremonies/{ceremony_id}/media/{media_id}/thumbnail/` — Kichik rasm (preview)
* `GET /api/v1/me/ceremonies/{id}/` — Menga biriktirilgan marosim
* `PATCH /api/v1/me/ceremonies/{id}/folder/` — Papka nomini o'zgartirish (faqat o'zim uchun)
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
* `GET /api/v1/me/studio-chats/` — Studiyalar bilan suhbatlarim
* `GET /api/v1/me/studio-chats/{studio_id}/` — Studiya bilan suhbat (xabarlar)
* `POST /api/v1/me/studio-chats/{studio_id}/` — Studiyaga xabar yozish
* `GET /api/v1/me/subscriptions/` — Mening obuna so'rovlarim va obunalarim
* `POST /api/v1/me/subscriptions/` — Obuna so'rovi yuborish (to'lov admin tomonidan tasdiqlanadi)
* `GET /api/v1/me/subscriptions/status/` — Obuna holati, limitlar, tariflar va to'lov ma'lumotlari
* `GET /api/v1/me/subscriptions/targets/` — Galichka sotib olish mumkin bo'lgan o'z bizneslarim
* `POST /api/v1/me/subscriptions/{id}/cancel/` — Kutilayotgan so'rovni bekor qilish
* `GET /api/v1/me/venue-bookings/` — Mening to'yxona bronlarim
* `POST /api/v1/me/venue-bookings/` — To'yxona smenasiga bron so'rovi yuborish
* `GET /api/v1/me/venue-bookings/{id}/` — Bron tafsiloti
* `POST /api/v1/me/venue-bookings/{id}/cancel/` — Bron / so'rovni bekor qilish
* `POST /api/v1/public/studios/{studio_id}/portfolio/{item_id}/comments/` — Izoh yozish
* `DELETE /api/v1/public/studios/{studio_id}/portfolio/{item_id}/comments/{comment_id}/` — O'z izohimni o'chirish
* `PUT /api/v1/public/studios/{studio_id}/portfolio/{item_id}/reaction/` — Portfolio ishiga like / dislike
* `DELETE /api/v1/public/studios/{studio_id}/portfolio/{item_id}/reaction/` — Like / dislike'ni olib tashlash
* `POST /api/v1/public/studios/{target_id}/like/` — Like bosish
* `DELETE /api/v1/public/studios/{target_id}/like/` — Like'ni olib tashlash
* `PUT /api/v1/public/studios/{target_id}/reviews/mine/` — Baho va izoh qoldirish / yangilash
* `DELETE /api/v1/public/studios/{target_id}/reviews/mine/` — O'z sharhimni o'chirish
* `GET /api/v1/support/tickets/` — Mening yordam xatlarim
* `POST /api/v1/support/tickets/` — Yordam xati yuborish
* `GET /api/v1/support/tickets/summary/` — Xatlarim soni (javob kelganlar — menyu belgisi uchun)
* `GET /api/v1/support/tickets/{id}/` — Yordam xati (yozishmalar bilan)
* `POST /api/v1/support/tickets/{id}/close/` — Xatni yopish (muammo hal bo'ldi)
* `POST /api/v1/support/tickets/{id}/messages/` — Xatga qo'shimcha yozish (yopilgan xat qayta ochiladi)
* `POST /api/v1/venues/{target_id}/like/` — Like bosish
* `DELETE /api/v1/venues/{target_id}/like/` — Like'ni olib tashlash
* `PUT /api/v1/venues/{target_id}/reviews/mine/` — Baho va izoh qoldirish / yangilash
* `DELETE /api/v1/venues/{target_id}/reviews/mine/` — O'z sharhimni o'chirish

### STUDIO (46)

* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/ceremonies/` — Marosimlar ro'yxati
* `POST /api/v1/ceremonies/` — Marosim yaratish
* `GET /api/v1/ceremonies/{ceremony_id}/media/` — Marosimning yuklangan fayllari va holati
* `POST /api/v1/ceremonies/{ceremony_id}/media/uploads/` — Media yuklashni boshlash (Google Drive resumable sessiya)
* `GET /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/` — Yuklash holati (Google'dan jonli progress)
* `DELETE /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/` — Tugallanmagan yuklashni ro'yxatdan o'chirish
* `POST /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/cancel/` — Yuklashni bekor qilish
* `POST /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/complete/` — Yuklashni yakunlash va tekshirish
* `POST /api/v1/ceremonies/{ceremony_id}/media/{media_id}/delete-request/` — Tayyor faylni o'chirishni so'rash (admin tasdiqlaydi)
* `POST /api/v1/ceremonies/{ceremony_id}/media/{media_id}/delete-request/cancel/` — O'chirish so'rovini qaytarib olish
* `GET /api/v1/ceremonies/{id}/` — Marosim ma'lumotlari
* `PATCH /api/v1/ceremonies/{id}/` — Marosimni tahrirlash
* `GET /api/v1/ceremonies/{id}/owners/` — Marosim egalari va egalik takliflari
* `POST /api/v1/ceremonies/{id}/owners/invite/` — Marosim egasini telefon yoki JSHSHIR orqali taklif qilish
* `GET /api/v1/ceremonies/{id}/participants/` — Marosim ishtirokchilari (deprecated — /owners/)
* `POST /api/v1/ceremonies/{id}/participants/` — Ishtirokchini telefon orqali taklif qilish (deprecated — /owners/invite/)
* `DELETE /api/v1/ceremonies/{id}/participants/{participant_id}/` — Ishtirokchini olib tashlash (deprecated)
* `GET /api/v1/me/subscriptions/` — Mening obuna so'rovlarim va obunalarim
* `POST /api/v1/me/subscriptions/` — Obuna so'rovi yuborish (to'lov admin tomonidan tasdiqlanadi)
* `GET /api/v1/me/subscriptions/status/` — Obuna holati, limitlar, tariflar va to'lov ma'lumotlari
* `GET /api/v1/me/subscriptions/targets/` — Galichka sotib olish mumkin bo'lgan o'z bizneslarim
* `POST /api/v1/me/subscriptions/{id}/cancel/` — Kutilayotgan so'rovni bekor qilish
* `GET /api/v1/studios/me/` — Mening studiyalarim
* `GET /api/v1/studios/me/ceremonies/` — Mening studiyamning marosimlari
* `GET /api/v1/studios/me/{studio_id}/chats/` — Mijozlar bilan suhbatlar
* `GET /api/v1/studios/me/{studio_id}/chats/{conversation_id}/` — Mijoz bilan suhbat (xabarlar)
* `POST /api/v1/studios/me/{studio_id}/chats/{conversation_id}/` — Mijozga javob yozish
* `GET /api/v1/studios/me/{studio_id}/images/` — Studiya portfoliosi (rasmlar va reels, like / izoh soni bilan)
* `POST /api/v1/studios/me/{studio_id}/images/` — Portfolioga rasm qo'shish
* `PATCH /api/v1/studios/me/{studio_id}/images/{image_id}/` — Portfolio ishining izohini (caption) o'zgartirish
* `DELETE /api/v1/studios/me/{studio_id}/images/{image_id}/` — Portfoliodan rasm / videoni o'chirish
* `GET /api/v1/studios/me/{studio_id}/images/{image_id}/comments/` — Portfolio ishiga yozilgan izohlar
* `DELETE /api/v1/studios/me/{studio_id}/images/{image_id}/comments/{comment_id}/` — Izohni o'chirish (studiya moderatsiyasi)
* `POST /api/v1/studios/me/{studio_id}/reels/` — Portfolioga reels (vertikal video) qo'shish
* `GET /api/v1/studios/me/{studio_id}/schedule/` — Studiya grafigi (marosimlar, band va dam olish kunlari)
* `PATCH /api/v1/studios/me/{studio_id}/schedule/` — Haftalik dam olish kunlari
* `PUT /api/v1/studios/me/{studio_id}/schedule/days/{day}/` — Kunni band / dam olish deb belgilash (status=null — tozalash)
* `GET /api/v1/studios/me/{studio_id}/storage/` — Portfolio joyi (ishlatilgan / ajratilgan)
* `GET /api/v1/support/tickets/` — Mening yordam xatlarim
* `POST /api/v1/support/tickets/` — Yordam xati yuborish
* `GET /api/v1/support/tickets/summary/` — Xatlarim soni (javob kelganlar — menyu belgisi uchun)
* `GET /api/v1/support/tickets/{id}/` — Yordam xati (yozishmalar bilan)
* `POST /api/v1/support/tickets/{id}/close/` — Xatni yopish (muammo hal bo'ldi)
* `POST /api/v1/support/tickets/{id}/messages/` — Xatga qo'shimcha yozish (yopilgan xat qayta ochiladi)

### VENUE_OWNER (36)

* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/me/subscriptions/` — Mening obuna so'rovlarim va obunalarim
* `POST /api/v1/me/subscriptions/` — Obuna so'rovi yuborish (to'lov admin tomonidan tasdiqlanadi)
* `GET /api/v1/me/subscriptions/status/` — Obuna holati, limitlar, tariflar va to'lov ma'lumotlari
* `GET /api/v1/me/subscriptions/targets/` — Galichka sotib olish mumkin bo'lgan o'z bizneslarim
* `POST /api/v1/me/subscriptions/{id}/cancel/` — Kutilayotgan so'rovni bekor qilish
* `GET /api/v1/support/tickets/` — Mening yordam xatlarim
* `POST /api/v1/support/tickets/` — Yordam xati yuborish
* `GET /api/v1/support/tickets/summary/` — Xatlarim soni (javob kelganlar — menyu belgisi uchun)
* `GET /api/v1/support/tickets/{id}/` — Yordam xati (yozishmalar bilan)
* `POST /api/v1/support/tickets/{id}/close/` — Xatni yopish (muammo hal bo'ldi)
* `POST /api/v1/support/tickets/{id}/messages/` — Xatga qo'shimcha yozish (yopilgan xat qayta ochiladi)
* `GET /api/v1/venue-owner/venues/` — Mening to'yxonalarim
* `POST /api/v1/venue-owner/venues/` — To'yxona yaratish (PRIVATE holatda)
* `GET /api/v1/venue-owner/venues/{id}/` — To'yxona ma'lumotlari (egasi uchun)
* `PATCH /api/v1/venue-owner/venues/{id}/` — To'yxonani tahrirlash
* `GET /api/v1/venue-owner/venues/{id}/bookings/` — Bronlar va so'rovlar
* `POST /api/v1/venue-owner/venues/{id}/bookings/` — Jadvalga yozuv qo'shish (o'z mijozi yoki yopiq smena)
* `PATCH /api/v1/venue-owner/venues/{id}/bookings/{booking_id}/` — Yozuv tafsilotlarini tahrirlash
* `POST /api/v1/venue-owner/venues/{id}/bookings/{booking_id}/cancel/` — Yozuvni bekor qilish (smena bo'shaydi)
* `POST /api/v1/venue-owner/venues/{id}/bookings/{booking_id}/confirm/` — So'rovni tasdiqlash (smena band bo'ladi)
* `POST /api/v1/venue-owner/venues/{id}/bookings/{booking_id}/reject/` — So'rovni rad etish
* `GET /api/v1/venue-owner/venues/{id}/calendar/` — Jadval: zallar, smenalar va shu oraliqdagi barcha yozuvlar
* `GET /api/v1/venue-owner/venues/{id}/halls/` — To'yxona zallari
* `POST /api/v1/venue-owner/venues/{id}/halls/` — Zal qo'shish
* `PATCH /api/v1/venue-owner/venues/{id}/halls/{hall_id}/` — Zalni tahrirlash
* `GET /api/v1/venue-owner/venues/{id}/halls/{hall_id}/sessions/` — Zal smenalari
* `POST /api/v1/venue-owner/venues/{id}/halls/{hall_id}/sessions/` — Zalga smena qo'shish
* `PATCH /api/v1/venue-owner/venues/{id}/halls/{hall_id}/sessions/{session_id}/` — Smenani tahrirlash / o'chirish-yoqish
* `GET /api/v1/venue-owner/venues/{id}/images/` — Galereya rasmlari
* `POST /api/v1/venue-owner/venues/{id}/images/` — Galereyaga rasm qo'shish
* `DELETE /api/v1/venue-owner/venues/{id}/images/{image_id}/` — Galereyadan rasmni o'chirish
* `GET /api/v1/venue-owner/venues/{id}/members/` — To'yxona a'zolari
* `POST /api/v1/venue-owner/venues/{id}/members/` — A'zo qo'shish (telefon raqam bo'yicha)
* `PATCH /api/v1/venue-owner/venues/{id}/members/{membership_id}/` — A'zoning rolini / faolligini o'zgartirish

### ADMIN (79)

* `GET /api/v1/admin/media-deletion-requests/` — Media o'chirish so'rovlari
* `GET /api/v1/admin/media-deletion-requests/summary/` — Kutilayotgan so'rovlar soni (menyu belgisi uchun)
* `GET /api/v1/admin/media-deletion-requests/{id}/` — O'chirish so'rovi tafsiloti
* `POST /api/v1/admin/media-deletion-requests/{id}/approve/` — Tasdiqlash: fayl Drive savatiga o'tadi va ilovadan o'chadi
* `POST /api/v1/admin/media-deletion-requests/{id}/reject/` — Rad etish (fayl qoladi)
* `GET /api/v1/admin/platform-policy/` — Rollar imkoniyatlarini ko'rish
* `PATCH /api/v1/admin/platform-policy/` — Rollar imkoniyatlarini yoqish / o'chirish
* `GET /api/v1/admin/reviews/` — Barcha sharhlar (moderatsiya)
* `GET /api/v1/admin/reviews/{id}/` — Sharh tafsiloti
* `PATCH /api/v1/admin/reviews/{id}/` — Sharhni yashirish / ko'rsatish
* `DELETE /api/v1/admin/reviews/{id}/` — Sharhni o'chirish
* `GET /api/v1/admin/subscription-plans/` — Tariflar (barchasi)
* `POST /api/v1/admin/subscription-plans/` — Tarif qo'shish
* `PATCH /api/v1/admin/subscription-plans/{id}/` — Tarif narxi / muddati / limitini o'zgartirish
* `GET /api/v1/admin/subscription-settings/` — To'lov ma'lumotlari (mijozga ko'rsatiladi)
* `PATCH /api/v1/admin/subscription-settings/` — To'lov ma'lumotlarini o'zgartirish
* `GET /api/v1/admin/subscriptions/` — Obunalar va to'lovlar
* `POST /api/v1/admin/subscriptions/` — Foydalanuvchiga obuna berish (to'lov qayd etiladi)
* `GET /api/v1/admin/subscriptions/summary/` — Obunalar statistikasi (so'rovlar, faollar, tushum)
* `GET /api/v1/admin/subscriptions/{id}/` — Obuna tafsiloti
* `POST /api/v1/admin/subscriptions/{id}/approve/` — To'lovni qayd etib tasdiqlash
* `POST /api/v1/admin/subscriptions/{id}/cancel/` — Obunani bekor qilish
* `POST /api/v1/admin/subscriptions/{id}/reject/` — So'rovni rad etish
* `GET /api/v1/admin/support/applications/` — Hamkorlik arizalari (studiya / to'yxona)
* `GET /api/v1/admin/support/applications/summary/` — Yangi arizalar soni
* `GET /api/v1/admin/support/applications/{id}/` — Ariza tafsiloti
* `PATCH /api/v1/admin/support/applications/{id}/` — Ariza holati va izohi
* `GET /api/v1/admin/support/tickets/` — Kelgan yordam xatlari
* `GET /api/v1/admin/support/tickets/summary/` — Javob kutayotgan xatlar soni (javob bera oladiganlari)
* `GET /api/v1/admin/support/tickets/{id}/` — Yordam xati (yozishmalar, kim javob bergani)
* `POST /api/v1/admin/support/tickets/{id}/close/` — Xatni yopish
* `POST /api/v1/admin/support/tickets/{id}/messages/` — Javob yozish
* `GET /api/v1/admin/venues/` — To'yxonalar ro'yxati (panel)
* `POST /api/v1/admin/venues/` — To'yxona qo'shish (egasi bilan)
* `GET /api/v1/admin/venues/{id}/` — To'yxona ma'lumotlari (panel)
* `PATCH /api/v1/admin/venues/{id}/` — To'yxonani tahrirlash / bloklash / holat
* `DELETE /api/v1/admin/venues/{id}/` — To'yxonani o'chirish (soft delete)
* `GET /api/v1/admin/venues/{id}/bookings/` — Bronlar va so'rovlar (panel)
* `POST /api/v1/admin/venues/{id}/bookings/` — Jadvalga yozuv qo'shish (panel)
* `PATCH /api/v1/admin/venues/{id}/bookings/{booking_id}/` — Yozuv tafsilotlarini tahrirlash (panel)
* `POST /api/v1/admin/venues/{id}/bookings/{booking_id}/cancel/` — Yozuvni bekor qilish (panel)
* `POST /api/v1/admin/venues/{id}/bookings/{booking_id}/confirm/` — So'rovni tasdiqlash (panel)
* `POST /api/v1/admin/venues/{id}/bookings/{booking_id}/reject/` — So'rovni rad etish (panel)
* `GET /api/v1/admin/venues/{id}/calendar/` — To'yxona jadvali: zallar, smenalar va yozuvlar (panel)
* `POST /api/v1/admin/venues/{id}/halls/` — Zal qo'shish (panel)
* `PATCH /api/v1/admin/venues/{id}/halls/{hall_id}/` — Zalni tahrirlash (panel)
* `GET /api/v1/admin/venues/{id}/halls/{hall_id}/sessions/` — Zal smenalari (panel)
* `POST /api/v1/admin/venues/{id}/halls/{hall_id}/sessions/` — Zalga smena qo'shish (panel)
* `PATCH /api/v1/admin/venues/{id}/halls/{hall_id}/sessions/{session_id}/` — Smenani tahrirlash / o'chirish-yoqish (panel)
* `POST /api/v1/admin/venues/{id}/images/` — Galereyaga rasm qo'shish (panel)
* `DELETE /api/v1/admin/venues/{id}/images/{image_id}/` — Galereyadan rasmni o'chirish (panel)
* `GET /api/v1/auth/me/` — Mening profilim
* `PATCH /api/v1/auth/me/` — Profilni tahrirlash
* `GET /api/v1/dashboard/overview/` — Dashboard statistikasi
* `GET /api/v1/studios/` — Studiyalar ro'yxati
* `POST /api/v1/studios/` — Studiya qo'shish
* `GET /api/v1/studios/{id}/` — Studiya ma'lumotlari
* `PATCH /api/v1/studios/{id}/` — Studiyani tahrirlash
* `DELETE /api/v1/studios/{id}/` — Studiyani o'chirish (soft delete)
* `GET /api/v1/studios/{id}/calendar/` — Studiya jadvali: oraliqdagi marosimlar (panel)
* `POST /api/v1/studios/{id}/images/` — Portfolioga rasm qo'shish (panel)
* `DELETE /api/v1/studios/{id}/images/{image_id}/` — Portfoliodan rasmni o'chirish (panel)
* `GET /api/v1/support/tickets/` — Mening yordam xatlarim
* `POST /api/v1/support/tickets/` — Yordam xati yuborish
* `GET /api/v1/support/tickets/summary/` — Xatlarim soni (javob kelganlar — menyu belgisi uchun)
* `GET /api/v1/support/tickets/{id}/` — Yordam xati (yozishmalar bilan)
* `POST /api/v1/support/tickets/{id}/close/` — Xatni yopish (muammo hal bo'ldi)
* `POST /api/v1/support/tickets/{id}/messages/` — Xatga qo'shimcha yozish (yopilgan xat qayta ochiladi)
* `GET /api/v1/users/` — Mijozlar ro'yxati (USER, STUDIO, VENUE_OWNER)
* `POST /api/v1/users/` — Mijoz qo'shish
* `GET /api/v1/users/{id}/` — Mijoz ma'lumotlari
* `PATCH /api/v1/users/{id}/` — Mijozni tahrirlash
* `DELETE /api/v1/users/{id}/` — Mijozni o'chirish (soft delete)
* `GET /api/v1/users/{id}/features/` — Hisob imkoniyatlari (shu profil uchun)
* `PATCH /api/v1/users/{id}/features/` — Hisob imkoniyatlarini yoqish / o'chirish
* `GET /api/v1/users/{id}/folders/` — Foydalanuvchining marosim papkalari
* `PATCH /api/v1/users/{id}/folders/{ceremony_id}/` — Foydalanuvchi papkasi nomini o'zgartirish
* `GET /api/v1/users/{id}/pinfl/` — To'liq JSHSHIR (audit qilinadi)
* `POST /api/v1/users/{id}/verify-phone/` — Telefon raqamini qo'lda tasdiqlash

### SUPER_ADMIN (109)

* `GET /api/v1/admin/media-deletion-requests/` — Media o'chirish so'rovlari
* `GET /api/v1/admin/media-deletion-requests/summary/` — Kutilayotgan so'rovlar soni (menyu belgisi uchun)
* `GET /api/v1/admin/media-deletion-requests/{id}/` — O'chirish so'rovi tafsiloti
* `POST /api/v1/admin/media-deletion-requests/{id}/approve/` — Tasdiqlash: fayl Drive savatiga o'tadi va ilovadan o'chadi
* `POST /api/v1/admin/media-deletion-requests/{id}/reject/` — Rad etish (fayl qoladi)
* `GET /api/v1/admin/platform-policy/` — Rollar imkoniyatlarini ko'rish
* `PATCH /api/v1/admin/platform-policy/` — Rollar imkoniyatlarini yoqish / o'chirish
* `GET /api/v1/admin/reviews/` — Barcha sharhlar (moderatsiya)
* `GET /api/v1/admin/reviews/{id}/` — Sharh tafsiloti
* `PATCH /api/v1/admin/reviews/{id}/` — Sharhni yashirish / ko'rsatish
* `DELETE /api/v1/admin/reviews/{id}/` — Sharhni o'chirish
* `GET /api/v1/admin/storage/google/connect/` — Google Drive'ni ulashni boshlash
* `POST /api/v1/admin/storage/google/disconnect/` — Google Drive'ni uzish
* `GET /api/v1/admin/storage/google/status/` — Google Drive ulanish holati
* `POST /api/v1/admin/storage/google/test/` — Ulanishni tekshirish
* `GET /api/v1/admin/subscription-plans/` — Tariflar (barchasi)
* `POST /api/v1/admin/subscription-plans/` — Tarif qo'shish
* `PATCH /api/v1/admin/subscription-plans/{id}/` — Tarif narxi / muddati / limitini o'zgartirish
* `GET /api/v1/admin/subscription-settings/` — To'lov ma'lumotlari (mijozga ko'rsatiladi)
* `PATCH /api/v1/admin/subscription-settings/` — To'lov ma'lumotlarini o'zgartirish
* `GET /api/v1/admin/subscriptions/` — Obunalar va to'lovlar
* `POST /api/v1/admin/subscriptions/` — Foydalanuvchiga obuna berish (to'lov qayd etiladi)
* `GET /api/v1/admin/subscriptions/summary/` — Obunalar statistikasi (so'rovlar, faollar, tushum)
* `GET /api/v1/admin/subscriptions/{id}/` — Obuna tafsiloti
* `POST /api/v1/admin/subscriptions/{id}/approve/` — To'lovni qayd etib tasdiqlash
* `POST /api/v1/admin/subscriptions/{id}/cancel/` — Obunani bekor qilish
* `POST /api/v1/admin/subscriptions/{id}/reject/` — So'rovni rad etish
* `GET /api/v1/admin/support/applications/` — Hamkorlik arizalari (studiya / to'yxona)
* `GET /api/v1/admin/support/applications/summary/` — Yangi arizalar soni
* `GET /api/v1/admin/support/applications/{id}/` — Ariza tafsiloti
* `PATCH /api/v1/admin/support/applications/{id}/` — Ariza holati va izohi
* `GET /api/v1/admin/support/tickets/` — Kelgan yordam xatlari
* `GET /api/v1/admin/support/tickets/summary/` — Javob kutayotgan xatlar soni (javob bera oladiganlari)
* `GET /api/v1/admin/support/tickets/{id}/` — Yordam xati (yozishmalar, kim javob bergani)
* `POST /api/v1/admin/support/tickets/{id}/close/` — Xatni yopish
* `POST /api/v1/admin/support/tickets/{id}/messages/` — Javob yozish
* `GET /api/v1/admin/venues/` — To'yxonalar ro'yxati (panel)
* `POST /api/v1/admin/venues/` — To'yxona qo'shish (egasi bilan)
* `GET /api/v1/admin/venues/{id}/` — To'yxona ma'lumotlari (panel)
* `PATCH /api/v1/admin/venues/{id}/` — To'yxonani tahrirlash / bloklash / holat
* `DELETE /api/v1/admin/venues/{id}/` — To'yxonani o'chirish (soft delete)
* `GET /api/v1/admin/venues/{id}/bookings/` — Bronlar va so'rovlar (panel)
* `POST /api/v1/admin/venues/{id}/bookings/` — Jadvalga yozuv qo'shish (panel)
* `PATCH /api/v1/admin/venues/{id}/bookings/{booking_id}/` — Yozuv tafsilotlarini tahrirlash (panel)
* `POST /api/v1/admin/venues/{id}/bookings/{booking_id}/cancel/` — Yozuvni bekor qilish (panel)
* `POST /api/v1/admin/venues/{id}/bookings/{booking_id}/confirm/` — So'rovni tasdiqlash (panel)
* `POST /api/v1/admin/venues/{id}/bookings/{booking_id}/reject/` — So'rovni rad etish (panel)
* `GET /api/v1/admin/venues/{id}/calendar/` — To'yxona jadvali: zallar, smenalar va yozuvlar (panel)
* `POST /api/v1/admin/venues/{id}/halls/` — Zal qo'shish (panel)
* `PATCH /api/v1/admin/venues/{id}/halls/{hall_id}/` — Zalni tahrirlash (panel)
* `GET /api/v1/admin/venues/{id}/halls/{hall_id}/sessions/` — Zal smenalari (panel)
* `POST /api/v1/admin/venues/{id}/halls/{hall_id}/sessions/` — Zalga smena qo'shish (panel)
* `PATCH /api/v1/admin/venues/{id}/halls/{hall_id}/sessions/{session_id}/` — Smenani tahrirlash / o'chirish-yoqish (panel)
* `POST /api/v1/admin/venues/{id}/images/` — Galereyaga rasm qo'shish (panel)
* `DELETE /api/v1/admin/venues/{id}/images/{image_id}/` — Galereyadan rasmni o'chirish (panel)
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
* `GET /api/v1/ceremonies/{ceremony_id}/media/` — Marosimning yuklangan fayllari va holati
* `POST /api/v1/ceremonies/{ceremony_id}/media/uploads/` — Media yuklashni boshlash (Google Drive resumable sessiya)
* `GET /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/` — Yuklash holati (Google'dan jonli progress)
* `DELETE /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/` — Tugallanmagan yuklashni ro'yxatdan o'chirish
* `POST /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/cancel/` — Yuklashni bekor qilish
* `POST /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/complete/` — Yuklashni yakunlash va tekshirish
* `POST /api/v1/ceremonies/{ceremony_id}/media/{media_id}/delete-request/` — Tayyor faylni o'chirishni so'rash (admin tasdiqlaydi)
* `POST /api/v1/ceremonies/{ceremony_id}/media/{media_id}/delete-request/cancel/` — O'chirish so'rovini qaytarib olish
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
* `GET /api/v1/studios/{id}/calendar/` — Studiya jadvali: oraliqdagi marosimlar (panel)
* `POST /api/v1/studios/{id}/images/` — Portfolioga rasm qo'shish (panel)
* `DELETE /api/v1/studios/{id}/images/{image_id}/` — Portfoliodan rasmni o'chirish (panel)
* `GET /api/v1/users/` — Mijozlar ro'yxati (USER, STUDIO, VENUE_OWNER)
* `POST /api/v1/users/` — Mijoz qo'shish
* `GET /api/v1/users/{id}/` — Mijoz ma'lumotlari
* `PATCH /api/v1/users/{id}/` — Mijozni tahrirlash
* `DELETE /api/v1/users/{id}/` — Mijozni o'chirish (soft delete)
* `GET /api/v1/users/{id}/features/` — Hisob imkoniyatlari (shu profil uchun)
* `PATCH /api/v1/users/{id}/features/` — Hisob imkoniyatlarini yoqish / o'chirish
* `GET /api/v1/users/{id}/folders/` — Foydalanuvchining marosim papkalari
* `PATCH /api/v1/users/{id}/folders/{ceremony_id}/` — Foydalanuvchi papkasi nomini o'zgartirish
* `GET /api/v1/users/{id}/pinfl/` — To'liq JSHSHIR (audit qilinadi)
* `POST /api/v1/users/{id}/verify-phone/` — Telefon raqamini qo'lda tasdiqlash

## Qo'shimcha shartlar

* `GET /api/v1/admin/platform-policy/`
  * Admin faqat Super Admin bergan platform ruxsatlari bilan.
* `PATCH /api/v1/admin/platform-policy/`
  * Admin faqat Super Admin bergan platform ruxsatlari bilan.
* `GET /api/v1/admin/storage/google/callback/`
  * JWT talab qilinmaydi (Google brauzer redirect'i), lekin faqat ulashni boshlagan faol SUPER_ADMIN uchun yakunlanadi: bir martalik `state` + brauzerga bog'lovchi httpOnly cookie
* `PATCH /api/v1/admin/subscription-plans/{id}/`
  * Yangi narx faqat keyingi so'rovlarga ta'sir qiladi.
* `POST /api/v1/admin/support/tickets/{id}/messages/`
  * Adminlarning xatlariga faqat SUPER_ADMIN javob beradi; o'z xatiga javob berilmaydi.
* `PATCH /api/v1/admin/venues/{id}/`
  * publication_status o'zgarishi uchun qo'shimcha `venues.publish`
* `POST /api/v1/admin/venues/{id}/images/`
  * Ko'pi bilan 20 ta rasm, har biri 5 MB gacha
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
* `POST /api/v1/ceremonies/{ceremony_id}/media/uploads/`
  * Har qanday faol studiya a'zosi (OWNER / MANAGER / UPLOADER) yoki SUPER_ADMIN.
  * Google Drive ulangan bo'lishi shart (aks holda 503 storage_unavailable).
  * Arxivlangan marosimga yuklab bo'lmaydi; tur va hajm cheklangan.
* `GET /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/`
  * upload_url faqat yuklashni boshlagan foydalanuvchiga qaytadi.
* `DELETE /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/`
  * Yuklashni boshlagan a'zo yoki studiya OWNER/MANAGER.
  * Faqat tugallanmagan fayl (UPLOADING / FAILED / CANCELLED / EXPIRED); tayyor fayl — so'rov orqali.
* `POST /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/cancel/`
  * Yuklashni boshlagan a'zo yoki studiya OWNER/MANAGER.
* `POST /api/v1/ceremonies/{ceremony_id}/media/uploads/{media_id}/complete/`
  * Har qanday faol studiya a'zosi (OWNER / MANAGER / UPLOADER) yoki SUPER_ADMIN.
  * Fayl Drive'dan qayta o'qilib tekshiriladi.
* `POST /api/v1/ceremonies/{ceremony_id}/media/{media_id}/delete-request/`
  * Har qanday faol studiya a'zosi (OWNER / MANAGER / UPLOADER) yoki SUPER_ADMIN.
  * Faqat READY fayl; bir faylga bitta kutilayotgan so'rov.
* `POST /api/v1/ceremonies/{ceremony_id}/media/{media_id}/delete-request/cancel/`
  * So'rovni yuborgan a'zo yoki studiya OWNER/MANAGER.
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
* `GET /api/v1/me/ceremonies/{ceremony_id}/media/{media_id}/download/`
  * Faqat obunasi faol marosim EGASI; ko'ruvchi — 403, obunasiz ega — 403 subscription_required
  * Har bir yuklab olish audit qilinadi
* `GET /api/v1/me/ceremonies/{ceremony_id}/media/{media_id}/stream/`
  * HTTP Range qo'llab-quvvatlanadi (video uchun)
  * Content-Disposition: inline
  * Obunasi faol ega — original; boshqalar — logoli nusxa (video tayyor bo'lmasa 409 watermark_pending)
* `GET /api/v1/me/ceremonies/{ceremony_id}/media/{media_id}/thumbnail/`
  * Obunasi faol ega bo'lmasa — MarosimGo logosi bilan
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
* `GET /api/v1/me/studio-chats/{studio_id}/`
  * Faqat faol studiyalar; xodimlar, mijozlar va marosim nomlari qaytmaydi.
* `POST /api/v1/me/studio-chats/{studio_id}/`
  * Faqat faol studiyalar; xodimlar, mijozlar va marosim nomlari qaytmaydi.
  * Faqat galichkasi faol studiya (aks holda 403 badge_required).
* `POST /api/v1/me/subscriptions/`
  * Bir hisob yoki biznes uchun bir vaqtda bitta kutilayotgan so'rov.
* `POST /api/v1/me/venue-bookings/`
  * Faqat ommaga chiqqan to'yxonaning faol smenasi, bugundan boshlab 2 yilgacha.
  * Smena band bo'lsa 409; bir vaqtda ko'pi bilan 10 ta ochiq so'rov.
  * So'rov smenani band qilmaydi — to'yxona tasdiqlaganda band bo'ladi.
* `POST /api/v1/public/partner-applications/`
  * IP bo'yicha cheklangan (partner_apply); bir martalik proof-of-work topshiriq, kamida 3 s; bitta raqamdan kuniga 3 ta; javobda shaxsiy ma'lumot yo'q.
* `GET /api/v1/public/partner-applications/challenge/`
  * IP bo'yicha cheklangan (partner_challenge).
* `GET /api/v1/public/studios/`
  * Faqat faol studiyalar; xodimlar, mijozlar va marosim nomlari qaytmaydi.
* `GET /api/v1/public/studios/{id}/`
  * Faqat faol studiyalar; xodimlar, mijozlar va marosim nomlari qaytmaydi.
* `GET /api/v1/public/studios/{id}/schedule/`
  * Faqat faol studiyalar; xodimlar, mijozlar va marosim nomlari qaytmaydi.
* `GET /api/v1/public/studios/{studio_id}/portfolio/{item_id}/comments/`
  * Faqat faol studiyalar; xodimlar, mijozlar va marosim nomlari qaytmaydi.
  * Yashirilgan izohlar ko'rinmaydi.
* `POST /api/v1/public/studios/{studio_id}/portfolio/{item_id}/comments/`
  * Faqat faol studiyalar; xodimlar, mijozlar va marosim nomlari qaytmaydi.
  * Faqat galichkasi faol studiya (aks holda 403 badge_required).
* `GET /api/v1/public/studios/{studio_id}/portfolio/{item_id}/file/{part}/`
  * Ommaga: faqat ko'rinadigan ishlar (reels — galichka faol bo'lsa); studiya a'zolari va studios.view ruxsatli xodimlar — barchasi
  * HTTP Range qo'llab-quvvatlanadi (video uchun)
* `PUT /api/v1/public/studios/{studio_id}/portfolio/{item_id}/reaction/`
  * Faqat faol studiyalar; xodimlar, mijozlar va marosim nomlari qaytmaydi.
  * Faqat galichkasi faol studiya (aks holda 403 badge_required).
* `DELETE /api/v1/public/studios/{studio_id}/portfolio/{item_id}/reaction/`
  * Faqat faol studiyalar; xodimlar, mijozlar va marosim nomlari qaytmaydi.
  * Faqat galichkasi faol studiya (aks holda 403 badge_required).
* `POST /api/v1/public/studios/{target_id}/like/`
  * Faqat ommaga ochiq (faol, tasdiqlangan) to'yxona / faol studiya; boshqasi 404.
* `DELETE /api/v1/public/studios/{target_id}/like/`
  * Faqat ommaga ochiq (faol, tasdiqlangan) to'yxona / faol studiya; boshqasi 404.
* `GET /api/v1/public/studios/{target_id}/reviews/`
  * Faqat ommaga ochiq (faol, tasdiqlangan) to'yxona / faol studiya; boshqasi 404.
  * Yashirilgan sharhlar ko'rinmaydi.
* `PUT /api/v1/public/studios/{target_id}/reviews/mine/`
  * Faqat ommaga ochiq (faol, tasdiqlangan) to'yxona / faol studiya; boshqasi 404.
* `DELETE /api/v1/public/studios/{target_id}/reviews/mine/`
  * Faqat ommaga ochiq (faol, tasdiqlangan) to'yxona / faol studiya; boshqasi 404.
* `POST /api/v1/studios/me/{studio_id}/chats/{conversation_id}/`
  * Faqat galichkasi faol studiya (aks holda 403 badge_required).
* `POST /api/v1/studios/me/{studio_id}/images/`
  * Ko'pi bilan 20 ta rasm, har biri 5 MB gacha
* `POST /api/v1/studios/me/{studio_id}/reels/`
  * Faqat galichkasi faol studiya (aks holda 403 badge_required).
  * Ko'pi bilan 15 ta vertikal video, 1–90 soniya
* `POST /api/v1/studios/{id}/images/`
  * Ko'pi bilan 20 ta rasm, har biri 5 MB gacha
* `POST /api/v1/support/tickets/`
  * ADMIN xati Super Admin'ga boradi; boshqalarniki — support.view ruxsati bor adminlarga.
* `DELETE /api/v1/users/{id}/`
  * Faol studiyaning mas'ul shaxsini o'chirib bo'lmaydi (409 conflict)
* `PATCH /api/v1/users/{id}/features/`
  * Faqat shu hisob roliga tegishli imkoniyat kodlari
* `GET /api/v1/users/{id}/folders/`
  * Faqat USER: egasi yoki ko'ruvchisi bo'lgan marosimlar
* `PATCH /api/v1/users/{id}/folders/{ceremony_id}/`
  * Faqat shu hisob ochishi mumkin bo'lgan marosim; boshqasi 404
* `GET /api/v1/users/{id}/pinfl/`
  * Har bir ko'rish audit qilinadi (PINFL_REVEAL)
  * Throttle: pinfl_reveal
* `POST /api/v1/venue-owner/venues/`
  * Yaratuvchi OWNER a'zo bo'ladi; standart 'Asosiy zal' ochiladi.
  * publication_status=PRIVATE, is_active — faqat admin o'zgartiradi.
* `PATCH /api/v1/venue-owner/venues/{id}/`
  * A'zolik roli `EDIT_PROFILE` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `GET /api/v1/venue-owner/venues/{id}/bookings/`
  * POST CONFIRMED: A'zolik roli `MANAGE_BOOKINGS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * POST BLOCKED: A'zolik roli `MANAGE_SCHEDULE` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
  * Band smenaga ikkinchi yozuv — 409 (DB unique index + qator qulfi).
* `POST /api/v1/venue-owner/venues/{id}/bookings/`
  * POST CONFIRMED: A'zolik roli `MANAGE_BOOKINGS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * POST BLOCKED: A'zolik roli `MANAGE_SCHEDULE` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
  * Band smenaga ikkinchi yozuv — 409 (DB unique index + qator qulfi).
* `PATCH /api/v1/venue-owner/venues/{id}/bookings/{booking_id}/`
  * BLOCKED: MANAGE_SCHEDULE, boshqalar: MANAGE_BOOKINGS
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `POST /api/v1/venue-owner/venues/{id}/bookings/{booking_id}/cancel/`
  * BLOCKED: MANAGE_SCHEDULE, boshqalar: MANAGE_BOOKINGS
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `POST /api/v1/venue-owner/venues/{id}/bookings/{booking_id}/confirm/`
  * A'zolik roli `MANAGE_BOOKINGS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
  * Shu smenaga boshqa kutilayotgan so'rovlar avtomatik rad etiladi; band bo'lsa 409.
* `POST /api/v1/venue-owner/venues/{id}/bookings/{booking_id}/reject/`
  * A'zolik roli `MANAGE_BOOKINGS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `GET /api/v1/venue-owner/venues/{id}/calendar/`
  * Har qanday faol a'zo (VIEW).
  * Oraliq ko'pi bilan 62 kun.
* `GET /api/v1/venue-owner/venues/{id}/halls/`
  * POST: A'zolik roli `MANAGE_HALLS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `POST /api/v1/venue-owner/venues/{id}/halls/`
  * POST: A'zolik roli `MANAGE_HALLS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `PATCH /api/v1/venue-owner/venues/{id}/halls/{hall_id}/`
  * A'zolik roli `MANAGE_HALLS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `GET /api/v1/venue-owner/venues/{id}/halls/{hall_id}/sessions/`
  * POST: A'zolik roli `MANAGE_SCHEDULE` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `POST /api/v1/venue-owner/venues/{id}/halls/{hall_id}/sessions/`
  * POST: A'zolik roli `MANAGE_SCHEDULE` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `PATCH /api/v1/venue-owner/venues/{id}/halls/{hall_id}/sessions/{session_id}/`
  * A'zolik roli `MANAGE_SCHEDULE` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
  * Bir zal smenalari vaqt bo'yicha kesishmaydi.
* `GET /api/v1/venue-owner/venues/{id}/images/`
  * POST: A'zolik roli `EDIT_PROFILE` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
  * Ko'pi bilan 20 ta rasm, har biri 5 MB gacha (JPG/PNG/WEBP)
* `POST /api/v1/venue-owner/venues/{id}/images/`
  * POST: A'zolik roli `EDIT_PROFILE` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
  * Ko'pi bilan 20 ta rasm, har biri 5 MB gacha (JPG/PNG/WEBP)
* `DELETE /api/v1/venue-owner/venues/{id}/images/{image_id}/`
  * A'zolik roli `EDIT_PROFILE` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
* `GET /api/v1/venue-owner/venues/{id}/members/`
  * A'zolik roli `MANAGE_MEMBERS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
  * POST: faqat faol VENUE_OWNER hisobi (telefon bo'yicha); topilmasa — bitta umumiy xato.
  * Throttle: venue_member_add
* `POST /api/v1/venue-owner/venues/{id}/members/`
  * A'zolik roli `MANAGE_MEMBERS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
  * POST: faqat faol VENUE_OWNER hisobi (telefon bo'yicha); topilmasa — bitta umumiy xato.
  * Throttle: venue_member_add
* `PATCH /api/v1/venue-owner/venues/{id}/members/{membership_id}/`
  * A'zolik roli `MANAGE_MEMBERS` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md).
  * Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi.
  * Oxirgi faol OWNER olib tashlanmaydi.
* `GET /api/v1/venues/`
  * Faqat admin tasdiqlagan (APPROVED) va faol to'yxonalar; mijozlar haqida ma'lumot qaytmaydi.
* `GET /api/v1/venues/search/`
  * Faqat admin tasdiqlagan (APPROVED) va faol to'yxonalar; mijozlar haqida ma'lumot qaytmaydi.
* `GET /api/v1/venues/{id}/`
  * Faqat admin tasdiqlagan (APPROVED) va faol to'yxonalar; mijozlar haqida ma'lumot qaytmaydi.
* `GET /api/v1/venues/{id}/availability/`
  * Faqat admin tasdiqlagan (APPROVED) va faol to'yxonalar; mijozlar haqida ma'lumot qaytmaydi.
* `POST /api/v1/venues/{target_id}/like/`
  * Faqat ommaga ochiq (faol, tasdiqlangan) to'yxona / faol studiya; boshqasi 404.
* `DELETE /api/v1/venues/{target_id}/like/`
  * Faqat ommaga ochiq (faol, tasdiqlangan) to'yxona / faol studiya; boshqasi 404.
* `GET /api/v1/venues/{target_id}/reviews/`
  * Faqat ommaga ochiq (faol, tasdiqlangan) to'yxona / faol studiya; boshqasi 404.
  * Yashirilgan sharhlar ko'rinmaydi.
* `PUT /api/v1/venues/{target_id}/reviews/mine/`
  * Faqat ommaga ochiq (faol, tasdiqlangan) to'yxona / faol studiya; boshqasi 404.
* `DELETE /api/v1/venues/{target_id}/reviews/mine/`
  * Faqat ommaga ochiq (faol, tasdiqlangan) to'yxona / faol studiya; boshqasi 404.

## Rejalashtirilgan (PLANNED — hali ishlamaydi)

> `apps/devcenter/planned.py`. Yuqoridagi jadval — faqat haqiqatda ishlaydigan endpointlar.
> CEREMONY_OWNER / CEREMONY_VIEWER — global rol emas, marosimga xos huquq.

| Bosqich | Metod | Yo'l | Tavsif | Kim | Shart |
|---|---|---|---|---|---|
| F | GET | `/api/v1/admin/ceremonies/` | Barcha marosimlar monitoringi | SUPER_ADMIN | — |
| F | GET | `/api/v1/admin/ceremonies/{id}/` | Marosim: egalar, takliflar, ko'ruvchilar, media, tarix | SUPER_ADMIN | Maxfiy maydonlar faqat audit qilinadigan alohida amal orqali |
