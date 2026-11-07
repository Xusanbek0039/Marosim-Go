"""Server-side RBAC.

* ``IsSuperAdmin`` — only SUPER_ADMIN (e.g. managing admins and their permissions).
* ``HasAdminPermission`` — SUPER_ADMIN always; ADMIN only with the permission code the view
  requires for the current action (see ``permissions_catalog``); every other role is denied.

Each class also describes itself through ``access_grant(view)`` — read by ``apps.accounts.access``
to publish the role metadata. Keep the two in sync: the contract tests call every endpoint as
every role and fail when the description and ``has_permission`` disagree.
"""

from rest_framework.permissions import BasePermission

from .models import Role

ACTION_SUFFIX = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "update",
    "partial_update": "update",
    "destroy": "delete",
}


def _is_staff_user(user) -> bool:
    return bool(user and user.is_authenticated and user.is_active and not user.is_deleted)


class IsSuperAdmin(BasePermission):
    message = "Bu amal faqat Super Admin uchun."

    def has_permission(self, request, view):
        user = request.user
        return _is_staff_user(user) and user.role == Role.SUPER_ADMIN

    def access_grant(self, view):
        from .access import Grant

        return Grant(frozenset({Role.SUPER_ADMIN.value}))


class HasAdminPermission(BasePermission):
    """The view declares ``permission_module`` and optionally ``action_permissions`` overrides."""

    message = "Bu amal uchun ruxsatingiz yo'q."

    def has_permission(self, request, view):
        user = request.user
        if not _is_staff_user(user) or user.role not in (Role.SUPER_ADMIN, Role.ADMIN):
            return False
        code = self.required_code(view)
        if code is None:  # unknown action: super admin only
            return user.role == Role.SUPER_ADMIN
        return user.has_admin_permission(code)

    def access_grant(self, view):
        from .access import Grant

        code = self.required_code(view)
        if code is None:
            return Grant(frozenset({Role.SUPER_ADMIN.value}))
        return Grant(
            frozenset({Role.SUPER_ADMIN.value, Role.ADMIN.value}), requirements={Role.ADMIN.value: frozenset({code})}
        )

    @staticmethod
    def required_code(view) -> str | None:
        explicit = getattr(view, "required_permission", None)
        if explicit:
            return explicit
        action = getattr(view, "action", None)
        overrides = getattr(view, "action_permissions", {}) or {}
        if action in overrides:
            return overrides[action]
        suffix = ACTION_SUFFIX.get(action)
        module = getattr(view, "permission_module", None)
        return f"{module}.{suffix}" if module and suffix else None


def describe_access(view, method: str = "GET") -> dict:
    """Legacy ``x-access`` shape (kept for existing clients); see ``apps.accounts.access`` for the full policy."""
    from .access import resolve

    return legacy_access(resolve(view, method))


def legacy_access(policy) -> dict:
    return {
        "auth_required": not policy.is_public,
        "roles": list(policy.allowed_roles),
        "permission": policy.required_permissions[0] if policy.required_permissions else None,
        "label": policy.label,
    }
