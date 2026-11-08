"""Studio media upload to Google Drive (Phase D) — direct-to-Drive resumable sessions.

1. ``start_upload``: validate, create the row, resolve the folder
   (``MarosimGo/Studio_<name>/Mijoz_****<last4>_<id6>/{Photos,Videos}``), open a Drive resumable session for exactly
   this file (declared type + length, ``appProperties.mg_media = <row id>``) and hand the session URI to
   the uploader. No OAuth token ever leaves the server; no bytes pass through it.
2. The client PUTs the bytes (in chunks, resumable) straight to Google.
3. ``complete``: the server asks *the session itself* for the created file (the client cannot point it
   at another file), re-reads it from Drive and verifies folder, ``mg_media`` marker, size, type and the
   optional MD5. Mismatch → the Drive file is deleted and the row FAILED. Success → READY (once: CAS).
"""

import logging
import re
import unicodedata
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status as http
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.accounts.models import Role
from apps.audit.services import AuditAction, record
from apps.ceremonies import services as ceremony_services
from apps.ceremonies.models import AccessRole, Ceremony, CeremonyStatus, IdentifierType, OwnershipStatus
from apps.core.exceptions import Conflict
from apps.storage import folders, vault
from apps.storage.google import GoogleError
from apps.storage.services import StorageError, access_credentials, gateway

from .models import MIME_TYPES, CeremonyMedia, MediaKind, MediaStatus, kind_of

logger = logging.getLogger("apps.media")

#: Google requires every chunk except the last to be a multiple of 256 KiB.
CHUNK_MULTIPLE = 256 * 1024
FOLDER_NAMES = {MediaKind.PHOTO: "Photos", MediaKind.VIDEO: "Videos"}


class StorageUnavailable(APIException):
    status_code = http.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Media ombori (Google Drive) hozir mavjud emas. Keyinroq urinib ko'ring."
    default_code = "storage_unavailable"


class UploadRejected(APIException):
    status_code = http.HTTP_409_CONFLICT
    default_detail = "Yuklangan fayl tekshiruvdan o'tmadi va o'chirildi."
    default_code = "upload_rejected"


class UploadIncomplete(APIException):
    status_code = http.HTTP_409_CONFLICT
    default_detail = "Fayl hali to'liq yuklanmagan."
    default_code = "upload_incomplete"


def _storage_error(exc: StorageError | GoogleError) -> StorageUnavailable:
    logger.warning("media storage error: %s", exc.code)
    return StorageUnavailable(f"{StorageUnavailable.default_detail} ({exc.code})")


# ------------------------------------------------------------------ rules
def can_upload(user, ceremony: Ceremony) -> bool:
    """Any active member of the ceremony's studio (OWNER / MANAGER / UPLOADER) or a Super Admin."""
    if user.role == Role.SUPER_ADMIN:
        return True
    return user.role == Role.STUDIO and ceremony.studio_id in ceremony_services.studio_ids(user)


def can_cancel(user, media: CeremonyMedia) -> bool:
    return media.uploaded_by_id == user.pk or ceremony_services.can_manage(user, media.ceremony)


def clean_filename(raw: str) -> str:
    name = re.split(r"[\\/]", raw or "")[-1]
    name = "".join(ch for ch in unicodedata.normalize("NFC", name) if unicodedata.category(ch)[0] != "C")
    name = name.strip(" .") or "fayl"
    return name[:200]


def _limits() -> dict:
    return settings.MEDIA_UPLOAD


# ----------------------------------------------------------------- folders
#: Characters Drive (or a later sync to disk) handles badly in folder names.
_UNSAFE_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def _drive_name(text: str, limit: int = 80) -> str:
    return " ".join(_UNSAFE_NAME.sub(" ", text or "").split())[:limit].strip() or "-"


def _client_last4(ceremony: Ceremony) -> str:
    """Last 4 JSHSHIR digits of the ceremony's client, or "" when not known yet.

    Only ever the last four digits (the user's choice, 2026-11-07): the full JSHSHIR must never be
    written into Drive, where folder names are plain text for anyone the folder reaches.
    """
    owners = ceremony.ownerships.filter(status=OwnershipStatus.ACCEPTED).select_related("user").order_by("accepted_at")
    for row in owners:
        if row.user.pinfl_last4:
            return row.user.pinfl_last4
    invitation = (
        ceremony.invitations.filter(requested_role=AccessRole.OWNER, identifier_type=IdentifierType.PINFL)
        .order_by("created_at")
        .first()
    )
    match = re.search(r"(\d{4})$", invitation.recipient_hint) if invitation else None
    return match.group(1) if match else ""


def _segments(ceremony: Ceremony, kind: str | None = None) -> list[tuple[str, str]]:
    """``MarosimGo / Studio_<name> / Mijoz_****<last4>_<id6> / {Photos, Videos}``.

    Keys stay id-based, so renaming a studio or learning the JSHSHIR later never forks the tree;
    the readable name is set when a folder is first created.
    """
    sid, cid = ceremony.studio_id, ceremony.pk
    last4 = _client_last4(ceremony)
    client = f"Mijoz_****{last4}_{cid.hex[:6]}" if last4 else f"Mijoz_{cid.hex[:6]}"
    segs = [
        (f"studio:{sid}", f"Studio_{_drive_name(ceremony.studio.name)}"),
        (f"studio:{sid}/ceremony:{cid}", client),
    ]
    if kind:
        segs.append((f"studio:{sid}/ceremony:{cid}/{kind.lower()}", FOLDER_NAMES[kind]))
    return segs


def _folder_for(ceremony: Ceremony, kind: str):
    ceremony_folder, creds = folders.ensure_path(_segments(ceremony))
    if not ceremony.drive_folder_id:
        Ceremony.objects.filter(pk=ceremony.pk, drive_folder_id="").update(drive_folder_id=ceremony_folder)
    leaf, creds = folders.ensure_path(_segments(ceremony, kind), creds)
    return leaf, creds


# ------------------------------------------------------------------ start
def start_upload(
    request, ceremony: Ceremony, *, filename: str, mime_type: str, size_bytes: int, md5: str = ""
) -> tuple[CeremonyMedia, str]:
    user = request.user
    if not can_upload(user, ceremony):
        raise PermissionDenied("Bu marosimga media yuklash huquqingiz yo'q.")
    if ceremony.status == CeremonyStatus.ARCHIVED:
        raise ValidationError({"non_field_errors": ["Arxivlangan marosimga media yuklab bo'lmaydi."]})
    if mime_type not in MIME_TYPES:
        raise ValidationError({"mime_type": ["Bu fayl turi qo'llab-quvvatlanmaydi."]})
    kind = kind_of(mime_type)
    limit = _limits()["PHOTO_MAX_BYTES" if kind == MediaKind.PHOTO else "VIDEO_MAX_BYTES"]
    if size_bytes > limit:
        raise ValidationError({"size_bytes": [f"Fayl hajmi {limit // (1024 * 1024)} MB dan oshmasligi kerak."]})
    active = CeremonyMedia.objects.filter(ceremony=ceremony, status=MediaStatus.UPLOADING).count()
    if active >= _limits()["MAX_ACTIVE_PER_CEREMONY"]:
        raise ValidationError({"non_field_errors": ["Bir vaqtning o'zida yuklanayotgan fayllar juda ko'p."]})

    media = CeremonyMedia.objects.create(
        ceremony=ceremony,
        kind=kind,
        original_name=clean_filename(filename),
        mime_type=mime_type,
        size_bytes=size_bytes,
        md5_expected=md5.lower(),
        uploaded_by=user,
    )
    try:
        session_uri, folder_id = _open_session(ceremony, media, browser_origin(request))
    except (StorageError, GoogleError) as exc:
        CeremonyMedia.objects.filter(pk=media.pk).update(status=MediaStatus.FAILED, error_code=exc.code)
        raise _storage_error(exc) from None

    media.drive_folder_id = folder_id
    media.upload_session_encrypted = vault.seal(session_uri)
    media.session_expires_at = timezone.now() + timedelta(hours=_limits()["SESSION_TTL_HOURS"])
    media.save(update_fields=["drive_folder_id", "upload_session_encrypted", "session_expires_at", "updated_at"])
    return media, session_uri


def browser_origin(request) -> str | None:
    """The uploading web app's Origin, only if allowlisted (mobile apps send none and need none)."""
    origin = request.headers.get("Origin", "")
    return origin if origin in _limits().get("BROWSER_ORIGINS", ()) else None


def _open_session(ceremony: Ceremony, media: CeremonyMedia, origin: str | None = None) -> tuple[str, str]:
    for attempt in (1, 2):
        folder_id, creds = _folder_for(ceremony, media.kind)
        try:
            uri = gateway().start_resumable_upload(
                creds,
                name=f"{media.pk}{MIME_TYPES[media.mime_type]}",
                parent_id=folder_id,
                mime_type=media.mime_type,
                size=media.size_bytes,
                app_properties={"mg_media": str(media.pk), "mg_ceremony": str(ceremony.pk)},
                origin=origin,
            )
            return uri, folder_id
        except GoogleError as exc:
            if exc.code == "not_found" and attempt == 1:
                folders.forget(f"studio:{ceremony.studio_id}")  # folder deleted in Drive: rebuild once
                continue
            raise
    raise StorageError("not_found")  # pragma: no cover - loop always returns or raises


# --------------------------------------------------------------- progress
def session_uri(media: CeremonyMedia) -> str | None:
    if media.status != MediaStatus.UPLOADING or not media.upload_session_encrypted:
        return None
    try:
        return vault.unseal(media.upload_session_encrypted)
    except vault.VaultNotConfigured:
        return None


def _close_session(media: CeremonyMedia, status: str, error_code: str = "") -> bool:
    won = CeremonyMedia.objects.filter(pk=media.pk, status=MediaStatus.UPLOADING).update(
        status=status, error_code=error_code, upload_session_encrypted="", updated_at=timezone.now()
    )
    if won:
        media.status, media.error_code, media.upload_session_encrypted = status, error_code, ""
    return bool(won)


def progress(media: CeremonyMedia) -> int | None:
    """Bytes Google has received (live). Finalises silently if the upload already finished."""
    uri = session_uri(media)
    if uri is None:
        return media.size_bytes if media.status == MediaStatus.READY else None
    try:
        state = gateway().upload_status(uri, media.size_bytes)
    except GoogleError as exc:
        raise _storage_error(exc) from None
    if state.state == "expired":
        _close_session(media, MediaStatus.EXPIRED, "session_expired")
        return None
    if state.state == "complete":
        try:
            _finalize(None, media, state.file)
        except UploadRejected:
            return None
        return media.size_bytes
    return state.received


# --------------------------------------------------------------- complete
def complete(request, media: CeremonyMedia) -> CeremonyMedia:
    if media.status == MediaStatus.READY:
        return media  # idempotent
    uri = session_uri(media)
    if uri is None:
        raise Conflict("Bu yuklash yakunlangan yoki bekor qilingan.")
    try:
        state = gateway().upload_status(uri, media.size_bytes)
    except GoogleError as exc:
        raise _storage_error(exc) from None
    if state.state == "expired":
        _close_session(media, MediaStatus.EXPIRED, "session_expired")
        raise Conflict("Yuklash sessiyasining muddati tugagan. Qaytadan yuklang.")
    if state.state != "complete":
        raise UploadIncomplete(f"Fayl hali to'liq yuklanmagan: {state.received} / {media.size_bytes} bayt.")
    _finalize(request, media, state.file)
    return media


def _verify(media: CeremonyMedia, meta: dict) -> str:
    """'' when the Drive file is exactly what this row announced; otherwise a failure code."""
    if meta.get("trashed"):
        return "file_trashed"
    if media.drive_folder_id not in (meta.get("parents") or []):
        return "wrong_folder"
    if (meta.get("appProperties") or {}).get("mg_media") != str(media.pk):
        return "marker_mismatch"
    if str(meta.get("size")) != str(media.size_bytes):
        return "size_mismatch"
    if meta.get("mimeType") != media.mime_type:
        return "type_mismatch"
    if media.md5_expected and (meta.get("md5Checksum") or "").lower() != media.md5_expected:
        return "checksum_mismatch"
    return ""


def _finalize(request, media: CeremonyMedia, created: dict | None) -> None:
    file_id = (created or {}).get("id")
    if not file_id:
        raise _storage_error(StorageError("upload_response_invalid"))
    try:
        creds = access_credentials()
        meta = gateway().file_metadata(creds, file_id)  # re-read: never trust the upload response alone
    except (StorageError, GoogleError) as exc:
        raise _storage_error(exc) from None

    failure = _verify(media, meta)
    if failure:
        try:
            gateway().delete_file(creds, file_id)
        except GoogleError:
            logger.warning("could not delete rejected Drive file for media %s", media.pk)
        if _close_session(media, MediaStatus.FAILED, failure):
            record(request, AuditAction.MEDIA_UPLOAD_FAILED, media, actor=media.uploaded_by, changes={"code": failure})
        raise UploadRejected(f"{UploadRejected.default_detail} ({failure})")

    image = meta.get("imageMediaMetadata") or {}
    video = meta.get("videoMediaMetadata") or {}
    now = timezone.now()
    with transaction.atomic():
        won = CeremonyMedia.objects.filter(pk=media.pk, status=MediaStatus.UPLOADING).update(
            status=MediaStatus.READY,
            drive_file_id=file_id,
            md5_checksum=(meta.get("md5Checksum") or "")[:32],
            width=image.get("width") or video.get("width"),
            height=image.get("height") or video.get("height"),
            duration_ms=int(video["durationMillis"]) if video.get("durationMillis") else None,
            completed_at=now,
            upload_session_encrypted="",
            error_code="",
            updated_at=now,
        )
        media.refresh_from_db()
        if won:
            record(
                request,
                AuditAction.MEDIA_UPLOAD,
                media,
                actor=media.uploaded_by,
                changes={"ceremony": str(media.ceremony_id), "kind": media.kind, "size_bytes": media.size_bytes},
                target_label=f"{media.ceremony_id} · {media.kind}",
            )
            from .watermark_jobs import queue_for

            queue_for(media)  # videos: burned-in logo copy for viewers without a subscription


# ----------------------------------------------------------------- cancel
def cancel(request, media: CeremonyMedia) -> CeremonyMedia:
    if not can_cancel(request.user, media):
        raise PermissionDenied("Yuklashni faqat uni boshlagan a'zo yoki studiya menejeri bekor qila oladi.")
    uri = session_uri(media)
    if uri is None:
        raise Conflict("Bu yuklash yakunlangan yoki bekor qilingan.")
    gateway().cancel_upload(uri)
    _close_session(media, MediaStatus.CANCELLED)
    return media


def expire_stale() -> int:
    """Close sessions past their TTL (``manage.py expire_media_uploads``)."""
    count = 0
    for media in CeremonyMedia.objects.filter(status=MediaStatus.UPLOADING, session_expires_at__lte=timezone.now()):
        uri = session_uri(media)
        if uri:
            gateway().cancel_upload(uri)
        count += _close_session(media, MediaStatus.EXPIRED, "session_expired")
    return count
