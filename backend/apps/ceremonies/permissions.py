"""Role gates for studio- and couple-facing endpoints.

These only decide *who may call* an endpoint. *Which rows* they see is enforced by each view's
``get_queryset`` (studio membership / participation) and documented in ``access_notes``.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.models import Role


def _alive(user) -> bool:
    return bool(user and user.is_authenticated and user.is_active and not user.is_deleted)


def is_studio_member(user) -> bool:
    """Role gate only. Membership decides *data* scope in each view's queryset (no membership →
    empty lists / 404), which keeps ``has_permission`` aligned with the documented roles."""
    return _alive(user) and user.role == Role.STUDIO


class IsStudioMember(BasePermission):
    message = "Bu amal faqat studiya hisoblari uchun."

    def has_permission(self, request, view):
        return is_studio_member(request.user)

    def access_grant(self, view):
        from apps.accounts.access import Grant

        return Grant(frozenset({Role.STUDIO.value}))


class IsStudioMemberOrSuperAdmin(BasePermission):
    message = "Bu amal faqat studiya a'zolari yoki Super Admin uchun."

    def has_permission(self, request, view):
        user = request.user
        return (_alive(user) and user.role == Role.SUPER_ADMIN) or is_studio_member(user)

    def access_grant(self, view):
        from apps.accounts.access import Grant

        return Grant(frozenset({Role.STUDIO.value, Role.SUPER_ADMIN.value}))


class IsClientUser(BasePermission):
    """Couples and guests: accounts with the USER role."""

    message = "Bu bo'lim faqat foydalanuvchilar uchun."

    def has_permission(self, request, view):
        user = request.user
        return _alive(user) and user.role == Role.USER

    def access_grant(self, view):
        from apps.accounts.access import Grant

        return Grant(frozenset({Role.USER.value}))
