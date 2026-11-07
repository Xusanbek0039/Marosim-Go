# Marosim egaligi, takliflar va shaxsiy media — arxitektura (V4.1)

Holat: **Phase A, B, C, D ✅ 2026-11-07**. E–G — tasdiq kutilmoqda. Media upload: [STORAGE_ARCHITECTURE.md §6](STORAGE_ARCHITECTURE.md).

## Phase A — mavjud loyiha auditi

| Soha | Mavjud holat | V4.1 uchun xulosa |
|---|---|---|
| Ma'lumotlar bazasi | Dev: SQLite (`backend/db.sqlite3`, git'da kuzatiladi); prod: `DATABASE_URL` (PostgreSQL). Barcha modellar `BaseModel` (UUID + vaqt). | Yangi jadvallar ham `BaseModel`; partial unique constraint'lar ikkala DB'da ishlaydi. |
| Marosim | `Ceremony` (studio, title, `event_type`, `event_date`, description, status, `drive_folder_id`, created_by). DRAFT…ARCHIVED. | Spec'dagi `ceremony_type`/`ceremony_date` = mavjud `event_type`/`event_date` (API buzilmasligi uchun nomlar saqlandi). `cover_image` qo'shildi, turlar kengaytirildi. |
| Studiya | `StudioMembership` OWNER / MANAGER / UPLOADER; ko'rish — har qanday faol a'zo, boshqarish — OWNER/MANAGER. | Studiya tomoni o'zgarmaydi; OWNER taklifi — faqat OWNER/MANAGER. |
| Egalik (v1) | `CeremonyParticipant`: studiya telefon orqali BRIDE/GROOM/OTHER taklif qiladi; INVITED → ACTIVE. Har bir ACTIVE ishtirokchi to'liq huquqqa ega, ko'ruvchi tushunchasi yo'q. | OWNER/VIEWER, ko'p ega, egalar tasdig'i, JSHSHIR orqali taklif, muddat — **yo'q edi**. Yangi model kiritildi, v1 qatorlari ko'chirildi. |
| Identifikatsiya | Telefon E.164 (`+998…`), `is_phone_verified` (OTP hali yo'q — admin qo'lda tasdiqlaydi). JSHSHIR: Fernet + HMAC blind index, ro'yxatdan o'tishda **foydalanuvchi o'zi kiritadi, tekshirilmaydi**. | JSHSHIR — faqat manzil (identifikator), hech qachon isbot emas. OWNER uchun tasdiqlangan telefon har doim shart. |
| Enumeration | v1 taklif javobi raqam ro'yxatdan o'tganini bildirmaydi; begona marosim — 404. | Saqlanadi; lookup endpointi yaratilmaydi (taklif yaratish o'zi javobsiz "lookup"). |
| Audit | `AuditLog` (o'zgarmas), `record()`. | Yangi harakatlar qo'shildi (pastda). |
| Google Drive | OAuth + shifrlangan refresh token, `drive.file`. Papka/media yo'q. `drive_folder_id` API orqali yozilmaydi. | Media kirishi Drive ID'ga emas, DB'dagi ACCEPTED huquqqa bog'lanadi (Phase D/E). |
| API kontrakt | Rollar DRF permission class'laridan (`accounts/access.py`), `access_notes`, `contracts/api_access_contract.json`, CI. | Yangi endpointlar avtomatik kiradi; rejalashtirilganlari `devcenter/planned.py` da alohida. |
| Frontend | `frontend/` — Super Admin paneli. `frontend-studio/`, `frontend-user/` — avvalgi bosqichda yaratilgan sodda ilovalar. | V4.1 talabi bo'yicha studiya/foydalanuvchi web'iga yangi ish qilinmaydi (mavjudlari tegmasdan qoladi). |

**Aniqlangan xavflar**
1. JSHSHIR o'z-o'zidan e'lon qilinadi → birov boshqaning JSHSHIRini oldinroq ro'yxatdan o'tkazib olishi mumkin.
   Yechim: JSHSHIR bo'yicha kelgan taklif ham faqat shu JSHSHIR'li **va** tasdiqlangan telefonli akkauntga; OWNER bo'lsa — egalar tasdig'i ham.
   Kelajak: MyID/OneID orqali `identity_verified` (alohida qaror).
2. OTP provayder yo'q → `is_phone_verified` faqat admin qo'lda. OWNER qabul qilish shunga bog'langan (`CEREMONY_OWNER_REQUIRE_VERIFIED_PHONE=true`, DEBUG'da ham).
3. v1'da studiya istalgan paytda yangi "egani" qo'sha oladi → V4.1'da egalar bor bo'lsa, yangi ega ularning tasdig'isiz kira olmaydi.
4. Dev DB git'da kuzatiladi (avto-commit) — tarkibida shifrlangan JSHSHIR/telefonlar bor; kalitlar `.env` da (git'da emas). Tavsiya: `db.sqlite3` ni kuzatuvdan chiqarish.

## Phase B — ma'lumotlar modeli

```
Studio 1─* Ceremony 1─* CeremonyInvitation ─?1 CeremonyOwnership 1─* CeremonyOwnershipApproval
                    │                       └?1 CeremonyViewerAccess
                    ├─* CeremonyOwnership (user, owner_type, status)
                    ├─* CeremonyViewerAccess (user, granted_by, status)
                    └─* CeremonyParticipant (v1, Phase C gacha)
```

| Model | Asosiy maydonlar | Cheklovlar |
|---|---|---|
| `CeremonyInvitation` | ceremony, invited_user (null — javob berilganda), identifier_type PHONE/PINFL, `recipient_identifier_encrypted` (Fernet), `recipient_identifier_hash` (HMAC, domain-separated), `recipient_hint` (maskalangan), requested_role VIEWER/OWNER, owner_type, invited_by, inviter_kind STUDIO/OWNER/SUPER_ADMIN, status PENDING/ACCEPTED/DECLINED/EXPIRED/REVOKED, expires_at, responded_at, revoked_at/by, send_count, last_sent_at, legacy_participant | Bitta oluvchiga marosimda bitta PENDING; OWNER ⇔ owner_type; VIEWER faqat egadan; ACCEPTED ⇒ invited_user |
| `CeremonyOwnership` | ceremony, user, owner_type BRIDE/GROOM/FAMILY_OWNER/OTHER_OWNER, invited_by, invitation, status PENDING/ACCEPTED/REJECTED/REVOKED, accepted_at, revoked_at/by | (ceremony,user) bo'yicha bitta ochiq (PENDING/ACCEPTED); bitta kelin, bitta kuyov; ACCEPTED ⇒ accepted_at |
| `CeremonyOwnershipApproval` | ownership, approver, decision PENDING/APPROVED/REJECTED, decided_at | (ownership, approver) unique |
| `CeremonyViewerAccess` | ceremony, user, granted_by, invitation, status ACCEPTED/REVOKED, accepted_at, revoked_at/by | (ceremony,user) bo'yicha bitta ACCEPTED |

`Ceremony`: `cover_image` (WEBP, metama'lumotsiz — `core.uploads.process_image`), `event_type` += ENGAGEMENT, SUNNAT, BESHIK, BIRTHDAY, ANNIVERSARY, OTHER.

### Egalik oqimi (Phase C'da endpointlarga ulanadi)

1. **Dastlabki egalar** — studiya (OWNER/MANAGER) yoki Super Admin OWNER taklifini yuboradi.
   Marosimda hali ACCEPTED ega bo'lmasa: oluvchi tizimga kirgan, identifikator mos, **telefon tasdiqlangan** → `CeremonyOwnership ACCEPTED`.
2. **Keyingi egalar** (ega yoki studiya taklif qiladi): oluvchi qabul qiladi → `CeremonyOwnership PENDING` + o'sha paytdagi har bir ACCEPTED ega uchun `CeremonyOwnershipApproval`.
   Taklif qilgan eganing ovozi avtomatik APPROVED. Hamma rozi → ACCEPTED; bittasi rad etsa → REJECTED.
   Tasdiq — *qabul qilgandan keyin*: egalar raqamni emas, aniq akkauntni (ismini) tasdiqlaydi.
3. **VIEWER** — faqat ACCEPTED ega yuboradi; qabul qilish → `CeremonyViewerAccess ACCEPTED`. Ko'ruvchi qayta ulasha olmaydi.
4. **Bekor qilish** — ega faqat o'zi bergan ko'ruvchini / o'zi yuborgan taklifni; o'zi chiqib keta oladi.
   Boshqa egani olib tashlash — faqat Super Admin (audit). Studiya faqat studiya yuborgan PENDING taklifni bekor qiladi.

### Ruxsat qatlami — `apps/ceremonies/ownership.py`

| Funksiya | Qoida |
|---|---|
| `role_in(user, ceremony)` | OWNER / VIEWER / None. Faqat faol USER roli, DRAFT bo'lmagan marosim, o'chirilmagan studiya, ACCEPTED qator. Har chaqiruvda DB'dan — bekor qilish darhol ta'sir qiladi. |
| `accessible_ceremonies`, `owned_ceremonies` | Queryset scoping (begona marosim → 404). |
| `can_view` | Marosim tafsiloti va barcha media endpointlari (thumbnail/preview/stream/download alohida chaqiradi). |
| `inviter_kind` / `can_invite` | VIEWER: faqat ega. OWNER: ega, studiya OWNER/MANAGER, Super Admin. |
| `invitations_for(user)` | PENDING, muddati o'tmagan, identifikator hash'i mos takliflar (faqat USER roli). |
| `response_refusal` | NOT_FOUND (begona/javob berilgan — 404), EXPIRED, PHONE_NOT_VERIFIED, ALREADY_HAS_ACCESS. Rad etish tasdiqsiz ham mumkin. |
| `approvers_for`, `approval_outcome`, `can_decide_owner_request` | Yuqoridagi 2-band. Endi ega bo'lmaganning ovozi hisoblanmaydi. |
| `can_revoke_invitation`, `can_revoke_viewer`, `can_revoke_ownership` | Yuqoridagi 4-band. |

DRF: `IsCeremonyMember`, `IsCeremonyOwner` (`permissions.py`) — USER rol darvozasi + object-level tekshiruv (defense in depth; scoping baribir `get_queryset` da).

### Maxfiylik
* Telefon / JSHSHIR taklifda faqat shifrlangan + HMAC; javoblarda faqat `recipient_hint`.
* Lookup endpointi **yo'q**: taklif yaratish akkaunt bor-yo'qligidan qat'i nazar bir xil javob qaytaradi (Phase C), throttle + `RECIPIENT_LOOKUP`/`*_INVITE` audit.
* Exact match faqat hash bo'yicha; ro'yxat/qidiruv yo'q.

### Audit harakatlari (qo'shildi)
`OWNER_INVITE`, `OWNER_ACCEPT`, `OWNER_REQUEST_APPROVE`, `OWNER_REJECT`, `VIEWER_INVITE`, `VIEWER_ACCEPT`,
`INVITATION_DECLINE`, `INVITATION_REVOKE`, `INVITATION_RESEND`, `ACCESS_REVOKE`, `RECIPIENT_LOOKUP`, `MEDIA_UPLOAD`.
Marosim yaratish — mavjud `CREATE` (target `ceremonies.Ceremony`).

### Migratsiyalar
* `ceremonies/0002_ownership_model` — sxema.
* `ceremonies/0003_backfill_ownership_from_participants` — v1 → yangi model (`backfill.py`, idempotent, qaytariladigan).
  INVITED→PENDING (yangi muddat), ACTIVE→ACCEPTED + ownership, DECLINED→DECLINED, REVOKED→REVOKED; OTHER→OTHER_OWNER.
  Mavjud ACTIVE ishtirokchilar egalikni saqlaydi (ular v1 qoidalari bilan qabul qilgan).
* `audit/0005_ceremony_ownership_actions` — faqat choices.

## Phase C — xavfsiz taklif tizimi (endpointlar)

| Metod | Yo'l | Kim | Izoh |
|---|---|---|---|
| POST | `/api/v1/ceremonies/{id}/owners/invite/` | STUDIO (OWNER/MANAGER), SUPER_ADMIN | `{identifier_type, identifier, owner_type}` |
| GET | `/api/v1/ceremonies/{id}/owners/` | studiya a'zosi, SUPER_ADMIN | egalik takliflari + natija; identifikator maskalangan |
| GET | `/api/v1/me/invitations/` · `/{id}/` | USER (oluvchi) | telefon tasdiqlanmagan bo'lsa marosim tafsilotlari yashiriladi |
| POST | `/api/v1/me/invitations/{id}/accept/` | USER (oluvchi) | `{status: ACCEPTED \| PENDING_APPROVAL, access_role, ceremony}` |
| POST | `/api/v1/me/invitations/{id}/decline/` | USER (oluvchi) | 204 |
| GET | `/api/v1/me/ceremonies/` · `/{id}/` | CEREMONY_OWNER / VIEWER | `access_role`, `my_role` (v1) |
| GET | `/api/v1/me/ceremonies/{id}/members/` | CEREMONY_OWNER | egalar + ko'ruvchilar (`can_revoke`) |
| GET/POST | `/api/v1/me/ceremonies/{id}/invitations/` | CEREMONY_OWNER | tarix / VIEWER yoki OWNER taklifi |
| POST | `/api/v1/me/ceremonies/{id}/invitations/{invitation_id}/revoke/` · `/resend/` | yuborgan ega | resend muddatni yangilaydi (max `CEREMONY_MAX_INVITATION_SENDS`) |
| POST | `/api/v1/me/ceremonies/{id}/viewers/{access_id}/revoke/` | huquqni bergan ega | boshqa ega — 403 |
| POST | `/api/v1/me/ceremonies/{id}/leave/` | ega / ko'ruvchi | egalik ketganda uning PENDING takliflari ham bekor bo'ladi |
| GET | `/api/v1/me/ceremonies/{id}/owner-requests/` | CEREMONY_OWNER | tasdiq kutayotgan egalar, ovozlar |
| POST | `…/owner-requests/{request_id}/approve/` · `/reject/` | so'rov ochilganda ACCEPTED bo'lgan ega | bitta rad — REJECTED |
| GET/POST/DELETE | `/api/v1/ceremonies/{id}/participants/…` | studiya | **deprecated** v1 alias (yangi modelga yozadi; raqam maskalangan) |

**Xato kodlari**: `phone_not_verified` (403), `identity_unverified` (403, JSHSHIR + tasdiqlovchi ega yo'q),
`invitation_expired` (410, holat EXPIRED saqlanadi), `conflict` (409, allaqachon a'zo / slot band),
begona yoki javob berilgan taklif — 404 (mavjudligi tasdiqlanmaydi).

**Qoidalar (amalda)**
* Kuyovni studiya oldindan taklif qilgan bo'lsa ham, kelin qabul qilib bo'lgach kuyov egaligi kelinning tasdig'ini kutadi
  (tasdiq — qabul qilish paytidagi egalar). Egalar qaysi akkaunt (ism) da'vo qilganini ko'rib tasdiqlaydi.
* JSHSHIR orqali birinchi egalik taklifi rad etiladi (400) va qabul qilishda ham tekshiriladi.
* Har bir holat o'zgarishi shartli `UPDATE … WHERE status=…` — parallel qabul/ovoz faqat bir marta o'tadi.
* Throttle: `ceremony_invite` (taklif yaratish/qayta yuborish), `invitation_respond` (qabul/rad).
* `manage.py expire_ceremony_invitations` — muddati o'tganlarni EXPIRED qiladi (cron); o'qishda ham hisobga olinadi.
* SMS provayder yo'q: taklif oluvchining "Mening takliflarim" ro'yxatida paydo bo'ladi; resend — muddatni yangilash.

### Qabul qilingan qarorlar (foydalanuvchi standartlarni tasdiqladi)
1. Studiya ACCEPTED egani olib tashlay olmaydi (403); faqat Super Admin (`DELETE …/participants/{id}/`, audit).
2. Ega ketsa/olib tashlansa, u bergan VIEWER huquqlari saqlanadi; uning javob kutilayotgan takliflari bekor bo'ladi.
3. v1 endpointlari yangi modelga o'tdi; `/participants/` — deprecated alias. `CeremonyParticipant` endi yozilmaydi
   (`0004_backfill_late_participants` oraliqdagi qatorlarni ko'chirdi).
4. MyID/OneID — alohida bosqich (ochiq).

## Phase E — media ko'rish va muddatli ulashish (2026-11-07) ✅

**Oqim:** studiya montaj qilingan video/rasmni `frontend-studio` → marosim sahifasidan yuklaydi (baytlar brauzerdan to'g'ridan-to'g'ri Google Drive'ga, 8 MB bo'laklar, uzilsa davom etadi) → server Drive'dan tekshiradi (READY) → marosim egasi `frontend-user` da ko'radi → ega 5 kishigacha telefon yoki JSHSHIR orqali taklif yuboradi → odam qabul qilgach, tanlangan muddat davomida faqat ko'radi.

**Drive papkasi:** `MarosimGo / Studio_<studiya nomi> / Mijoz_****<JSHSHIR oxirgi 4 raqami>_<marosim id 6 belgi> / {Videos, Photos} / <media id>.<ext>`. Ega hali ma'lum bo'lmasa — `Mijoz_<id6>`. Kalitlar ID asosida (nom keyin o'zgarsa daraxt bo'linmaydi); mavjud papkalar qayta nomlanmaydi.

**Endpointlar** (`/api/v1/me/ceremonies/{ceremony_id}/media/`)

| Endpoint | OWNER | VIEWER |
|---|:-:|:-:|
| `GET …/media/` — READY fayllar (Drive id, asl nom, yuklovchi yo'q) | ✓ | ✓ |
| `GET …/{media_id}/thumbnail/?size=240\|480\|960` — Drive preview, server keshi 10 daqiqa | ✓ | ✓ |
| `GET …/{media_id}/stream/` — inline, bitta HTTP Range (video seek) | ✓ | ✓ |
| `GET …/{media_id}/download/` — attachment, audit `MEDIA_DOWNLOAD` | ✓ | 403 |

Huquq har so'rovda DB'dan qayta o'qiladi: muddati tugagan yoki bekor qilingan ruxsat darhol 404.

**Muddatli ulashish:** VIEWER taklifida `access_duration` majburiy (`24H`, `3D`, `1W`, `1M`=30 kun); muddat qabul qilingan paytdan. `CeremonyViewerAccess.expires_at`; barcha tekshiruvlar `ownership.live_viewers()` orqali (`expires_at` bilan solishtiriladi). Muddati o'tgan qator qayta taklif qabul qilinganda `EXPIRED` bo'ladi. Eski (muddatsiz) qatorlar — `expires_at = null`.

**Chegara:** har bir ega bir vaqtda ko'pi bilan `CEREMONY_MAX_VIEWERS_PER_OWNER = 5` (faol ruxsatlar + javob kutilayotgan takliflar; kelin va kuyov alohida). Hisoblash marosim qatori `SELECT … FOR UPDATE` bilan qulflangan holda.

**"Faqat ko'rish" chegarasi:** ko'ruvchiga yuklab olish endpointi va tugmasi yo'q, `controlsList="nodownload"`, kontekst menyu o'chirilgan. Ekran yozib olishni texnik jihatdan to'liq to'sib bo'lmaydi.

**Google CORS (jonli topilgan):** brauzer PUT'ining yakuniy (200) javobida CORS sarlavhasi faqat sessiya o'sha `Origin` bilan ochilgan bo'lsa qaytadi. Server `Origin` ni faqat `MEDIA_UPLOAD_BROWSER_ORIGINS` ro'yxatidan (dev: `http://localhost:3001`) Google'ga uzatadi. **Production'da studiya domenini shu o'zgaruvchiga qo'shish shart.**

**Tekshiruv:** 1251 test (SQLite + PostgreSQL). Haqiqiy Google Drive bilan jonli sinov: yuklash → READY → `Studio_…/Mijoz_****2345_…/Photos` → ega Range oqimi va yuklab olish → begona 404 → 24 soatlik ulashish → mehmon ko'radi, yuklab ololmaydi → thumbnail. Sinov ma'lumotlari va Drive papkasi o'chirildi.
