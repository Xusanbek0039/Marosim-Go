from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.audit.services import AuditAction, diff, record, snapshot
from apps.core.exceptions import Conflict

from . import permissions_catalog as catalog
from .access import AccessNote
from .filters import AdminFilter, ManagedUserFilter
from .models import CLIENT_ROLES, Role, User
from .permissions import HasAdminPermission, IsSuperAdmin
from .phone_verification import mark_verified
from .serializers import AdminSerializer, ManagedUserSerializer, PermissionDefSerializer, PinflRevealSerializer
from .tokens import revoke_all_sessions

AUDITED_FIELDS = [
    "phone_number",
    "email",
    "first_name",
    "last_name",
    "profile_picture",
    "address",
    "role",
    "is_active",
    "admin_permissions",
]


class ManagedUserViewSetBase(viewsets.ModelViewSet):
    """Shared CRUD for panel-managed accounts. DELETE is a soft delete."""

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    managed_roles: tuple[str, ...] = ()
    search_fields = ["first_name", "last_name", "phone_number", "email", "address"]
    ordering_fields = ["created_at", "updated_at", "first_name", "last_name", "phone_number", "email", "last_login"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return User.objects.alive().filter(role__in=self.managed_roles)

    @transaction.atomic
    def perform_create(self, serializer):
        user = serializer.save()
        record(self.request, AuditAction.CREATE, user, changes=snapshot(user, AUDITED_FIELDS))

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        before = snapshot(instance, AUDITED_FIELDS)
        was_active = instance.is_active
        touched = {f for f in ("password", "pinfl") if f in serializer.validated_data}

        user = serializer.save()
        after = snapshot(user, AUDITED_FIELDS)

        if was_active and not user.is_active:
            self._ensure_not_studio_owner(user, "Nofaol qilish")
            revoke_all_sessions(user)
            record(self.request, AuditAction.DEACTIVATE, user)
        elif not was_active and user.is_active:
            record(self.request, AuditAction.ACTIVATE, user)
        if "password" in touched or before.get("phone_number") != after.get("phone_number"):
            # New credentials or a new login identifier: every existing session must sign in again.
            revoke_all_sessions(user)
        if before.get("admin_permissions") != after.get("admin_permissions"):
            record(
                self.request,
                AuditAction.PERMISSIONS_CHANGE,
                user,
                changes={"from": before.get("admin_permissions"), "to": after.get("admin_permissions")},
            )

        changes = diff(before, after, touched)
        changes.pop("is_active", None)
        changes.pop("admin_permissions", None)
        if changes:
            record(self.request, AuditAction.UPDATE, user, changes=changes)

    @transaction.atomic
    def perform_destroy(self, instance):
        self._ensure_not_studio_owner(instance, "O'chirish")
        instance.soft_delete()
        revoke_all_sessions(instance)
        record(self.request, AuditAction.DELETE, instance)

    @staticmethod
    def _ensure_not_studio_owner(user, verb: str) -> None:
        if user.responsible_studios.filter(deleted_at__isnull=True, is_active=True).exists():
            raise Conflict(
                f"{verb} mumkin emas: bu shaxs faol studiyaning mas'ul shaxsi. Avval studiyani boshqa shaxsga "
                "biriktiring yoki nofaol qiling."
            )

    def _reveal_pinfl(self, request):
        user = self.get_object()
        value = user.get_pinfl()
        record(request, AuditAction.PINFL_REVEAL, user)
        return Response(PinflRevealSerializer({"pinfl": value or ""}).data)

    @extend_schema(request=None, responses=ManagedUserSerializer, summary="Telefon raqamini qo'lda tasdiqlash")
    @action(detail=True, methods=["post"], url_path="verify-phone")
    @transaction.atomic
    def verify_phone(self, request, pk=None):
        user = self.get_object()
        user = User.objects.select_for_update().get(pk=user.pk)
        if not user.phone_number:
            raise ValidationError({"phone_number": ["Avval telefon raqamini kiriting."]})
        if not user.is_phone_verified:
            mark_verified(user)
            record(request, AuditAction.UPDATE, user, changes={"is_phone_verified": {"from": False, "to": True}})
        return Response(self.get_serializer(user).data)


@extend_schema_view(
    list=extend_schema(summary="Mijozlar ro'yxati (USER, STUDIO)"),
    create=extend_schema(summary="Mijoz qo'shish"),
    retrieve=extend_schema(summary="Mijoz ma'lumotlari"),
    partial_update=extend_schema(summary="Mijozni tahrirlash"),
    destroy=extend_schema(summary="Mijozni o'chirish (soft delete)"),
)
class UserViewSet(ManagedUserViewSetBase):
    """Clients of the platform: USER and STUDIO accounts."""

    managed_roles = tuple(r.value for r in CLIENT_ROLES)
    serializer_class = ManagedUserSerializer
    filterset_class = ManagedUserFilter
    permission_classes = [HasAdminPermission]
    permission_module = "users"
    action_permissions = {"pinfl": "users.view_pinfl", "verify_phone": "users.update"}
    access_notes = {
        "*": AccessNote(
            ownership="Faqat USER va STUDIO rolidagi, o'chirilmagan hisoblar (get_queryset). "
            "ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404)."
        ),
        "pinfl": AccessNote(conditions=("Har bir ko'rish audit qilinadi (PINFL_REVEAL)", "Throttle: pinfl_reveal")),
        "destroy": AccessNote(conditions=("Faol studiyaning mas'ul shaxsini o'chirib bo'lmaydi (409 conflict)",)),
    }

    @extend_schema(responses=PinflRevealSerializer, summary="To'liq JSHSHIR (audit qilinadi)")
    @action(detail=True, methods=["get"])
    def pinfl(self, request, pk=None):
        return self._reveal_pinfl(request)

    def get_throttles(self):
        if self.action == "pinfl":
            self.throttle_scope = "pinfl_reveal"
            return [*super().get_throttles(), ScopedRateThrottle()]
        return super().get_throttles()


@extend_schema_view(
    list=extend_schema(summary="Adminlar ro'yxati"),
    create=extend_schema(summary="Admin qo'shish"),
    retrieve=extend_schema(summary="Admin ma'lumotlari"),
    partial_update=extend_schema(summary="Adminni tahrirlash (ruxsatlar bilan)"),
    destroy=extend_schema(summary="Adminni o'chirish (soft delete)"),
)
class AdminViewSet(ManagedUserViewSetBase):
    """ADMIN accounts and their granular permissions — Super Admin only."""

    managed_roles = (Role.ADMIN.value,)
    serializer_class = AdminSerializer
    filterset_class = AdminFilter
    permission_classes = [IsSuperAdmin]
    access_notes = {
        "*": AccessNote(ownership="Faqat ADMIN rolidagi, o'chirilmagan hisoblar (get_queryset)."),
        "permissions": AccessNote(ownership=""),
        "pinfl": AccessNote(conditions=("Har bir ko'rish audit qilinadi (PINFL_REVEAL)",)),
    }

    @extend_schema(responses=PermissionDefSerializer(many=True), summary="Adminlarga beriladigan ruxsatlar ro'yxati")
    @action(detail=False, methods=["get"], pagination_class=None, filter_backends=[])
    def permissions(self, request):
        data = [
            {"code": p.code, "module": p.module, "module_label": catalog.MODULE_LABELS[p.module], "label": p.label}
            for p in catalog.ADMIN_PERMISSIONS
        ]
        return Response(PermissionDefSerializer(data, many=True).data, status=status.HTTP_200_OK)

    @extend_schema(responses=PinflRevealSerializer, summary="Adminning to'liq JSHSHIRi (audit qilinadi)")
    @action(detail=True, methods=["get"])
    def pinfl(self, request, pk=None):
        return self._reveal_pinfl(request)
