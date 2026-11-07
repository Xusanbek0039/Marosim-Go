"""Role gate for venue-side endpoints.

Only decides *who may call* an endpoint (VENUE_OWNER accounts). *Which venues* they see and *what*
they may do there is decided per request by ``services`` (active membership + capabilities) and
documented in each view's ``access_notes``.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.models import Role


class IsVenueAccount(BasePermission):
    message = "Bu amal faqat to'yxona hisoblari uchun."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_active and not user.is_deleted and user.role == Role.VENUE_OWNER
        )

    def access_grant(self, view):
        from apps.accounts.access import Grant

        return Grant(frozenset({Role.VENUE_OWNER.value}))
