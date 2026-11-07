"""Ceremonies (weddings) and the people attached to them.

Dependency direction: ceremonies → studios → accounts. Nothing below imports this app.

Participants are invited **by phone number**. The invitation is not linked to an account until
the owner of that number accepts it, so a studio can never learn whether a number has an
account, and a wrong number never exposes the ceremony to a stranger without their consent.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel
from apps.studios.models import Studio


class EventType(models.TextChoices):
    WEDDING = "WEDDING", "To'y"


class CeremonyStatus(models.TextChoices):
    DRAFT = "DRAFT", "Qoralama"
    UPLOADING = "UPLOADING", "Yuklanmoqda"
    PROCESSING = "PROCESSING", "Qayta ishlanmoqda"
    READY = "READY", "Tayyor"
    ARCHIVED = "ARCHIVED", "Arxivlangan"


#: Transitions a studio may make by hand. UPLOADING / PROCESSING belong to the media pipeline.
STUDIO_TRANSITIONS: dict[str, frozenset[str]] = {
    CeremonyStatus.DRAFT: frozenset({CeremonyStatus.READY, CeremonyStatus.ARCHIVED}),
    CeremonyStatus.READY: frozenset({CeremonyStatus.DRAFT, CeremonyStatus.ARCHIVED}),
    CeremonyStatus.ARCHIVED: frozenset({CeremonyStatus.DRAFT, CeremonyStatus.READY}),
    CeremonyStatus.UPLOADING: frozenset(),
    CeremonyStatus.PROCESSING: frozenset(),
}

#: Statuses a couple can see. DRAFT is studio-internal.
VISIBLE_TO_PARTICIPANTS = (
    CeremonyStatus.UPLOADING,
    CeremonyStatus.PROCESSING,
    CeremonyStatus.READY,
    CeremonyStatus.ARCHIVED,
)


class Ceremony(BaseModel):
    studio = models.ForeignKey(Studio, on_delete=models.PROTECT, related_name="ceremonies")
    title = models.CharField(max_length=200)
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.WEDDING)
    event_date = models.DateField()
    description = models.TextField(max_length=2000, blank=True)
    status = models.CharField(max_length=20, choices=CeremonyStatus.choices, default=CeremonyStatus.DRAFT)
    # Set by the storage module (Phase B); never writable through the API.
    drive_folder_id = models.CharField(max_length=128, blank=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-event_date", "-created_at"]
        indexes = [
            models.Index(fields=["studio", "status"]),
            models.Index(fields=["event_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.event_date})"


class ParticipantType(models.TextChoices):
    BRIDE = "BRIDE", "Kelin"
    GROOM = "GROOM", "Kuyov"
    OTHER = "OTHER", "Boshqa"


class AccessStatus(models.TextChoices):
    INVITED = "INVITED", "Taklif yuborilgan"
    ACTIVE = "ACTIVE", "Faol"
    DECLINED = "DECLINED", "Rad etilgan"
    REVOKED = "REVOKED", "Bekor qilingan"


OPEN_STATUSES = (AccessStatus.INVITED, AccessStatus.ACTIVE)
COUPLE_TYPES = (ParticipantType.BRIDE, ParticipantType.GROOM)


class CeremonyParticipant(BaseModel):
    ceremony = models.ForeignKey(Ceremony, on_delete=models.CASCADE, related_name="participants")
    #: E.164 number the studio invited. The invitation belongs to whoever proves this number.
    phone_number = models.CharField(max_length=16)
    #: Empty until the owner of ``phone_number`` accepts.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ceremony_participations",
    )
    participant_type = models.CharField(max_length=10, choices=ParticipantType.choices)
    access_status = models.CharField(max_length=10, choices=AccessStatus.choices, default=AccessStatus.INVITED)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["phone_number", "access_status"]),
            models.Index(fields=["user", "access_status"]),
        ]
        constraints = [
            # One open invitation per number per ceremony (DECLINED/REVOKED rows are history).
            models.UniqueConstraint(
                fields=["ceremony", "phone_number"],
                condition=Q(access_status__in=["INVITED", "ACTIVE"]),
                name="ceremonies_participant_open_phone_unique",
            ),
            # At most one bride and one groom per ceremony.
            models.UniqueConstraint(
                fields=["ceremony", "participant_type"],
                condition=Q(participant_type__in=["BRIDE", "GROOM"], access_status__in=["INVITED", "ACTIVE"]),
                name="ceremonies_participant_couple_role_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ceremony_id} {self.participant_type} {self.access_status}"
