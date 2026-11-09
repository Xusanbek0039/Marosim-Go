"""Photos and videos of a ceremony, stored in the connected Google Drive.

Dependency direction: media → ceremonies, storage. A row is the *only* thing that ties a Drive file to
a ceremony; Drive ids are never exposed through the API and never grant access by themselves.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.ceremonies.models import Ceremony
from apps.core.models import BaseModel


class MediaKind(models.TextChoices):
    PHOTO = "PHOTO", "Rasm"
    VIDEO = "VIDEO", "Video"


class MediaStatus(models.TextChoices):
    #: A Drive resumable session is open; bytes go from the client straight to Google.
    UPLOADING = "UPLOADING", "Yuklanmoqda"
    READY = "READY", "Tayyor"
    FAILED = "FAILED", "Xato"
    CANCELLED = "CANCELLED", "Bekor qilingan"
    EXPIRED = "EXPIRED", "Sessiya muddati tugagan"
    #: Removed: an admin approved a deletion request (Drive file trashed) or the studio dismissed a
    #: failed/unfinished upload. Hidden from every list; the row stays for the audit trail.
    DELETED = "DELETED", "O'chirilgan"


#: Accepted content types → Drive file extension. The declared type is verified against Drive on completion.
PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}
VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/x-m4v": ".m4v",
    "video/webm": ".webm",
    "video/x-matroska": ".mkv",
}
MIME_TYPES = {**PHOTO_TYPES, **VIDEO_TYPES}


def kind_of(mime_type: str) -> str:
    return MediaKind.PHOTO if mime_type in PHOTO_TYPES else MediaKind.VIDEO


class WatermarkStatus(models.TextChoices):
    """Burned-in logo copy of a VIDEO (photos are stamped on the fly and stay NONE)."""

    NONE = "NONE", "Kerak emas"
    PENDING = "PENDING", "Navbatda"
    PROCESSING = "PROCESSING", "Tayyorlanmoqda"
    READY = "READY", "Tayyor"
    FAILED = "FAILED", "Xato"


class CeremonyMedia(BaseModel):
    ceremony = models.ForeignKey(Ceremony, on_delete=models.PROTECT, related_name="media")
    kind = models.CharField(max_length=10, choices=MediaKind.choices)
    status = models.CharField(max_length=12, choices=MediaStatus.choices, default=MediaStatus.UPLOADING)
    #: Display only (sanitised, never used as a path or Drive name).
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.BigIntegerField()
    #: Optional client-supplied MD5, compared with Drive's checksum on completion.
    md5_expected = models.CharField(max_length=32, blank=True)
    md5_checksum = models.CharField(max_length=32, blank=True)
    drive_folder_id = models.CharField(max_length=128, blank=True)
    drive_file_id = models.CharField(max_length=128, blank=True, db_index=True)
    #: Resumable session URI (a bearer capability for this one upload) — Fernet-encrypted, never logged.
    upload_session_encrypted = models.TextField(blank=True, editable=False)
    session_expires_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration_ms = models.PositiveBigIntegerField(null=True, blank=True)
    # Watermarked copy (videos): what everyone without a running subscription is served.
    wm_status = models.CharField(max_length=12, choices=WatermarkStatus.choices, default=WatermarkStatus.NONE)
    wm_drive_file_id = models.CharField(max_length=128, blank=True)
    wm_size_bytes = models.BigIntegerField(null=True, blank=True)
    wm_attempts = models.PositiveSmallIntegerField(default=0)
    wm_error = models.CharField(max_length=300, blank=True)
    wm_started_at = models.DateTimeField(null=True, blank=True)
    #: 0-100 while PROCESSING, shown in the gallery.
    wm_progress = models.PositiveSmallIntegerField(default=0)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ceremony", "status"]),
            models.Index(fields=["status", "session_expires_at"]),
            models.Index(fields=["wm_status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["drive_file_id"], condition=~Q(drive_file_id=""), name="media_drive_file_unique"
            ),
            models.CheckConstraint(
                condition=~Q(status="READY") | ~Q(drive_file_id=""), name="media_ready_has_drive_file"
            ),
            models.CheckConstraint(condition=Q(size_bytes__gt=0), name="media_size_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.original_name} ({self.status})"


class DeletionRequestStatus(models.TextChoices):
    PENDING = "PENDING", "Kutilmoqda"
    APPROVED = "APPROVED", "Tasdiqlangan"
    REJECTED = "REJECTED", "Rad etilgan"
    CANCELLED = "CANCELLED", "Bekor qilingan"


class MediaDeletionRequest(BaseModel):
    """A studio asks to delete a READY file; an ADMIN (``requests.media_delete``) or SUPER_ADMIN decides.

    Approval moves the Drive file (and its watermarked copy) to the Drive trash and marks the media
    DELETED. At most one PENDING request per file.
    """

    media = models.ForeignKey(CeremonyMedia, on_delete=models.PROTECT, related_name="deletion_requests")
    status = models.CharField(
        max_length=12, choices=DeletionRequestStatus.choices, default=DeletionRequestStatus.PENDING
    )
    reason = models.CharField(max_length=500)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["media"], condition=Q(status="PENDING"), name="media_deletion_one_pending"
            ),
        ]

    def __str__(self) -> str:
        return f"delete {self.media_id} ({self.status})"
