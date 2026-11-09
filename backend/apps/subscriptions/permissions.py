from rest_framework.permissions import BasePermission

from apps.accounts.features import ensure_feature
from apps.accounts.models import CLIENT_ROLES


class IsSubscriberAccount(BasePermission):
    message = "Obuna faqat mijoz, studiya va to'yxona hisoblari uchun."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_active and not user.is_deleted and user.role in CLIENT_ROLES
        ) and ensure_feature(request, view)

    def access_grant(self, view):
        from apps.accounts.access import Grant

        return Grant(frozenset(role.value for role in CLIENT_ROLES))
