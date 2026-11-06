from django.conf import settings
from django.db import models

from apps.core.models import BaseModel, SoftDeleteModel


def studio_upload_to(instance, filename):
    return f"studios/{filename}"


class Studio(BaseModel, SoftDeleteModel):
    """An organisation. Personal data (PINFL) belongs to ``responsible_user``, not to the studio."""

    name = models.CharField(max_length=150)
    profile_picture = models.ImageField(upload_to=studio_upload_to, null=True, blank=True)
    address = models.CharField(max_length=255)
    responsible_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="responsible_studios"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_active", "created_at"])]

    def __str__(self) -> str:
        return self.name


class StudioMembership(BaseModel):
    """Staff attached to a studio (operators, videographers…). API comes in a later phase."""

    class Role(models.TextChoices):
        OWNER = "OWNER", "Egasi"
        MANAGER = "MANAGER", "Menejer"
        OPERATOR = "OPERATOR", "Operator"
        VIDEOGRAPHER = "VIDEOGRAPHER", "Videograf"

    studio = models.ForeignKey(Studio, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="studio_memberships")
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["studio", "user"], name="studios_membership_unique")]

    def __str__(self) -> str:
        return f"{self.studio} · {self.user} ({self.role})"
