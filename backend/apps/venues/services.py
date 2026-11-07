"""Venue access rules and write paths in one place (views stay thin, tests target these).

Scope: a venue-side account sees only venues it has an *active* membership in; anything else is
a 404 (``venues_for``), so a foreign venue's existence is never confirmed. Actions inside a venue
are decided by the membership's capabilities (``models.CAPABILITIES``). A venue blocked by an
admin (``is_active=False``) stays readable for its members but cannot be changed by them.
"""

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import Role
from apps.audit.services import AuditAction, diff, record, snapshot

from .models import Capability, MembershipRole, Venue, VenueHall, VenueMembership

VENUE_AUDITED_FIELDS = [
    "name",
    "description",
    "venue_type",
    "address",
    "region",
    "district",
    "latitude",
    "longitude",
    "phone_number",
    "cover_image",
    "capacity_min",
    "capacity_max",
    "base_price",
    "currency",
    "is_active",
    "publication_status",
]
HALL_AUDITED_FIELDS = ["venue", "name", "capacity", "base_price", "is_active"]
MEMBERSHIP_AUDITED_FIELDS = ["venue", "user", "role", "is_active"]
DEFAULT_HALL_NAME = "Asosiy zal"


def _alive(user) -> bool:
    return bool(user and user.is_authenticated and user.is_active and not user.is_deleted)


# ------------------------------------------------------------------- scoping
def active_memberships(user):
    """Memberships that grant venue-side access right now (blocked venues included, read-only)."""
    if not _alive(user) or user.role != Role.VENUE_OWNER:
        return VenueMembership.objects.none()
    return VenueMembership.objects.filter(user=user, is_active=True, venue__deleted_at__isnull=True).select_related(
        "venue"
    )


def venues_for(user):
    """Venues a venue-side account may see (others: none)."""
    ids = active_memberships(user).values("venue_id")
    return Venue.objects.filter(pk__in=ids, deleted_at__isnull=True)


def membership_of(user, venue: Venue) -> VenueMembership | None:
    return active_memberships(user).filter(venue=venue).first()


def capabilities_for(user, venue: Venue) -> frozenset[str]:
    membership = membership_of(user, venue)
    if membership is None:
        return frozenset()
    if not venue.is_active:  # blocked by an admin: members may only look
        return membership.capabilities & {Capability.VIEW}
    return membership.capabilities


def has_capability(user, venue: Venue, capability: str) -> bool:
    return capability in capabilities_for(user, venue)


def ensure_capability(user, venue: Venue, capability: str) -> None:
    if has_capability(user, venue, capability):
        return
    if not venue.is_active and membership_of(user, venue) is not None:
        raise PermissionDenied("To'yxona administrator tomonidan bloklangan — o'zgartirish mumkin emas.")
    raise PermissionDenied("To'yxonadagi rolingiz bu amalga ruxsat bermaydi.")


# -------------------------------------------------------------- write paths
@transaction.atomic
def create_venue(request, owner, **data) -> Venue:
    """Create a PRIVATE venue with ``owner`` as its OWNER member and a default hall."""
    if not _alive(owner) or owner.role != Role.VENUE_OWNER:
        raise ValidationError({"owner": ["Egasi faol VENUE_OWNER rolidagi foydalanuvchi bo'lishi kerak."]})
    data.pop("publication_status", None)  # only the publication workflow changes it
    data.pop("is_active", None)  # only admins block / unblock
    venue = Venue.objects.create(**data)
    VenueMembership.objects.create(venue=venue, user=owner, role=MembershipRole.OWNER)
    hall = VenueHall.objects.create(venue=venue, name=DEFAULT_HALL_NAME, capacity=venue.capacity_max)
    record(request, AuditAction.CREATE, venue, changes=snapshot(venue, VENUE_AUDITED_FIELDS))
    record(request, AuditAction.CREATE, hall, changes=snapshot(hall, HALL_AUDITED_FIELDS))
    return venue


def _lock(venue: Venue) -> Venue:
    """Serialize membership changes of one venue (``SELECT … FOR UPDATE`` on PostgreSQL)."""
    return Venue.objects.select_for_update().get(pk=venue.pk)


def _active_owner_count(venue: Venue, exclude_pk=None) -> int:
    qs = VenueMembership.objects.filter(venue=venue, role=MembershipRole.OWNER, is_active=True)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs.count()


@transaction.atomic
def add_member(request, venue: Venue, user, role: str) -> VenueMembership:
    """Add (or re-activate) a member. Only active VENUE_OWNER accounts can work for a venue."""
    if role not in MembershipRole.values:
        raise ValidationError({"role": ["Noma'lum a'zolik roli."]})
    if not _alive(user) or user.role != Role.VENUE_OWNER:
        raise ValidationError({"user": ["Foydalanuvchi faol VENUE_OWNER rolidagi hisob bo'lishi kerak."]})
    _lock(venue)
    membership, created = VenueMembership.objects.get_or_create(
        venue=venue, user=user, defaults={"role": role, "is_active": True}
    )
    if created:
        record(request, AuditAction.CREATE, membership, changes=snapshot(membership, MEMBERSHIP_AUDITED_FIELDS))
        return membership
    return update_member(request, membership, role=role, is_active=True)


@transaction.atomic
def update_member(request, membership: VenueMembership, *, role: str | None = None, is_active: bool | None = None):
    """Change a member's role / activity; a venue never loses its last active OWNER."""
    _lock(membership.venue)
    membership.refresh_from_db()
    before = snapshot(membership, MEMBERSHIP_AUDITED_FIELDS)
    new_role = role if role is not None else membership.role
    new_active = is_active if is_active is not None else membership.is_active
    if new_role not in MembershipRole.values:
        raise ValidationError({"role": ["Noma'lum a'zolik roli."]})
    stops_being_owner = membership.role == MembershipRole.OWNER and membership.is_active
    stops_being_owner = stops_being_owner and (new_role != MembershipRole.OWNER or not new_active)
    if stops_being_owner and _active_owner_count(membership.venue, exclude_pk=membership.pk) == 0:
        raise ValidationError({"role": ["To'yxonada kamida bitta faol OWNER qolishi kerak."]})
    membership.role, membership.is_active = new_role, new_active
    membership.save(update_fields=["role", "is_active", "updated_at"])
    changes = diff(before, snapshot(membership, MEMBERSHIP_AUDITED_FIELDS))
    if changes:
        record(request, AuditAction.UPDATE, membership, changes=changes)
    return membership
