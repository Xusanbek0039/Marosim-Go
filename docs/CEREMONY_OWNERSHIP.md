# Marosim egaligi, takliflar va shaxsiy media — arxitektura (V4.1)

Holat: **Phase A (audit) + Phase B (modellar, migratsiyalar, ruxsatlar) ✅ 2026-11-07**. C–G — tasdiq kutilmoqda.

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

### Phase C uchun ochiq qarorlar
1. v1 endpointlari (`/ceremonies/{id}/participants/`, `/me/invitations/`, `/me/ceremonies/`) yangi modelga o'tkaziladi;
   v1 `participants` — deprecated alias. Phase B'dan keyin yaratilgan v1 qatorlari 0003'ni qayta ishga tushiruvchi migratsiya bilan ko'chiriladi.
2. Studiya ACCEPTED egani olib tashlay oladimi? Hozirgi dizayn: **yo'q** (faqat Super Admin).
3. Ega olib tashlansa, u bergan VIEWER huquqlari saqlanadimi? Hozirgi dizayn: saqlanadi (Super Admin / ko'ruvchi o'zi bekor qila oladi).
4. MyID/OneID orqali shaxsni tasdiqlash — alohida bosqich.
