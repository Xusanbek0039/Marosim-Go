from django.conf import settings
from django.db import models

from apps.accounts import phone as phone_utils
from apps.core.models import BaseModel, SoftDeleteModel


def studio_upload_to(instance, filename):
    return f"studios/{filename}"


class Studio(BaseModel, SoftDeleteModel):
    """An organisation. Personal data (PINFL) belongs to ``responsible_user``, not to the studio.

    ``responsible_user`` is the studio *owner*; it is mirrored as an OWNER ``StudioMembership``
    (``services.sync_owner_membership``) so every studio-side permission checks memberships only.
    """

    name = models.CharField(max_length=150)
    description = models.TextField(max_length=2000, blank=True)
    profile_picture = models.ImageField(upload_to=studio_upload_to, null=True, blank=True)
    address = models.CharField(max_length=255)
    #: Public contact number of the studio (E.164), shown on its public profile.
    phone_number = models.CharField(max_length=16, blank=True, validators=[phone_utils.validate_e164])
    responsible_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="responsible_studios"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_active", "created_at"])]

    def __str__(self) -> str:
        return self.name


#: Portfolio size limit (same as a venue gallery).
MAX_PORTFOLIO_IMAGES = 20


class StudioImage(BaseModel):
    """Portfolio image of a studio (its work), shown on the public studio profile."""

    studio = models.ForeignKey(Studio, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=studio_upload_to)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "created_at"]
        indexes = [models.Index(fields=["studio", "position"])]

    def __str__(self) -> str:
        return f"{self.studio_id} #{self.position}"


class StudioMembership(BaseModel):
    """A STUDIO-role account working for a studio. Studio-side API access is decided here.

    OWNER/MANAGER manage ceremonies and participants; UPLOADER will only upload media (Phase C).
    """

    class Role(models.TextChoices):
        OWNER = "OWNER", "Egasi"
        MANAGER = "MANAGER", "Menejer"
        UPLOADER = "UPLOADER", "Yuklovchi"

    #: Roles allowed to create/edit ceremonies and manage participants.
    MANAGING_ROLES = (Role.OWNER, Role.MANAGER)

    studio = models.ForeignKey(Studio, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="studio_memberships")
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["studio", "user"], name="studios_membership_unique")]
        indexes = [models.Index(fields=["user", "is_active"])]

    def __str__(self) -> str:
        return f"{self.studio} · {self.user} ({self.role})"
