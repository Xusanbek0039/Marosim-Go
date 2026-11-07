"""Server-side RBAC.

* ``IsSuperAdmin`` — only SUPER_ADMIN (e.g. managing admins and their permissions).
* ``HasAdminPermission`` — SUPER_ADMIN always; ADMIN only with the permission code the view
  requires for the current action (see ``permissions_catalog``); every other role is denied.
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


def describe_access(view) -> dict:
    """Machine-readable access rule of a view/action — published in OpenAPI as ``x-access``.

    Derived from the real permission classes, so the docs cannot drift from the enforcement.
    """
    from rest_framework.permissions import AllowAny, IsAuthenticated

    permissions = view.get_permissions() if hasattr(view, "get_permissions") else []
    authenticators = getattr(view, "authentication_classes", None)
    public = any(isinstance(p, AllowAny) for p in permissions) or authenticators == []
    access = {"auth_required": not public, "roles": [], "permission": None, "label": "Ochiq (public)"}
    if public:
        return access

    for perm in permissions:
        if isinstance(perm, IsSuperAdmin):
            return {**access, "roles": [Role.SUPER_ADMIN.value], "label": "Faqat SUPER_ADMIN"}
        if isinstance(perm, HasAdminPermission):
            code = HasAdminPermission.required_code(view)
            if code is None:
                return {**access, "roles": [Role.SUPER_ADMIN.value], "label": "Faqat SUPER_ADMIN"}
            return {
                **access,
                "roles": [Role.SUPER_ADMIN.value, Role.ADMIN.value],
                "permission": code,
                "label": f"SUPER_ADMIN yoki `{code}` ruxsatli ADMIN",
            }
        if isinstance(perm, IsAuthenticated):
            access = {**access, "label": "Har qanday tizimga kirgan foydalanuvchi"}
    return access
