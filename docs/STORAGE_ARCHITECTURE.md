# Storage arxitekturasi

Holat: **Phase A (OAuth) va media upload (papkalar + resumable upload, V4.1-D) — tayyor.** Dashboard — rejada.

## 1. Modul

```
apps/storage/
  client_config.py   OAuth client JSON / env'dan xavfsiz o'qish (sirni hech qachon chiqarmaydi)
  vault.py           Fernet (MultiFernet) — refresh token, PKCE verifier; alohida kalit
  google.py          GoogleGateway — Google bilan gaplashadigan YAGONA joy (testlarda fake)
  services.py        connect / callback / refresh / test / disconnect logikasi
  views.py, urls.py  /api/v1/admin/storage/google/*
  models.py          StorageConnection · StorageCredential · OAuthState
```

`apps.storage` → `apps.accounts` (rol), `apps.audit` (jurnal). Teskari bog'lanish yo'q.
Kelajakdagi `media_library` faqat `services.access_credentials()` / provider interfeysini chaqiradi.

## 2. Ma'lumotlar

| Model | Maqsad | Maxfiy? |
|---|---|---|
| `StorageConnection` | provider (unique), account_email, root_folder_id/name, status, scopes, last_checked/success_at, last_error_code, connected_by/at | yo'q — API'da ko'rsatiladi |
| `StorageCredential` | `refresh_token_encrypted` (1:1) | ha — hech qachon serialize qilinmaydi, `repr` ham yashiradi |
| `OAuthState` | `state_hash`, `binding_hash`, `code_verifier_encrypted`, initiated_by, expires_at, used_at | faqat hash/shifr saqlanadi |

Statuslar: `DISCONNECTED` → `CONNECTED` → (`RECONNECT_REQUIRED` | `ERROR`).

## 3. OAuth oqimi

```
Panel (Super Admin JWT)                Django                          Google
  GET /connect/ ───────────────▶ state, binding, PKCE verifier yaratadi
                                 OAuthState(hash'lar) saqlaydi
  ◀── {authorization_url} + Set-Cookie mg_oauth_bind (httpOnly, Lax, 10 daq)
  window.location = Google URL ───────────────────────────────────▶ consent
                                                                    │
  brauzer ◀──────────── 302 /callback/?state&code ──────────────────┘
  GET /callback/ (JWT YO'Q) ───▶ 1. state: mavjud · ishlatilmagan → darhol "used"
                                 2. muddati o'tmagan (10 daq)
                                 3. cookie hash == binding_hash (constant-time)
                                 4. boshlovchi hali faol SUPER_ADMIN
                                 5. error=access_denied emas
                                 6. code + PKCE verifier → token (server→Google)
                                 7. refresh_token bor, drive.file berilgan
                                 8. refresh token → vault → StorageCredential
  ◀── 302 PANEL_URL/storage?google=connected | error&reason=<kod>
```

Nega callback JWT talab qilmaydi: uni Google brauzer redirect'i bilan chaqiradi. Uning o'rniga
bir martalik **state** (CSRF), **binding cookie** (aynan shu brauzer — login-CSRF / begona akkauntni
ulab qo'yish hujumiga qarshi) va **PKCE** (o'g'irlangan `code` foydasiz) ishlatiladi.

## 4. Tokenlar

* Refresh token: faqat serverda, `GOOGLE_TOKEN_ENCRYPTION_KEY` bilan shifrlangan; API, panel, log va
  audit'ga chiqmaydi. Access token faqat xotirada (har chaqiruvda refresh).
* `invalid_grant` (bekor qilingan / Testing rejimida 7 kun) → `RECONNECT_REQUIRED` + panelda ogohlantirish.
* Disconnect: Google'da revoke (best effort) + lokal o'chirish.
* Loglar: `django.server` access log'idagi `?code=&state=` redaktsiya qilinadi; RequestLog query string saqlamaydi.

## 5. `drive.file` scope tahlili (Picker va mavjud papka)

`drive.file` — **non-sensitive**, eng tor Drive scope: ilova faqat **o'zi yaratgan** yoki egasi
**Google Picker orqali tanlagan** fayl/papkalarga kira oladi.

| Ssenariy | `drive.file` bilan | Izoh |
|---|---|---|
| Ilova o'zi "MarosimGo" root papka yaratadi | ✅ to'liq | Ichida Studio/Ceremony papkalar, upload — hammasi ishlaydi |
| Oldindan mavjud papka **Picker orqali** tanlanadi | ✅ (Google hujjatlariga ko'ra) papkaga kirish beriladi; ichida yangi papka/fayl yaratish mumkin | Papka ichidagi *eski* fayllar ko'rinmaydi (bizga kerak emas). **Jonli tasdiq kutilmoqda**: Phase B'da Picker bilan tanlab, `storage_selftest --parent <id>` |
| Folder ID **qo'lda** kiritiladi (Picker'siz) | ❌ `404 notFound` | Ilova bu papkani "ko'rmagan". Faqat `drive` (restricted) scope hal qiladi — **tavsiya etilmaydi** |

Phase B uchun tavsiya: **Picker** (asosiy) yoki **"MarosimGo papkasini yaratish"** tugmasi (eng sodda).
Qo'lda ID kiritish faqat ilova oldin yaratgan/Picker'da tanlangan papkalar uchun ishlaydi —
aks holda aniq "ruxsat yo'q, Picker'dan tanlang" xabari ko'rsatiladi. Kengroq scope'ga avtomatik o'tilmaydi.

Picker dizayni (Phase B): Picker brauzerda ishlaydi va qisqa muddatli **access token** talab qiladi
(refresh token emas). Variant: faqat SUPER_ADMIN uchun `drive.file`-li 1 soatlik access token beruvchi
alohida endpoint + Picker `appId` = Cloud project number (`status` javobidagi `picker.app_id`) +
browser API key (HTTP referrer bilan cheklangan). Tanlangan papka ID'si serverda `files.get`
(`mimeType`, `capabilities.canAddChildren`) bilan tekshiriladi va `StorageConnection.root_folder_id`
ga yoziladi. Bu token-ni-brauzerga-berish qarori Phase B boshida tasdiqlanadi.

Jonli tekshiruv: `python manage.py storage_selftest [--parent <picked_folder_id>]` — test papka,
`Videos/` subpapka va kichik fayl yaratadi, o'qiydi va **faqat ularni** o'chiradi.

## 6. Media upload (V4.1 Phase D) — to'g'ridan-to'g'ri Drive resumable sessiya

**Qaror**: baytlar backend orqali o'tmaydi. Vaqtinchalik disk, Celery/Redis kerak emas (yangi infratuzilma yo'q).

```
Mobil ilova (studiya)            Django                                  Google Drive
 POST …/media/uploads/ ─────▶ ruxsat · tur/hajm · arxiv emas · limit
  {filename, mime_type,        CeremonyMedia(UPLOADING) yaratiladi
   size_bytes, md5?}           papka: MarosimGo/Studio_<id>/Ceremony_<id>/{Photos,Videos}
                               (DriveFolder kesh, unique key — idempotent)
                               resumable sessiya ochadi ───────────────▶ (nom = <media_id>.<ext>,
                                                                         appProperties.mg_media = <id>,
                                                                         X-Upload-Content-Length)
  ◀── {upload_url, chunk_size_multiple=256 KiB}  (session URI shifrlangan holda saqlanadi)
 PUT upload_url (bo'laklab, Content-Range) ─────────────────────────────▶ (Authorization shart emas;
                                                                         URI faqat shu bitta fayl uchun)
 GET …/uploads/{id}/ ─────────▶ PUT bytes */N → Google'dan jonli progress (uzilsa davom ettirish)
 POST …/uploads/{id}/complete/ ▶ fayl id'si SESSIYANING O'ZIDAN olinadi (mijozdan emas)
                               files.get qayta o'qiladi va tekshiriladi:
                               trashed emas · parent = ceremony papkasi · mg_media = id ·
                               size = e'lon qilingan · mimeType · (md5 berilgan bo'lsa)
                               mos → READY (CAS, bir marta, audit MEDIA_UPLOAD)
                               mos emas → Drive fayli o'chiriladi, FAILED (audit MEDIA_UPLOAD_FAILED)
```

| Mavzu | Yechim |
|---|---|
| OAuth token | hech qachon mijozga berilmaydi; faqat bitta faylga yaroqli session URI |
| Session URI | `vault` (Fernet) bilan shifrlangan; faqat yuklashni boshlagan foydalanuvchiga va UPLOADING holatida qaytadi |
| Drive ID'lar | API javoblarida yo'q; fayl hech qachon public qilinmaydi; kirish faqat `CeremonyMedia` qatori orqali (Phase E) |
| Fayl nomlari | Drive'da faqat `<uuid>.<ext>` va `Studio_<uuid>`/`Ceremony_<uuid>` — ism/telefon yo'q |
| Papka idempotentligi | `DriveFolder(account_email, key)` unique; kesh yo'qolsa mavjud papka topiladi; poygada yutqazgan dublikat o'chiriladi; papka Drive'da o'chirilgan bo'lsa (`not_found`) bir marta qayta quriladi |
| Akkaunt almashsa | `DriveFolder` akkauntga bog'langan — eski ID'lar qayta ishlatilmaydi |
| Limitlar | `MEDIA_PHOTO_MAX_MB` (50), `MEDIA_VIDEO_MAX_MB` (20480), `MEDIA_MAX_ACTIVE_UPLOADS` (50/marosim), throttle `media_upload` |
| Muddat | sessiya TTL 144 soat (`MEDIA_SESSION_TTL_HOURS`); `manage.py expire_media_uploads` (cron) |
| Drive ulanmagan / kvota | 503 `storage_unavailable` (sabab kodi bilan), qator FAILED |

**Cheklov (ochiq)**: server faylni yuklab olib kontentini "sniff" qilmaydi — tur e'lon qilingan qiymat va Drive
metadatasi bilan tekshiriladi. Phase E'da media faqat avtorizatsiyalangan proksi orqali, qat'iy `Content-Type`
va `X-Content-Type-Options: nosniff` bilan beriladi. Drive — CDN emas: uzoq muddatda S3-compatible + CDN rejasi.
Picker orqali mavjud papkani root qilish — hali ochiq (hozir ilova `MarosimGo` papkasini o'zi yaratadi).
