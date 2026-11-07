"""Venues (to'yxonalar), their halls and the people who run them.

Dependency direction: venues → accounts / core. Scheduling, pricing and bookings (Phases C–G)
will depend on this app, never the other way round.

* ``Venue`` — the business listed to the public (after admin approval, Phase E).
* ``VenueHall`` — a bookable room. Availability is kept per hall, so one hall being busy never
  blocks another hall of the same venue. Every venue gets a default hall on creation.
* ``VenueMembership`` — who works for the venue and what they may do there. A VENUE_OWNER account
  may be a member of several venues with different roles; ``User.role`` is only the account-type
  gate, the membership decides the data scope and the actions (``CAPABILITIES``).
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.accounts import phone as phone_utils
from apps.core.models import BaseModel, SoftDeleteModel

#: Money: Uzbek so'm, stored exactly (never float). 14 digits ≈ up to 999 billion so'm.
MONEY = {"max_digits": 14, "decimal_places": 2}


class Currency(models.TextChoices):
    UZS = "UZS", "O'zbek so'mi"


class Region(models.TextChoices):
    """Top-level administrative divisions of Uzbekistan (district stays free text)."""

    TASHKENT_CITY = "TASHKENT_CITY", "Toshkent shahri"
    TASHKENT = "TASHKENT", "Toshkent viloyati"
    ANDIJAN = "ANDIJAN", "Andijon viloyati"
    BUKHARA = "BUKHARA", "Buxoro viloyati"
    FERGANA = "FERGANA", "Farg'ona viloyati"
    JIZZAKH = "JIZZAKH", "Jizzax viloyati"
    KHOREZM = "KHOREZM", "Xorazm viloyati"
    NAMANGAN = "NAMANGAN", "Namangan viloyati"
    NAVOI = "NAVOI", "Navoiy viloyati"
    KASHKADARYA = "KASHKADARYA", "Qashqadaryo viloyati"
    KARAKALPAKSTAN = "KARAKALPAKSTAN", "Qoraqalpog'iston Respublikasi"
    SAMARKAND = "SAMARKAND", "Samarqand viloyati"
    SIRDARYO = "SIRDARYO", "Sirdaryo viloyati"
    SURKHANDARYA = "SURKHANDARYA", "Surxondaryo viloyati"


class VenueType(models.TextChoices):
    """``venue_type`` filter of the date search (Phase F)."""

    BANQUET_HALL = "BANQUET_HALL", "To'yxona"
    RESTAURANT = "RESTAURANT", "Restoran"
    CAFE = "CAFE", "Kafe"
    OUTDOOR = "OUTDOOR", "Ochiq maydon"
    OTHER = "OTHER", "Boshqa"


class PublicationStatus(models.TextChoices):
    """Whether the venue's calendar may be shown to the public. Changed only by the workflow (Phase E)."""

    PRIVATE = "PRIVATE", "Yopiq"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Tasdiq kutilmoqda"
    APPROVED = "APPROVED", "Tasdiqlangan"
    REJECTED = "REJECTED", "Rad etilgan"
    SUSPENDED = "SUSPENDED", "To'xtatilgan"


def venue_upload_to(instance, filename):
    return f"venues/{filename}"


class Venue(BaseModel, SoftDeleteModel):
    name = models.CharField(max_length=150)
    description = models.TextField(max_length=4000, blank=True)
    venue_type = models.CharField(max_length=20, choices=VenueType.choices, default=VenueType.BANQUET_HALL)
    address = models.CharField(max_length=255)
    region = models.CharField(max_length=20, choices=Region.choices)
    district = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))],
    )
    #: Public contact number of the business (E.164) — not a member's personal number.
    phone_number = models.CharField(max_length=16, blank=True, validators=[phone_utils.validate_e164])
    # Written only after ``core.uploads.process_image`` (re-encoded WEBP, metadata stripped).
    cover_image = models.ImageField(upload_to=venue_upload_to, null=True, blank=True)
    capacity_min = models.PositiveIntegerField(default=0)
    capacity_max = models.PositiveIntegerField()
    #: Starting price shown on the venue card; the real quote comes from the pricing engine (Phase D).
    base_price = models.DecimalField(**MONEY, validators=[MinValueValidator(Decimal("0"))])
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.UZS)
    #: Blocked by a (super) admin when False. Owners cannot change it.
    is_active = models.BooleanField(default=True)
    publication_status = models.CharField(
        max_length=20, choices=PublicationStatus.choices, default=PublicationStatus.PRIVATE
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "publication_status"]),
            models.Index(fields=["region", "district"]),
            models.Index(fields=["base_price"]),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(capacity_max__gte=1), name="venues_venue_capacity_max_positive"),
            models.CheckConstraint(
                condition=Q(capacity_min__lte=F("capacity_max")), name="venues_venue_capacity_range"
            ),
            models.CheckConstraint(condition=Q(base_price__gte=0), name="venues_venue_base_price_non_negative"),
            models.CheckConstraint(condition=Q(currency="UZS"), name="venues_venue_currency_uzs"),
            models.CheckConstraint(
                condition=Q(latitude__isnull=True) | Q(latitude__gte=-90, latitude__lte=90),
                name="venues_venue_latitude_range",
            ),
            models.CheckConstraint(
                condition=Q(longitude__isnull=True) | Q(longitude__gte=-180, longitude__lte=180),
                name="venues_venue_longitude_range",
            ),
            models.CheckConstraint(
                condition=Q(phone_number="") | Q(phone_number__startswith="+"), name="venues_venue_phone_e164"
            ),
            models.CheckConstraint(
                condition=Q(publication_status__in=[s.value for s in PublicationStatus]),
                name="venues_venue_publication_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class VenueImage(BaseModel):
    """Gallery image of a venue (ordered). Processed like every other upload."""

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=venue_upload_to)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "created_at"]
        indexes = [models.Index(fields=["venue", "position"])]

    def __str__(self) -> str:
        return f"{self.venue_id} #{self.position}"


class VenueHall(BaseModel, SoftDeleteModel):
    """A bookable banquet hall. Scheduling (Phase C) attaches calendar entries to halls, not venues."""

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="halls")
    name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()
    #: ``None`` = use the venue's ``base_price`` (the pricing engine resolves it, Phase D).
    base_price = models.DecimalField(**MONEY, null=True, blank=True, validators=[MinValueValidator(Decimal("0"))])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["venue", "is_active"])]
        constraints = [
            models.UniqueConstraint(
                fields=["venue", "name"],
                condition=Q(deleted_at__isnull=True),
                name="venues_hall_name_unique_per_venue",
            ),
            models.CheckConstraint(condition=Q(capacity__gte=1), name="venues_hall_capacity_positive"),
            models.CheckConstraint(
                condition=Q(base_price__isnull=True) | Q(base_price__gte=0), name="venues_hall_base_price_non_negative"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.venue} · {self.name}"

    @property
    def effective_base_price(self) -> Decimal:
        return self.base_price if self.base_price is not None else self.venue.base_price


class Capability(models.TextChoices):
    """What a venue member may do inside *their* venue. Checked by ``services.ensure_capability``."""

    VIEW = "VIEW", "Ko'rish"
    EDIT_PROFILE = "EDIT_PROFILE", "Profilni tahrirlash"
    MANAGE_HALLS = "MANAGE_HALLS", "Zallarni boshqarish"
    MANAGE_SCHEDULE = "MANAGE_SCHEDULE", "Kalendarni boshqarish"
    MANAGE_PRICING = "MANAGE_PRICING", "Narxlarni boshqarish"
    MANAGE_BOOKINGS = "MANAGE_BOOKINGS", "Bronlarni boshqarish (tasdiqlash / bekor qilish)"
    REQUEST_PUBLICATION = "REQUEST_PUBLICATION", "Ommaga chiqarish so'rovi"
    MANAGE_MEMBERS = "MANAGE_MEMBERS", "A'zolarni boshqarish"


class MembershipRole(models.TextChoices):
    OWNER = "OWNER", "Egasi"
    MANAGER = "MANAGER", "Menejer"
    SCHEDULER = "SCHEDULER", "Jadval yurituvchi"
    VIEWER = "VIEWER", "Kuzatuvchi"


_C = Capability
#: Single source of the membership → capability matrix (documented in docs/VENUE_AVAILABILITY.md).
CAPABILITIES: dict[str, frozenset[str]] = {
    MembershipRole.OWNER: frozenset(_C.values),
    MembershipRole.MANAGER: frozenset(
        {_C.VIEW, _C.EDIT_PROFILE, _C.MANAGE_HALLS, _C.MANAGE_SCHEDULE, _C.MANAGE_PRICING, _C.MANAGE_BOOKINGS}
    ),
    MembershipRole.SCHEDULER: frozenset({_C.VIEW, _C.MANAGE_SCHEDULE}),
    MembershipRole.VIEWER: frozenset({_C.VIEW}),
}


class VenueMembership(BaseModel):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="venue_memberships")
    role = models.CharField(max_length=20, choices=MembershipRole.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["user", "is_active"]), models.Index(fields=["venue", "is_active"])]
        constraints = [
            models.UniqueConstraint(fields=["venue", "user"], name="venues_membership_unique"),
            models.CheckConstraint(
                condition=Q(role__in=[r.value for r in MembershipRole]), name="venues_membership_role_valid"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.venue} · {self.user} ({self.role})"

    @property
    def capabilities(self) -> frozenset[str]:
        return CAPABILITIES.get(self.role, frozenset()) if self.is_active else frozenset()
