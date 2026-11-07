# Google Drive ulash — sozlash qo'llanmasi (Phase A)

Drive turi: **shaxsiy Gmail / My Drive**. Ulanish — platforma egasining Google akkaunti orqali
OAuth 2.0 *Authorization Code Flow* (offline access + PKCE). Service account ishlatilmaydi.
Studiya va foydalanuvchilar Google'ga ulanmaydi — ular faqat MarosimGo JWT bilan API'ga murojaat qiladi.

## 1. Google Cloud Console (bir marta)

| Qadam | Qayerda | Qiymat |
|---|---|---|
| Loyiha | console.cloud.google.com | `marosimgo` |
| Drive API | APIs & Services → Library → **Google Drive API** → Enable | |
| OAuth consent screen | APIs & Services → OAuth consent screen | User type: **External**, app name: MarosimGo |
| Scopes | consent screen → Data access | `openid`, `.../auth/userinfo.email`, `.../auth/drive.file` |
| Test users | consent screen → Audience | o'zingizning Gmail manzilingiz |
| OAuth client | Credentials → Create credentials → OAuth client ID | Type: **Web application** |
| Redirect URI | client → Authorized redirect URIs | `http://localhost:8000/api/v1/admin/storage/google/callback/` |

> **Testing holati va 7 kun.** Consent screen *Testing* holatida bo'lsa, Google refresh tokenni
> **7 kundan keyin** bekor qiladi. Panelda holat `RECONNECT_REQUIRED` bo'ladi va "Qayta ulash"
> tugmasi chiqadi. Doimiy ishlash uchun consent screen'ni **In production** holatiga o'tkazing.
> `drive.file` + `email` — *non-sensitive* scope'lar, shuning uchun Google'ning to'liq tekshiruvi
> (security assessment) talab qilinmaydi; faqat brend ma'lumotlari tekshirilishi mumkin.

## 2. Serverga credentials joylashtirish

1. Client sahifasida **Download JSON** → faylni `backend/credentials/google_oauth_client.json` sifatida saqlang
   (papka git'dan chetlatilgan, qarang `backend/credentials/README.md`).
2. `backend/.env` ga shifrlash kalitini qo'shing:

   ```bash
   python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"
   # chiqqan qiymatni .env ga: GOOGLE_TOKEN_ENCRYPTION_KEY=<qiymat>
   ```

3. Tekshiring (sirlar ekranga chiqmaydi):

   ```bash
   cd backend
   python manage.py migrate
   python manage.py google_oauth_check     # oxirida "Ready" chiqishi kerak
   ```

## 3. Environment o'zgaruvchilari

| O'zgaruvchi | Majburiy | Nima uchun / qayerdan |
|---|---|---|
| `GOOGLE_TOKEN_ENCRYPTION_KEY` | ha | Refresh tokenni shifrlaydi. Yuqoridagi Fernet buyrug'i bilan yarating. Vergul bilan bir nechta kalit = rotatsiya (birinchisi shifrlaydi). |
| `GOOGLE_OAUTH_CLIENT_FILE` | yo'q | JSON fayl yo'li (standart: `backend/credentials/google_oauth_client.json`). |
| `GOOGLE_OAUTH_CLIENT_ID` | yo'q* | JSON o'rniga (production secret manager). Cloud Console → Credentials. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | yo'q* | Yuqoridagi bilan birga. Hech qachon kodga yoki git'ga yozilmaydi. |
| `GOOGLE_OAUTH_REDIRECT_URI` | yo'q | Standart: `http://localhost:8000/api/v1/admin/storage/google/callback/`. Cloud'dagi ro'yxat bilan **aynan** bir xil bo'lishi shart. |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | yo'q | Boshlang'ich root papka ID (Phase B'da panel orqali tanlanadi). |
| `PANEL_URL` | yo'q | Callback'dan keyin brauzer qaytadigan panel manzili (standart `http://localhost:3000`). |

\* JSON fayl bo'lmasa, `CLIENT_ID` + `CLIENT_SECRET` ikkalasi kerak.

## 4. Akkauntni ulash

1. Backend va panelni ishga tushiring; panelni **aynan `http://localhost:3000`** orqali oching
   (`127.0.0.1` emas — callback `localhost` da, bog'lovchi cookie host'ga bog'langan).
2. Super Admin sifatida kiring → chap menyu **Google Drive** → **Connect Google Drive**.
3. Google'da akkauntingizni tanlang. "Google hasn't verified this app" chiqsa → *Continue*
   (Testing rejimida bu odatiy).
4. Ruxsatlar oynasida **Drive katagini belgilang** ("See, edit, create and delete only the specific
   Google Drive files you use with this app") → *Continue*.
5. Panelga qaytasiz: holat **Ulangan**, akkaunt emaili ko'rinadi. **Test Connection** — tokenni
   yangilab Drive'dan javob olinadi (xotira hajmi ham ko'rsatiladi).
6. Ixtiyoriy jonli tekshiruv (faqat o'zi yaratgan test papka/faylni yaratadi va o'chiradi):

   ```bash
   python manage.py storage_selftest
   ```

## 5. Muammolar

| Panel xabari / kod | Sabab | Yechim |
|---|---|---|
| `redirect_uri_mismatch` | Cloud'dagi URI farq qiladi | Oxiridagi `/` gacha bir xil qiling |
| `binding_mismatch` | Boshqa brauzer yoki `127.0.0.1` | `http://localhost:3000` dan qayta boshlang |
| `scope_denied` | Drive katagi belgilanmagan | Qayta ulab, katakni belgilang |
| `no_refresh_token` | Google refresh token bermadi | myaccount.google.com/permissions → MarosimGo → Remove access → qayta ulang |
| `RECONNECT_REQUIRED` / `invalid_grant` | Token bekor qilingan yoki 7 kun o'tgan | "Qayta ulash" |
| `drive_api_disabled` | Drive API yoqilmagan | Cloud Console → Library → Enable |
| `encryption_key_missing` | `.env` da kalit yo'q | 2-bo'lim |
