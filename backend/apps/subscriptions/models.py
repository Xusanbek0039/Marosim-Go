"""Paid subscriptions of couples (USER accounts) — sold by hand for now, approved in the admin panel.

User decisions 2026-11-08:
* Without a subscription: media is shown with the MarosimGo logo and cannot be downloaded; an owner
  may share with 5 people (``CEREMONY_MAX_VIEWERS_PER_OWNER``).
* With an active subscription the owner sees originals without the logo, may download them and may
  share with the plan's ``max_viewers`` people. Viewers never download.
* Plans (prices editable by the Super Admin / permitted admins): 1 month 25 000, 3 months 60 000,
  1 year 100 000, 5 years 300 000 so'm; viewers 10 / 20 / 30 / 50.
* Payment is not automated: the couple sends a request, an admin records the payment and approves.

Dependency direction: subscriptions → accounts / core. Media and ceremonies ask
``services.active_subscription(user)``; this app never imports them.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel

MONEY = {"max_digits": 14, "decimal_places": 2}


class SubscriptionPlan(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=60)
    duration_months = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(**MONEY, validators=[MinValueValidator(Decimal("0"))])
    currency = models.CharField(max_length=3, default="UZS")
    #: How many people an owner with this plan may share a ceremony with at once.
    max_viewers = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "duration_months"]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="subscriptions_plan_price_non_negative"),
            models.CheckConstraint(condition=Q(duration_months__gte=1), name="subscriptions_plan_duration_positive"),
            models.CheckConstraint(condition=Q(max_viewers__gte=1), name="subscriptions_plan_viewers_positive"),
        ]

    def __str__(self) -> str:
        return self.name


class SubscriptionStatus(models.TextChoices):
    PENDING = "PENDING", "To'lov tasdig'i kutilmoqda"
    ACTIVE = "ACTIVE", "Faol"  # still check ends_at: an ACTIVE row past its end is expired
    REJECTED = "REJECTED", "Rad etilgan"
    CANCELLED = "CANCELLED", "Bekor qilingan"


class PaymentMethod(models.TextChoices):
    CARD_TRANSFER = "CARD_TRANSFER", "Kartadan kartaga"
    CASH = "CASH", "Naqd"
    CLICK = "CLICK", "Click"
    PAYME = "PAYME", "Payme"
    BANK = "BANK", "Bank o'tkazmasi"
    OTHER = "OTHER", "Boshqa"


class Subscription(BaseModel):
    """One purchase. Plan terms are copied at request time so a later price change never moves it."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=10, choices=SubscriptionStatus.choices, default=SubscriptionStatus.PENDING)
    price = models.DecimalField(**MONEY)
    currency = models.CharField(max_length=3, default="UZS")
    duration_months = models.PositiveSmallIntegerField()
    max_viewers = models.PositiveSmallIntegerField()
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    #: Written by the couple ("Click orqali to'ladim, chek …").
    user_note = models.CharField(max_length=500, blank=True)
    # Payment, recorded by the admin who approves.
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    paid_amount = models.DecimalField(**MONEY, null=True, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.CharField(max_length=500, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status", "ends_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"], condition=Q(status="PENDING"), name="subscriptions_one_pending_per_user"
            ),
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in SubscriptionStatus]), name="subscriptions_status_valid"
            ),
            models.CheckConstraint(
                condition=~Q(status="ACTIVE") | Q(starts_at__isnull=False, ends_at__isnull=False),
                name="subscriptions_active_has_period",
            ),
            models.CheckConstraint(
                condition=Q(paid_amount__isnull=True) | Q(paid_amount__gte=0), name="subscriptions_paid_non_negative"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.plan} ({self.status})"


class SubscriptionSettings(models.Model):
    """Singleton (pk=1): what the couple is told about paying (card number, recipient, phone)."""

    payment_instructions = models.TextField(max_length=2000, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return "Obuna to'lov ma'lumotlari"

    @classmethod
    def load(cls) -> "SubscriptionSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
