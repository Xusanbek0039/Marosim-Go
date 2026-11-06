# MarosimGo

Marosim xizmatlari uchun raqamli platforma. **1-bosqich:** Super Admin paneli — foydalanuvchilar, adminlar
(granular ruxsatlar bilan) va studiyalarni boshqarish.

| Qism | Texnologiya |
|---|---|
| `backend/` | Python 3.12 · Django 5.2 · DRF · SimpleJWT · drf-spectacular · SQLite (PostgreSQL'ga tayyor) |
| `frontend/` | Next.js 16 (App Router) · TypeScript · Tailwind v4 · shadcn/ui · Motion · TanStack Query · RHF + Zod |
| `docs/` | Arxitektura ([ARCHITECTURE.md](docs/ARCHITECTURE.md)) va OpenAPI sxema ([openapi.yaml](docs/openapi.yaml)) |

Biznes logika va REST API faqat Django'da. Next.js — faqat admin web panel; kelajakdagi mobil ilovalar
xuddi shu `/api/v1/` API'dan `Authorization: Bearer` bilan foydalanadi.

---

## Ishga tushirish (lokal)

Talablar: Python 3.12+, Node.js 20+ (LTS).

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   ·   macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt

cp ../.env.example .env          # so'ng sirlarni haqiqiy qiymatlar bilan to'ldiring:
python -c "import secrets;print(secrets.token_urlsafe(50))"                          # DJANGO_SECRET_KEY, JWT_SIGNING_KEY
python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"  # PINFL_ENCRYPTION_KEYS
# lokal http uchun .env ichida: AUTH_COOKIE_SECURE=false (yoki DJANGO_DEBUG=true)

python manage.py migrate
python manage.py createsuperuser   # yagona Super Admin yaratish yo'li (API orqali mumkin emas)
python manage.py seed_demo         # ixtiyoriy, faqat DJANGO_DEBUG=true bo'lganda: demo ma'lumotlar
python manage.py runserver 127.0.0.1:8000
```

### 2. Frontend

```bash
cd frontend
npm install
echo BACKEND_URL=http://127.0.0.1:8000 > .env.local
npm run dev            # http://localhost:3000
```

Brauzer faqat `http://localhost:3000` bilan ishlaydi: `/api/v1/*` va `/media/*` so'rovlarini Next.js
server tomonda Django'ga uzatadi, shuning uchun auth cookie'lar first-party bo'lib qoladi.

### Swagger

`http://127.0.0.1:8000/api/v1/docs/` — `DJANGO_DEBUG=true` bo'lsa ochiq, aks holda faqat Super Admin uchun.

---

## Tekshiruvlar

```bash
# backend
cd backend
python -m pytest                     # 68 test: RBAC matritsasi, JWT, JSHSHIR, upload, audit
ruff check . && ruff format --check .
python manage.py spectacular --validate --fail-on-warn --file ../docs/openapi.yaml

# frontend
cd frontend
npx tsc --noEmit
npm run lint
npm run build
```

---

## PostgreSQL'ga o'tish

Kod o'zgarmaydi — faqat `backend/.env`:

```env
DATABASE_URL=postgres://marosimgo:parol@localhost:5432/marosimgo
```

so'ng `pip install "psycopg[binary]"` va `python manage.py migrate`. Bir nechta worker ishlatilsa,
login bloklash va throttling uchun umumiy kesh ham kerak: `CACHE_URL=redis://localhost:6379/0`.

---

## Xavfsizlik — qisqacha

- **JWT:** access 10 daqiqa, refresh 7 kun; refresh har safar almashadi (rotation) va eskisi blacklist'ga tushadi.
  Ishlatilgan refresh qayta kelsa — o'g'irlik deb hisoblanib, foydalanuvchining **barcha** sessiyalari bekor qilinadi.
- **Web:** tokenlar faqat `HttpOnly` cookie'da (refresh — `SameSite=Strict`, faqat `/api/v1/auth/` yo'lida);
  localStorage'da hech qanday token yo'q. Cookie bilan kelgan har bir o'zgartiruvchi so'rov CSRF tekshiruvidan o'tadi.
- **Sessiyani bekor qilish:** nofaol qilish, o'chirish yoki parol o'zgarganda barcha tokenlar darhol yaroqsiz bo'ladi.
- **Brute-force:** IP bo'yicha throttle (5/min) + email bo'yicha 5 xatodan keyin 15 daqiqalik blok.
- **RBAC:** hamma tekshiruvlar serverda. `ADMIN` faqat Super Admin bergan ruxsatlar doirasida ishlaydi;
  adminlarni faqat Super Admin boshqaradi.
- **JSHSHIR:** Fernet bilan shifrlangan (kalit rotatsiyasi bilan), unikallik — HMAC orqali; API'da faqat
  `**********1234`. To'liq qiymat alohida endpoint orqali, ruxsat bilan va audit qilinib beriladi; loglardan kesiladi.
- **Yuklamalar:** ≤5 MB, faqat JPEG/PNG/WEBP, Pillow bilan to'liq dekodlanadi, EXIF o'chiriladi, WEBP'ga qayta kodlanadi.
- **Audit:** har bir yaratish/tahrirlash/nofaol qilish/o'chirish/kirish/JSHSHIR ko'rish o'zgarmas jurnalga yoziladi.
- **Headerlar:** CSP, `X-Frame-Options: DENY`, `nosniff`, API javoblari `no-store`.
