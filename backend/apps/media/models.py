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

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ceremony", "status"]),
            models.Index(fields=["status", "session_expires_at"]),
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
