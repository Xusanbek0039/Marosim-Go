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
    #: Weekly days off (0 = Monday … 6 = Sunday), shown as "dam olish" on the public calendar.
    off_weekdays = models.JSONField(default=list, blank=True)
    #: Space for the studio's portfolio (photos + reels), kept on Google Drive. Set by the panel.
    portfolio_quota_mb = models.PositiveIntegerField(default=1024)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_active", "created_at"])]

    def __str__(self) -> str:
        return self.name


def reel_upload_to(instance, filename):
    return f"studios/reels/{filename}"


#: Portfolio size limits: photos (same as a venue gallery) and vertical reels.
MAX_PORTFOLIO_IMAGES = 20
MAX_PORTFOLIO_REELS = 15


class PortfolioKind(models.TextChoices):
    IMAGE = "IMAGE", "Rasm"
    #: Vertical (9:16) short video. Needs the studio's paid badge (galichka).
    VIDEO = "VIDEO", "Reels video"


class PortfolioStorage(models.TextChoices):
    #: Google Drive: ``MarosimGo / Studio_<nom> / Portfolio`` (default when Drive is connected).
    DRIVE = "DRIVE", "Google Drive"
    #: Local MEDIA_ROOT: older rows and installations without a Drive connection.
    LOCAL = "LOCAL", "Server diski"


class StudioImage(BaseModel):
    """Portfolio item of a studio (its work), shown on the public studio profile.

    ``kind=VIDEO`` rows are reels: the video and its poster frame. Reels, reactions and comments are
    public only while the studio's galichka is active. Files live on Drive (``drive_*_id``) or, for
    ``storage=LOCAL``, in ``image`` / ``video``. ``size_bytes`` counts against the studio's quota.
    """

    studio = models.ForeignKey(Studio, on_delete=models.CASCADE, related_name="images")
    kind = models.CharField(max_length=5, choices=PortfolioKind.choices, default=PortfolioKind.IMAGE)
    storage = models.CharField(max_length=5, choices=PortfolioStorage.choices, default=PortfolioStorage.LOCAL)
    image = models.ImageField(upload_to=studio_upload_to, blank=True)
    video = models.FileField(upload_to=reel_upload_to, null=True, blank=True)
    drive_file_id = models.CharField(max_length=128, blank=True, help_text="Video (reels) yoki rasm fayli")
    drive_poster_id = models.CharField(max_length=128, blank=True, help_text="Reels muqovasi")
    mime_type = models.CharField(max_length=50, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    caption = models.CharField(max_length=300, blank=True)
    duration = models.FloatField(default=0)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "created_at"]
        indexes = [models.Index(fields=["studio", "kind", "position"])]

    def __str__(self) -> str:
        return f"{self.studio_id} {self.kind} #{self.position}"


class StudioPortfolioReaction(BaseModel):
    """One like (+1) or dislike (-1) per customer per portfolio item."""

    LIKE, DISLIKE = 1, -1

    item = models.ForeignKey(StudioImage, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    value = models.SmallIntegerField(choices=[(LIKE, "Like"), (DISLIKE, "Dislike")])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "user"], name="studios_reaction_one_per_item"),
            models.CheckConstraint(condition=models.Q(value__in=[1, -1]), name="studios_reaction_value"),
        ]


class StudioPortfolioComment(BaseModel):
    """Customer comment on a portfolio item. The studio (OWNER/MANAGER) may hide it."""

    item = models.ForeignKey(StudioImage, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    text = models.TextField(max_length=500)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["item", "is_hidden", "created_at"])]


class StudioDayStatus(BaseModel):
    """A day the studio marked by hand on its calendar (ceremonies already count as busy)."""

    class Status(models.TextChoices):
        BUSY = "BUSY", "Band"
        OFF = "OFF", "Dam olish"

    studio = models.ForeignKey(Studio, on_delete=models.CASCADE, related_name="day_statuses")
    date = models.DateField()
    status = models.CharField(max_length=4, choices=Status.choices)
    #: Private to the studio — never shown publicly.
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["date"]
        constraints = [models.UniqueConstraint(fields=["studio", "date"], name="studios_day_status_unique")]


class StudioConversation(BaseModel):
    """Chat between one customer (USER) and one studio. Opening it needs the studio's galichka."""

    studio = models.ForeignKey(Studio, on_delete=models.CASCADE, related_name="conversations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="studio_conversations")
    last_message_at = models.DateTimeField()
    user_read_at = models.DateTimeField(null=True, blank=True)
    studio_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_message_at"]
        constraints = [models.UniqueConstraint(fields=["studio", "user"], name="studios_conversation_unique")]
        indexes = [models.Index(fields=["studio", "last_message_at"]), models.Index(fields=["user", "last_message_at"])]


class StudioChatMessage(BaseModel):
    conversation = models.ForeignKey(StudioConversation, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    #: Written by a studio member (otherwise by the customer).
    from_studio = models.BooleanField(default=False)
    body = models.TextField(max_length=2000)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]


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
