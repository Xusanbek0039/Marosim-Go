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

from .models import PlanAudience, Subscription, SubscriptionPlan, SubscriptionStatus

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
        user=user,
        studio__isnull=True,
        venue__isnull=True,
        status=SubscriptionStatus.ACTIVE,
        starts_at__lte=at,
        ends_at__gt=at,
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


def target_filter(user, studio=None, venue=None) -> dict:
    if studio is not None:
        return {"studio": studio}
    if venue is not None:
        return {"venue": venue}
    return {"user": user, "studio__isnull": True, "venue__isnull": True}


def paid_until(user, studio=None, venue=None) -> datetime.datetime | None:
    """End of the last queued ACTIVE period (renewals stack after it)."""
    last = (
        Subscription.objects.filter(
            **target_filter(user, studio, venue), status=SubscriptionStatus.ACTIVE, ends_at__gt=timezone.now()
        )
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


def ensure_target(user, plan, studio=None, venue=None) -> None:
    """A business purchase belongs to one business, never to all businesses of a payer."""
    if not user or not user.is_active or user.is_deleted:
        raise ValidationError({"user_id": ["Faol hisob talab qilinadi."]})
    if plan.audience == PlanAudience.USER:
        _ensure_client(user)
        valid = studio is None and venue is None
    elif plan.audience == PlanAudience.STUDIO:
        valid = (
            user.role == Role.STUDIO
            and studio is not None
            and venue is None
            and studio.is_active
            and not studio.is_deleted
            and studio.responsible_user_id == user.pk
        )
    else:
        from apps.venues.models import MembershipRole

        valid = (
            user.role == Role.VENUE_OWNER
            and venue is not None
            and studio is None
            and venue.is_active
            and not venue.is_deleted
            and venue.memberships.filter(user=user, is_active=True, role=MembershipRole.OWNER).exists()
        )
    if not valid:
        raise ValidationError({"plan": ["Tarif turiga mos, o'zingizga tegishli studiya yoki to'yxonani tanlang."]})


def business_verified(*, studio=None, venue=None) -> bool:
    if studio is None and venue is None:
        return False
    target = studio if studio is not None else venue
    if not target.is_active or target.is_deleted:
        return False
    now = timezone.now()
    return Subscription.objects.filter(
        **target_filter(None, studio, venue), status=SubscriptionStatus.ACTIVE, starts_at__lte=now, ends_at__gt=now
    ).exists()


def _terms(plan: SubscriptionPlan) -> dict:
    return {
        "plan": plan,
        "price": plan.price,
        "currency": plan.currency,
        "duration_months": plan.duration_months,
        "max_viewers": plan.max_viewers,
    }


@transaction.atomic
def request_subscription(
    request, user, plan: SubscriptionPlan, user_note: str = "", *, studio=None, venue=None
) -> Subscription:
    _lock_target(user, studio, venue)
    ensure_target(user, plan, studio, venue)
    if not plan.is_active:
        raise ValidationError({"plan": ["Bu tarif hozir sotuvda emas."]})
    if Subscription.objects.filter(**target_filter(user, studio, venue), status=SubscriptionStatus.PENDING).exists():
        raise ValidationError({"plan": ["Sizda tasdiq kutayotgan so'rov bor. Avval uni bekor qiling."]})
    sub = Subscription.objects.create(user=user, studio=studio, venue=venue, user_note=user_note, **_terms(plan))
    record(request, AuditAction.CREATE, sub, changes={"plan": plan.code, "price": str(plan.price)})
    return sub


def _activate(sub: Subscription, by, payment: dict) -> None:
    now = timezone.now()
    starts = max(now, paid_until(sub.user, sub.studio, sub.venue) or now)
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
    _lock_target(sub.user, sub.studio, sub.venue)
    ensure_target(sub.user, sub.plan, sub.studio, sub.venue)
    _activate(sub, request.user, payment)
    sub.save()
    record(
        request, AuditAction.UPDATE, sub, changes={"status": ["PENDING", "ACTIVE"], "ends_at": sub.ends_at.isoformat()}
    )
    return sub


@transaction.atomic
def grant(request, user, plan: SubscriptionPlan, *, studio=None, venue=None, **payment) -> Subscription:
    """An admin sells a subscription directly (e.g. paid in cash at the office)."""
    _lock_target(user, studio, venue)
    ensure_target(user, plan, studio, venue)
    if not plan.is_active:
        raise ValidationError({"plan": ["Bu tarif hozir sotuvda emas."]})
    sub = Subscription(user=user, studio=studio, venue=venue, user_note="", **_terms(plan))
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


def _lock_target(user, studio=None, venue=None) -> None:
    """Serialise period stacking for one user (two approvals cannot both start 'now')."""
    from apps.accounts.models import User

    target = studio if studio is not None else venue
    if target is not None:
        type(target).objects.select_for_update().get(pk=target.pk)
    else:
        User.objects.select_for_update().get(pk=user.pk)
