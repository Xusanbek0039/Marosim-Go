"""Ceremonies (weddings, …) and the people attached to them.

Dependency direction: ceremonies → studios → accounts. Nothing below imports this app.

Two generations of access models live here (see ``docs/CEREMONY_OWNERSHIP.md``):

* ``CeremonyParticipant`` — v1 studio-side phone invitations (BRIDE/GROOM/OTHER). Still serves the
  current ``/ceremonies/{id}/participants/`` and ``/me/…`` endpoints until Phase C switches them.
* ``CeremonyInvitation`` → ``CeremonyOwnership`` / ``CeremonyViewerAccess`` — the ownership model:
  invitations by phone or JSHSHIR, several owners, owner-approved owner promotion, viewer sharing.
  Access is decided only by ACCEPTED ownership / viewer rows (``ownership.py``), never by an
  invitation existing.

An invitation is not linked to an account until its recipient accepts it, so an inviter never
learns whether a number / JSHSHIR has an account.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel
from apps.studios.models import Studio


class EventType(models.TextChoices):
    """``ceremony_type`` in the product spec (column name kept for API compatibility)."""

    WEDDING = "WEDDING", "To'y"
    ENGAGEMENT = "ENGAGEMENT", "Fotiha / unashtiruv"
    SUNNAT = "SUNNAT", "Sunnat to'yi"
    BESHIK = "BESHIK", "Beshik to'yi"
    BIRTHDAY = "BIRTHDAY", "Tug'ilgan kun"
    ANNIVERSARY = "ANNIVERSARY", "Yubiley"
    OTHER = "OTHER", "Boshqa marosim"


def cover_upload_to(instance, filename):
    return f"ceremonies/covers/{filename}"


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
    # Written only after ``core.uploads.process_image`` (re-encoded WEBP, metadata stripped).
    cover_image = models.ImageField(upload_to=cover_upload_to, null=True, blank=True)
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


# ============================================================ ownership model
class OwnerType(models.TextChoices):
    BRIDE = "BRIDE", "Kelin"
    GROOM = "GROOM", "Kuyov"
    FAMILY_OWNER = "FAMILY_OWNER", "Oila vakili"
    OTHER_OWNER = "OTHER_OWNER", "Boshqa mas'ul shaxs"


#: Owner types a ceremony can have at most one of (open = PENDING or ACCEPTED).
SINGLE_OWNER_TYPES = (OwnerType.BRIDE, OwnerType.GROOM)


class AccessRole(models.TextChoices):
    """Ceremony-specific access. Not a global ``User.role``."""

    VIEWER = "VIEWER", "Ko'ruvchi"
    OWNER = "OWNER", "Egasi"


class IdentifierType(models.TextChoices):
    PHONE = "PHONE", "Telefon raqam"
    PINFL = "PINFL", "JSHSHIR"


class InviterKind(models.TextChoices):
    STUDIO = "STUDIO", "Studiya"
    OWNER = "OWNER", "Marosim egasi"
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"


class InvitationStatus(models.TextChoices):
    PENDING = "PENDING", "Kutilmoqda"
    ACCEPTED = "ACCEPTED", "Qabul qilingan"
    DECLINED = "DECLINED", "Rad etilgan"
    EXPIRED = "EXPIRED", "Muddati tugagan"
    REVOKED = "REVOKED", "Bekor qilingan"


class OwnershipStatus(models.TextChoices):
    #: The invitee accepted an OWNER invitation; the ceremony's existing owners have not all approved yet.
    PENDING = "PENDING", "Tasdiq kutilmoqda"
    ACCEPTED = "ACCEPTED", "Tasdiqlangan"
    REJECTED = "REJECTED", "Rad etilgan"
    REVOKED = "REVOKED", "Bekor qilingan"


OPEN_OWNERSHIP = (OwnershipStatus.PENDING, OwnershipStatus.ACCEPTED)


class ViewerStatus(models.TextChoices):
    ACCEPTED = "ACCEPTED", "Faol"
    REVOKED = "REVOKED", "Bekor qilingan"


class ApprovalDecision(models.TextChoices):
    PENDING = "PENDING", "Kutilmoqda"
    APPROVED = "APPROVED", "Tasdiqlandi"
    REJECTED = "REJECTED", "Rad etildi"


class CeremonyInvitation(BaseModel):
    """An offer of VIEWER or OWNER access, addressed to a phone number or a JSHSHIR.

    The recipient identifier is stored encrypted (Fernet) plus a keyed blind index
    (``recipient_identifier_hash``) used for exact matching only. ``invited_user`` stays empty
    until the recipient — signed in, and matching the identifier — responds. Sending an
    invitation never grants anything by itself.
    """

    ceremony = models.ForeignKey(Ceremony, on_delete=models.CASCADE, related_name="invitations")
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ceremony_invitations",
    )
    identifier_type = models.CharField(max_length=10, choices=IdentifierType.choices)
    recipient_identifier_encrypted = models.TextField(editable=False)
    recipient_identifier_hash = models.CharField(max_length=64, editable=False)
    #: Masked identifier for the inviter's history (``+99890***4567`` / ``**********1234``).
    recipient_hint = models.CharField(max_length=24, editable=False)
    requested_role = models.CharField(max_length=10, choices=AccessRole.choices)
    #: Only for OWNER invitations.
    owner_type = models.CharField(max_length=20, choices=OwnerType.choices, blank=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    inviter_kind = models.CharField(max_length=20, choices=InviterKind.choices)
    status = models.CharField(max_length=10, choices=InvitationStatus.choices, default=InvitationStatus.PENDING)
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    send_count = models.PositiveSmallIntegerField(default=1)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    #: v1 row this invitation was migrated from (keeps the backfill idempotent).
    legacy_participant = models.OneToOneField(
        CeremonyParticipant, null=True, blank=True, on_delete=models.SET_NULL, related_name="invitation"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient_identifier_hash", "status"]),
            models.Index(fields=["ceremony", "status"]),
            models.Index(fields=["status", "expires_at"]),
        ]
        constraints = [
            # Duplicate handling: one pending invitation per recipient per ceremony.
            models.UniqueConstraint(
                fields=["ceremony", "identifier_type", "recipient_identifier_hash"],
                condition=Q(status="PENDING"),
                name="ceremonies_invitation_pending_unique",
            ),
            models.CheckConstraint(
                condition=(Q(requested_role="OWNER") & ~Q(owner_type=""))
                | (Q(requested_role="VIEWER") & Q(owner_type="")),
                name="ceremonies_invitation_owner_type_matches_role",
            ),
            # Only owners share VIEWER access; studios and admins hand out ownership only.
            models.CheckConstraint(
                condition=Q(requested_role="OWNER") | Q(inviter_kind="OWNER"),
                name="ceremonies_invitation_viewer_from_owner",
            ),
            models.CheckConstraint(
                condition=~Q(status="ACCEPTED") | Q(invited_user__isnull=False),
                name="ceremonies_invitation_accepted_has_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ceremony_id} {self.requested_role} → {self.recipient_hint} ({self.status})"


class CeremonyOwnership(BaseModel):
    """A user's ownership of a ceremony. Only ``ACCEPTED`` rows grant anything."""

    ceremony = models.ForeignKey(Ceremony, on_delete=models.CASCADE, related_name="ownerships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ceremony_ownerships")
    owner_type = models.CharField(max_length=20, choices=OwnerType.choices)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    invitation = models.OneToOneField(
        CeremonyInvitation, null=True, blank=True, on_delete=models.SET_NULL, related_name="ownership"
    )
    status = models.CharField(max_length=10, choices=OwnershipStatus.choices, default=OwnershipStatus.PENDING)
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["user", "status"]), models.Index(fields=["ceremony", "status"])]
        constraints = [
            # No duplicate active ownership for one user.
            models.UniqueConstraint(
                fields=["ceremony", "user"],
                condition=Q(status__in=["PENDING", "ACCEPTED"]),
                name="ceremonies_ownership_open_user_unique",
            ),
            models.UniqueConstraint(
                fields=["ceremony", "owner_type"],
                condition=Q(owner_type__in=["BRIDE", "GROOM"], status__in=["PENDING", "ACCEPTED"]),
                name="ceremonies_ownership_couple_type_unique",
            ),
            models.CheckConstraint(
                condition=~Q(status="ACCEPTED") | Q(accepted_at__isnull=False),
                name="ceremonies_ownership_accepted_has_timestamp",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ceremony_id} {self.owner_type} {self.user_id} ({self.status})"


class CeremonyOwnershipApproval(BaseModel):
    """One required approver of a PENDING ownership (an "owner request").

    Rows are created when the request opens, one per owner ACCEPTED at that moment — a snapshot:
    owners added later get no vote, owners revoked meanwhile lose theirs.
    """

    ownership = models.ForeignKey(CeremonyOwnership, on_delete=models.CASCADE, related_name="approvals")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    decision = models.CharField(max_length=10, choices=ApprovalDecision.choices, default=ApprovalDecision.PENDING)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["ownership", "approver"], name="ceremonies_approval_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.ownership_id} by {self.approver_id}: {self.decision}"


class CeremonyViewerAccess(BaseModel):
    """VIEWER access shared by an owner. Only that owner (or a Super Admin) may revoke it."""

    ceremony = models.ForeignKey(Ceremony, on_delete=models.CASCADE, related_name="viewer_accesses")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ceremony_views")
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    invitation = models.OneToOneField(
        CeremonyInvitation, null=True, blank=True, on_delete=models.SET_NULL, related_name="viewer_access"
    )
    status = models.CharField(max_length=10, choices=ViewerStatus.choices, default=ViewerStatus.ACCEPTED)
    accepted_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["user", "status"]), models.Index(fields=["ceremony", "status"])]
        constraints = [
            models.UniqueConstraint(
                fields=["ceremony", "user"],
                condition=Q(status="ACCEPTED"),
                name="ceremonies_viewer_active_user_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ceremony_id} VIEWER {self.user_id} ({self.status})"
