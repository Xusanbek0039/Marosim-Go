from rest_framework.permissions import BasePermission

from apps.accounts.features import ensure_feature

from .services import AUTHOR_ROLES


class IsSupportAuthor(BasePermission):
    """Every account except the Super Admin writes help tickets (admins write to the Super Admin)."""

    message = "Yordam xatlari Super Admin uchun emas: kelgan xatlar admin panelida."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_active and not user.is_deleted and user.role in AUTHOR_ROLES
        ) and ensure_feature(request, view)

    def access_grant(self, view):
        from apps.accounts.access import Grant

        return Grant(frozenset(role.value for role in AUTHOR_ROLES))
