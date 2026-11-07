# backend/credentials/

Bu papkadagi **hamma narsa git'dan chetlatilgan** (faqat shu README kuzatiladi).

## Google OAuth client JSON

1. Google Cloud Console → **APIs & Services → Credentials** → sizning *Web application* OAuth client'ingiz → **Download JSON**.
2. Faylni shu nom bilan saqlang:

   ```
   backend/credentials/google_oauth_client.json
   ```

3. Tekshirish (maxfiy qiymatlar ekranga chiqmaydi):

   ```bash
   cd backend
   python manage.py google_oauth_check
   ```

Faylni chatga, issue'ga, screenshot'ga yoki git'ga **qo'ymang**. Agar tasodifan oshkor bo'lsa —
Cloud Console'da client secret'ni **Reset** qiling va yangi JSON'ni yuklab oling.

Production'da fayl o'rniga environment o'zgaruvchilaridan foydalanish mumkin:
`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`.
