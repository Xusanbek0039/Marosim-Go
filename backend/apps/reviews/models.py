"""Customer reviews (baho + izoh) and likes of venues and studios.

Dependency direction: reviews → accounts / core; venues and studios are referenced by string so
``venues`` / ``studios`` may import ``reviews.services`` for their public cards without a cycle.

A row targets exactly one business: ``venue`` *or* ``studio`` (DB check constraint). One review and
one like per account per business. Hidden reviews (panel moderation) are kept for the audit trail
but never shown publicly and never counted in the rating.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel

ONE_TARGET = (Q(venue__isnull=False) & Q(studio__isnull=True)) | (Q(venue__isnull=True) & Q(studio__isnull=False))


class TargetKind(models.TextChoices):
    VENUE = "venue", "To'yxona"
    STUDIO = "studio", "Studiya"


class Review(BaseModel):
    venue = models.ForeignKey("venues.Venue", on_delete=models.CASCADE, null=True, blank=True, related_name="reviews")
    studio = models.ForeignKey(
        "studios.Studio", on_delete=models.CASCADE, null=True, blank=True, related_name="reviews"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField(max_length=1000, blank=True)
    #: Set by a (super) admin. Hidden reviews are invisible to the public and excluded from ratings.
    is_hidden = models.BooleanField(default=False)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["venue", "is_hidden"]),
            models.Index(fields=["studio", "is_hidden"]),
        ]
        constraints = [
            models.CheckConstraint(condition=ONE_TARGET, name="reviews_review_one_target"),
            models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name="reviews_review_rating_range"),
            models.UniqueConstraint(
                fields=["venue", "author"], condition=Q(venue__isnull=False), name="reviews_review_one_per_venue"
            ),
            models.UniqueConstraint(
                fields=["studio", "author"], condition=Q(studio__isnull=False), name="reviews_review_one_per_studio"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.venue_id or self.studio_id} · {self.rating}★"

    @property
    def kind(self) -> str:
        return TargetKind.VENUE if self.venue_id else TargetKind.STUDIO


class Like(BaseModel):
    venue = models.ForeignKey("venues.Venue", on_delete=models.CASCADE, null=True, blank=True, related_name="likes")
    studio = models.ForeignKey("studios.Studio", on_delete=models.CASCADE, null=True, blank=True, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=ONE_TARGET, name="reviews_like_one_target"),
            models.UniqueConstraint(
                fields=["venue", "user"], condition=Q(venue__isnull=False), name="reviews_like_one_per_venue"
            ),
            models.UniqueConstraint(
                fields=["studio", "user"], condition=Q(studio__isnull=False), name="reviews_like_one_per_studio"
            ),
        ]

    def __str__(self) -> str:
        return f"♥ {self.venue_id or self.studio_id}"
