# Deploy — cPanel, bitta backend, beshta domen

Faqat `backend/` papkasi deploy qilinadi. Bitta Django ilovasi (Passenger) barcha domenlarga javob beradi,
Node.js kerak emas:

| Domen | Nima ochiladi | Build papkasi |
|---|---|---|
| `marosimgo.uz`, `www.marosimgo.uz` | Loyiha haqidagi landing sahifa | `backend/landing/` (qo'lda yozilgan, build kerak emas) |
| `api.marosimgo.uz` | Faqat API (`/api/v1/`) — mobil ilovalar | — |
| `superadmin.marosimgo.uz` | Super Admin panel + `/api/v1/` | `backend/panel/` |
| `admin.marosimgo.uz` | Admin panel + `/api/v1/` | `backend/panel-admin/` |
| `studio.marosimgo.uz` | Studiya kabineti + `/api/v1/` | `backend/panel-studio/` |

Domen qaysi panelni olishi uning birinchi qismidan aniqlanadi (`studio.` → studiya). Har bir panel API'ni
o'z domenida chaqiradi, shuning uchun cookie'lar first-party bo'lib qoladi va CORS kerak bo'lmaydi.

## 1. Panellarni build qilish (o'z kompyuteringizda)

```bash
cd frontend         && npm run build:panel        # → backend/panel/
cd frontend         && npm run build:panel:admin  # → backend/panel-admin/
cd frontend-studio  && npm run build:panel        # → backend/panel-studio/
```

Build fayllari gitga commit qilinadi, server ularni `git pull` bilan oladi.

## 2. cPanel sozlamalari

1. **Domains:** asosiy domen `marosimgo.uz` va `api`, `superadmin`, `admin`, `studio` subdomenlari.
2. **Setup Python App:** Application root = `backend/`, startup file = `passenger_wsgi.py`,
   entry point = `application`, Application URL = `api.marosimgo.uz`.
3. Qolgan domenlar (`marosimgo.uz`, `superadmin`, `admin`, `studio`) ham **shu bitta** ilovaga ulanishi kerak. cPanel bitta ilovaga bitta URL
   bersa, `api` subdomenining document root'idagi `.htaccess` faylidan Passenger qatorlarini
   (`PassengerAppRoot`, `PassengerBaseURI`, `PassengerPython` va boshqalar) ularning document root'laridagi
   `.htaccess` ga nusxalang. Ikkinchi Python ilova yaratmang.
4. **SSL/TLS Status → Run AutoSSL:** barcha domenlarga (`www` bilan) sertifikat chiqaring.
5. `backend/.env` faylini `backend/.env.production.example` asosida to'ldiring.

> **`.env` formati:** `KALIT=qiymat`, `=` atrofida va vergullardan keyin bo'sh joy qoldirmang.
> `DJANGO_ALLOWED_HOSTS = a, b` ko'rinishidagi qatorni Django **e'tiborsiz qoldiradi** ("Invalid line"),
> natijada har bir so'rov 400 xato beradi.

```dotenv
DJANGO_ALLOWED_HOSTS=marosimgo.uz,www.marosimgo.uz,api.marosimgo.uz,superadmin.marosimgo.uz,admin.marosimgo.uz,studio.marosimgo.uz
CSRF_TRUSTED_ORIGINS=https://superadmin.marosimgo.uz,https://admin.marosimgo.uz,https://studio.marosimgo.uz
CORS_ALLOWED_ORIGINS=https://superadmin.marosimgo.uz,https://admin.marosimgo.uz,https://studio.marosimgo.uz
MEDIA_UPLOAD_BROWSER_ORIGINS=https://studio.marosimgo.uz
PANEL_URL=https://superadmin.marosimgo.uz
```

## 3. Har deploy'da (cPanel Terminal, virtualenv ichida)

```bash
cd ~/marosimgo && git pull
cd backend
pip install -r requirements.txt
python manage.py migrate          # umumiy cache jadvalini ham yaratadi
python manage.py check --deploy
touch tmp/restart.txt             # yoki "Setup Python App" → Restart
```

## 4. Tekshirish

```bash
curl https://api.marosimgo.uz/api/v1/health/ready/
# {"status":"ok","checks":{"database":"ok","cache":"ok"}}
```

Super Admin → Monitoring sahifasida "Healthy" yashil bo'lishi kerak. Holat sariq ("Degraded") bo'lsa:

- `checks.cache = "fail"` — `.env` dagi `CACHE_URL` ishlamayotgan Redis'ga qarayapti. Uni o'chiring
  (bazadagi cache ishlatiladi) yoki Redis'ni ishga tushiring.
- Cache "ok" bo'lsa, oxirgi 15 daqiqada so'rovlarning 5% dan ko'pi 5xx xato bergan yoki p95 > 2 s.
  Monitoring → Errors bo'limida qaysi endpoint xato berayotganini ko'ring.

## Ko'p foydalanuvchi uchun

- **Cache:** login bloklash va so'rovlar cheklovi (rate limit) barcha worker jarayonlar uchun umumiy
  bo'lishi kerak. Production'da standart cache — asosiy bazadagi jadval (`migrate` yaratadi). Redis
  bo'lsa: `CACHE_URL=redis://127.0.0.1:6379/0`.
- **Baza:** SQLite WAL rejimida ishlaydi va yozuvchilar 20 soniyagacha navbat kutadi. Shunga qaramay,
  bir vaqtda minglab yozuv bo'lsa PostgreSQL yoki MySQL'ga o'ting (`DATABASE_URL=postgres://...`).
  Ulanishlar qayta ishlatiladi (`DB_CONN_MAX_AGE`, standart 60 s).
- **Passenger:** cPanel'da bir nechta jarayon ishlashiga ruxsat bering ("Setup Python App" yoki hosting
  tarifi orqali).
