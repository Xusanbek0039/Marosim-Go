"""Subscription rules and write paths. Media / sharing only ever call ``active_subscription`` /
``viewer_limit`` / ``has_clean_access``.

Periods: approving while the user already has a running subscription starts the new one when the
current one ends (renewal never loses paid days). A row is "running" when ACTIVE and
``starts_at <= now < ends_at``; expiry needs no job — it is computed.
"""

import calendar
import datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import Role
from apps.audit.services import AuditAction, record

from .models import Subscription, SubscriptionPlan, SubscriptionStatus

AUDITED = ["user", "plan", "status", "price", "starts_at", "ends_at", "paid_amount", "payment_method"]


def add_months(moment: datetime.datetime, months: int) -> datetime.datetime:
    """Calendar months (31 Jan + 1 month = 28/29 Feb)."""
    month_index = moment.month - 1 + months
    year, month = moment.year + month_index // 12, month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


# ---------------------------------------------------------------- reading
def running(user, at: datetime.datetime | None = None):
    at = at or timezone.now()
    return Subscription.objects.filter(
        user=user, status=SubscriptionStatus.ACTIVE, starts_at__lte=at, ends_at__gt=at
    ).order_by("-ends_at")


def active_subscription(user) -> Subscription | None:
    if not (user and getattr(user, "is_authenticated", False)):
        return None
    return running(user).first()


def has_clean_access(user) -> bool:
    """Originals without the logo + download — only while a subscription runs."""
    return active_subscription(user) is not None


def viewer_limit(user) -> int:
    """How many people this owner may share one ceremony with right now."""
    sub = active_subscription(user)
    free = settings.CEREMONY_MAX_VIEWERS_PER_OWNER
    return max(sub.max_viewers, free) if sub else free


def paid_until(user) -> datetime.datetime | None:
    """End of the last queued ACTIVE period (renewals stack after it)."""
    last = (
        Subscription.objects.filter(user=user, status=SubscriptionStatus.ACTIVE, ends_at__gt=timezone.now())
        .order_by("-ends_at")
        .values_list("ends_at", flat=True)
        .first()
    )
    return last


def state_of(sub: Subscription) -> str:
    """PENDING / ACTIVE / SCHEDULED / EXPIRED / REJECTED / CANCELLED (for display)."""
    if sub.status != SubscriptionStatus.ACTIVE:
        return sub.status
    now = timezone.now()
    if sub.ends_at <= now:
        return "EXPIRED"
    if sub.starts_at > now:
        return "SCHEDULED"
    return "ACTIVE"


# ----------------------------------------------------------------- writes
def _ensure_client(user) -> None:
    if not (user and user.is_active and not user.is_deleted and user.role == Role.USER):
        raise ValidationError({"user_id": ["Obuna faqat mijoz (USER) hisoblariga beriladi."]})


def _terms(plan: SubscriptionPlan) -> dict:
    return {
        "plan": plan,
        "price": plan.price,
        "currency": plan.currency,
        "duration_months": plan.duration_months,
        "max_viewers": plan.max_viewers,
    }


@transaction.atomic
def request_subscription(request, user, plan: SubscriptionPlan, user_note: str = "") -> Subscription:
    _ensure_client(user)
    if not plan.is_active:
        raise ValidationError({"plan": ["Bu tarif hozir sotuvda emas."]})
    if Subscription.objects.select_for_update().filter(user=user, status=SubscriptionStatus.PENDING).exists():
        raise ValidationError({"plan": ["Sizda tasdiq kutayotgan so'rov bor. Avval uni bekor qiling."]})
    sub = Subscription.objects.create(user=user, user_note=user_note, **_terms(plan))
    record(request, AuditAction.CREATE, sub, changes={"plan": plan.code, "price": str(plan.price)})
    return sub


def _activate(sub: Subscription, by, payment: dict) -> None:
    now = timezone.now()
    starts = max(now, paid_until(sub.user) or now)
    sub.status = SubscriptionStatus.ACTIVE
    sub.starts_at = starts
    sub.ends_at = add_months(starts, sub.duration_months)
    sub.payment_method = payment.get("payment_method") or sub.payment_method
    sub.paid_amount = payment["paid_amount"] if payment.get("paid_amount") is not None else sub.price
    sub.payment_reference = payment.get("payment_reference", "")
    sub.paid_at = payment.get("paid_at") or now
    sub.admin_note = payment.get("admin_note", sub.admin_note)
    sub.decided_by, sub.decided_at = by, now


@transaction.atomic
def approve(request, sub: Subscription, **payment) -> Subscription:
    sub = Subscription.objects.select_for_update().get(pk=sub.pk)
    if sub.status != SubscriptionStatus.PENDING:
        raise ValidationError({"status": ["Faqat kutilayotgan so'rovni tasdiqlash mumkin."]})
    _lock_user(sub.user_id)
    _activate(sub, request.user, payment)
    sub.save()
    record(
        request, AuditAction.UPDATE, sub, changes={"status": ["PENDING", "ACTIVE"], "ends_at": sub.ends_at.isoformat()}
    )
    return sub


@transaction.atomic
def grant(request, user, plan: SubscriptionPlan, **payment) -> Subscription:
    """An admin sells a subscription directly (e.g. paid in cash at the office)."""
    _ensure_client(user)
    _lock_user(user.pk)
    sub = Subscription(user=user, user_note="", **_terms(plan))
    _activate(sub, request.user, payment)
    sub.save()
    record(request, AuditAction.CREATE, sub, changes={"plan": plan.code, "status": "ACTIVE", "granted": True})
    return sub


@transaction.atomic
def reject(request, sub: Subscription, admin_note: str = "") -> Subscription:
    sub = Subscription.objects.select_for_update().get(pk=sub.pk)
    if sub.status != SubscriptionStatus.PENDING:
        raise ValidationError({"status": ["Faqat kutilayotgan so'rovni rad etish mumkin."]})
    sub.status, sub.decided_by, sub.decided_at = SubscriptionStatus.REJECTED, request.user, timezone.now()
    sub.admin_note = admin_note or sub.admin_note
    sub.save(update_fields=["status", "decided_by", "decided_at", "admin_note", "updated_at"])
    record(request, AuditAction.UPDATE, sub, changes={"status": ["PENDING", "REJECTED"]})
    return sub


@transaction.atomic
def cancel(request, sub: Subscription, *, by_user: bool, admin_note: str = "") -> Subscription:
    """The couple withdraws a PENDING request; an admin may also revoke an ACTIVE subscription."""
    sub = Subscription.objects.select_for_update().get(pk=sub.pk)
    allowed = {SubscriptionStatus.PENDING} if by_user else {SubscriptionStatus.PENDING, SubscriptionStatus.ACTIVE}
    if sub.status not in allowed:
        raise ValidationError({"status": ["Bu obunani bekor qilib bo'lmaydi."]})
    before = sub.status
    sub.status, sub.decided_at = SubscriptionStatus.CANCELLED, timezone.now()
    if not by_user:
        sub.decided_by, sub.admin_note = request.user, admin_note or sub.admin_note
    sub.save(update_fields=["status", "decided_by", "decided_at", "admin_note", "updated_at"])
    record(request, AuditAction.UPDATE, sub, changes={"status": [before, "CANCELLED"], "by_user": by_user})
    return sub


def _lock_user(user_id) -> None:
    """Serialise period stacking for one user (two approvals cannot both start 'now')."""
    from apps.accounts.models import User

    User.objects.select_for_update().filter(pk=user_id).first()
