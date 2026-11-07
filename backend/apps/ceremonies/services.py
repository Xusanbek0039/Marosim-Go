"""Studio-side ceremony scoping (which studio member sees / manages which ceremony).

Couple / guest access lives in ``ownership.py`` (rules) and ``invitations.py`` (flows).
"""

from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Role
from apps.studios.models import StudioMembership
from apps.studios.services import active_memberships

from .models import Ceremony


# ------------------------------------------------------------------- scoping
def studio_ids(user, managing_only: bool = False) -> list:
    qs = active_memberships(user)
    if managing_only:
        qs = qs.filter(role__in=StudioMembership.MANAGING_ROLES)
    return list(qs.values_list("studio_id", flat=True))


def ceremonies_for(user):
    """Ceremonies a studio member or super admin may see (others: none)."""
    qs = Ceremony.objects.select_related("studio")
    if user.role == Role.SUPER_ADMIN:
        return qs
    if user.role == Role.STUDIO:
        return qs.filter(studio_id__in=studio_ids(user))
    return qs.none()


def can_manage(user, ceremony: Ceremony) -> bool:
    if user.role == Role.SUPER_ADMIN:
        return True
    return user.role == Role.STUDIO and ceremony.studio_id in studio_ids(user, managing_only=True)


def ensure_can_manage(user, ceremony: Ceremony) -> None:
    if not can_manage(user, ceremony):
        raise PermissionDenied("Bu marosimni boshqarish uchun studiyada OWNER yoki MANAGER bo'lishingiz kerak.")
