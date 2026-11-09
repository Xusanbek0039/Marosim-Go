"""Removing ceremony media.

* Unfinished uploads (UPLOADING / FAILED / CANCELLED / EXPIRED) never became a usable file, so the
  studio dismisses them itself (``dismiss``): an open Drive session is cancelled, the row is DELETED.
* A READY file is only removed through a request (user decision 2026-11-09): a studio member asks
  (``request_deletion``), an ADMIN with ``requests.media_delete`` or a SUPER_ADMIN approves or rejects.
  Approval moves the original and its watermarked copy to the Drive trash (restorable there for
  ~30 days) and marks the row DELETED, which hides it from every gallery and stream.
"""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.audit.services import AuditAction, record
from apps.ceremonies import services as ceremony_services
from apps.core.exceptions import Conflict
from apps.storage.google import GoogleError
from apps.storage.services import StorageError, access_credentials, gateway

from . import services
from .models import CeremonyMedia, DeletionRequestStatus, MediaDeletionRequest, MediaStatus

logger = logging.getLogger("apps.media")

DISMISSABLE = (MediaStatus.UPLOADING, MediaStatus.FAILED, MediaStatus.CANCELLED, MediaStatus.EXPIRED)


def _label(media: CeremonyMedia) -> str:
    return f"{media.ceremony_id} · {media.kind} · {media.original_name}"


# --------------------------------------------------------------- dismiss
def dismiss(request, media: CeremonyMedia) -> None:
    if not services.can_cancel(request.user, media):
        raise PermissionDenied("Yuklashni faqat uni boshlagan a'zo yoki studiya menejeri o'chira oladi.")
    if media.status not in DISMISSABLE:
        raise Conflict("Tayyor faylni o'chirish uchun administratorga so'rov yuboring.")
    uri = services.session_uri(media)
    if uri:
        try:
            gateway().cancel_upload(uri)
        except GoogleError:
            logger.warning("could not cancel Drive session for dismissed media %s", media.pk)
    won = CeremonyMedia.objects.filter(pk=media.pk, status__in=DISMISSABLE).update(
        status=MediaStatus.DELETED, upload_session_encrypted="", deleted_at=timezone.now(), updated_at=timezone.now()
    )
    if won:
        record(request, AuditAction.MEDIA_DISMISS, media, changes={"status": media.status}, target_label=_label(media))


# --------------------------------------------------------------- request
def pending_request(media: CeremonyMedia) -> MediaDeletionRequest | None:
    return media.deletion_requests.filter(status=DeletionRequestStatus.PENDING).first()


def request_deletion(request, media: CeremonyMedia, reason: str) -> MediaDeletionRequest:
    if not services.can_upload(request.user, media.ceremony):
        raise PermissionDenied("Bu marosim fayllarini o'chirishni so'rash huquqingiz yo'q.")
    if media.status != MediaStatus.READY:
        raise Conflict("Faqat tayyor fayl uchun o'chirish so'rovi yuboriladi.")
    try:
        with transaction.atomic():
            row = MediaDeletionRequest.objects.create(media=media, reason=reason.strip(), requested_by=request.user)
    except IntegrityError:
        raise Conflict("Bu fayl uchun o'chirish so'rovi allaqachon yuborilgan.") from None
    record(request, AuditAction.MEDIA_DELETE_REQUEST, row, changes={"media": str(media.pk)}, target_label=_label(media))
    return row


def cancel_request(request, media: CeremonyMedia) -> MediaDeletionRequest:
    row = pending_request(media)
    if row is None:
        raise Conflict("Kutilayotgan o'chirish so'rovi yo'q.")
    user = request.user
    if row.requested_by_id != user.pk and not ceremony_services.can_manage(user, media.ceremony):
        raise PermissionDenied("So'rovni faqat uni yuborgan a'zo yoki studiya menejeri bekor qila oladi.")
    _decide(row, DeletionRequestStatus.CANCELLED, user, "")
    record(request, AuditAction.MEDIA_DELETE_CANCEL, row, target_label=_label(media))
    return row


# --------------------------------------------------------------- decide
def _decide(row: MediaDeletionRequest, status: str, user, note: str) -> None:
    now = timezone.now()
    won = MediaDeletionRequest.objects.filter(pk=row.pk, status=DeletionRequestStatus.PENDING).update(
        status=status, decided_by=user, decided_at=now, decision_note=note, updated_at=now
    )
    if not won:
        raise Conflict("Bu so'rov allaqachon ko'rib chiqilgan.")
    row.status, row.decided_by, row.decided_at, row.decision_note = status, user, now, note


def _trash(creds, file_id: str) -> None:
    if not file_id:
        return
    try:
        gateway().trash_file(creds, file_id)
    except GoogleError as exc:
        if exc.code != "not_found":  # already gone from Drive: nothing left to remove
            raise


def approve(request, row: MediaDeletionRequest, note: str = "") -> MediaDeletionRequest:
    if row.status != DeletionRequestStatus.PENDING:
        raise Conflict("Bu so'rov allaqachon ko'rib chiqilgan.")
    media = row.media
    try:
        creds = access_credentials()
        _trash(creds, media.drive_file_id)
        _trash(creds, media.wm_drive_file_id)
    except (StorageError, GoogleError) as exc:
        raise services._storage_error(exc) from None  # request stays PENDING; retry later
    with transaction.atomic():
        _decide(row, DeletionRequestStatus.APPROVED, request.user, note)
        now = timezone.now()
        CeremonyMedia.objects.filter(pk=media.pk).update(status=MediaStatus.DELETED, deleted_at=now, updated_at=now)
    record(
        request,
        AuditAction.MEDIA_DELETE_APPROVE,
        row,
        changes={"media": str(media.pk), "note": note},
        target_label=_label(media),
    )
    return row


def reject(request, row: MediaDeletionRequest, note: str = "") -> MediaDeletionRequest:
    _decide(row, DeletionRequestStatus.REJECTED, request.user, note)
    record(
        request,
        AuditAction.MEDIA_DELETE_REJECT,
        row,
        changes={"media": str(row.media_id), "note": note},
        target_label=_label(row.media),
    )
    return row
