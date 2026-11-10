from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.audit.services import AuditAction, diff, record, snapshot
from apps.core.exceptions import Conflict

from apps.ceremonies.invitations import settle_user_ownerships
from apps.ceremonies.serializers import AccountFolderSerializer, FolderRenameSerializer, FolderResultSerializer

from . import features
from . import permissions_catalog as catalog
from .access import AccessNote
from .filters import AdminFilter, ManagedUserFilter
from .models import CLIENT_ROLES, Role, User
from .permissions import HasAdminPermission, IsSuperAdmin
from .phone_verification import mark_verified
from .serializers import (
    AccountFeatureSerializer,
    AccountFeaturesWriteSerializer,
    AdminSerializer,
    ManagedUserSerializer,
    PermissionDefSerializer,
    PinflRevealSerializer,
)
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

        if (was_active and not user.is_active) or (before.get("role") == Role.USER != user.role):
            settle_user_ownerships(user)  # their pending votes on owner requests stop counting

        changes = diff(before, after, touched)
        changes.pop("is_active", None)
        changes.pop("admin_permissions", None)
        if changes:
            record(self.request, AuditAction.UPDATE, user, changes=changes)

    @transaction.atomic
    def perform_destroy(self, instance):
        self._ensure_not_studio_owner(instance, "O'chirish")
        instance.soft_delete()
        settle_user_ownerships(instance)
        revoke_all_sessions(instance)
        record(self.request, AuditAction.DELETE, instance)

    @staticmethod
    def _ensure_not_studio_owner(user, verb: str) -> None:
        if user.venue_memberships.filter(
            is_active=True, role="OWNER", venue__deleted_at__isnull=True, venue__is_active=True
        ).exists():
            raise Conflict(
                f"{verb} mumkin emas: bu shaxs faol to'yxona egasi. Avval egalikni boshqa shaxsga o'tkazing."
            )
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
    list=extend_schema(summary="Mijozlar ro'yxati (USER, STUDIO, VENUE_OWNER)"),
    create=extend_schema(summary="Mijoz qo'shish"),
    retrieve=extend_schema(summary="Mijoz ma'lumotlari"),
    partial_update=extend_schema(summary="Mijozni tahrirlash"),
    destroy=extend_schema(summary="Mijozni o'chirish (soft delete)"),
)
class UserViewSet(ManagedUserViewSetBase):
    """Clients of the platform: USER, STUDIO and VENUE_OWNER accounts."""

    managed_roles = tuple(r.value for r in CLIENT_ROLES)
    serializer_class = ManagedUserSerializer
    filterset_class = ManagedUserFilter
    permission_classes = [HasAdminPermission]
    permission_module = "users"
    action_permissions = {
        "pinfl": "users.view_pinfl",
        "verify_phone": "users.update",
        "features": "platform.view",
        "set_features": "platform.manage",
        "folders": "users.view",
        "rename_folder": "users.update",
    }
    access_notes = {
        "*": AccessNote(
            ownership="Faqat USER, STUDIO va VENUE_OWNER rolidagi, o'chirilmagan hisoblar (get_queryset). "
            "ADMIN / SUPER_ADMIN hisoblari bu yerda ko'rinmaydi (404)."
        ),
        "pinfl": AccessNote(conditions=("Har bir ko'rish audit qilinadi (PINFL_REVEAL)", "Throttle: pinfl_reveal")),
        "destroy": AccessNote(conditions=("Faol studiyaning mas'ul shaxsini o'chirib bo'lmaydi (409 conflict)",)),
        "set_features": AccessNote(conditions=("Faqat shu hisob roliga tegishli imkoniyat kodlari",)),
        "folders": AccessNote(conditions=("Faqat USER: egasi yoki ko'ruvchisi bo'lgan marosimlar",)),
        "rename_folder": AccessNote(conditions=("Faqat shu hisob ochishi mumkin bo'lgan marosim; boshqasi 404",)),
    }

    @extend_schema(responses=PinflRevealSerializer, summary="To'liq JSHSHIR (audit qilinadi)")
    @action(detail=True, methods=["get"])
    def pinfl(self, request, pk=None):
        return self._reveal_pinfl(request)

    # -------------------------------------------- per-account capabilities
    @extend_schema(summary="Hisob imkoniyatlari (shu profil uchun)", responses=AccountFeatureSerializer(many=True))
    @action(detail=True, methods=["get"], pagination_class=None, filter_backends=[])
    def features(self, request, pk=None):
        return Response(AccountFeatureSerializer(features.account_catalog(self.get_object()), many=True).data)

    @extend_schema(
        summary="Hisob imkoniyatlarini yoqish / o'chirish",
        request=AccountFeaturesWriteSerializer,
        responses=AccountFeatureSerializer(many=True),
    )
    @features.mapping.patch
    @transaction.atomic
    def set_features(self, request, pk=None):
        user = User.objects.select_for_update().get(pk=self.get_object().pk)
        body = AccountFeaturesWriteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        allowed = set(features.account_codes(user))
        wrong = sorted(set(body.validated_data["disabled_features"]) - allowed)
        if wrong:
            raise ValidationError({"disabled_features": [f"Bu hisob roliga tegishli emas: {', '.join(wrong)}"]})
        before = user.disabled_features or []
        user.disabled_features = sorted(set(body.validated_data["disabled_features"]))
        user.save(update_fields=["disabled_features", "updated_at"])
        if before != user.disabled_features:
            record(request, AuditAction.UPDATE, user, changes={"disabled_features": {"from": before, "to": user.disabled_features}})
        return Response(AccountFeatureSerializer(features.account_catalog(user), many=True).data)

    # ------------------------------------------------- ceremony folders
    @extend_schema(summary="Foydalanuvchining marosim papkalari", responses=AccountFolderSerializer(many=True))
    @action(detail=True, methods=["get"], pagination_class=None, filter_backends=[])
    def folders(self, request, pk=None):
        from apps.ceremonies import folders as ceremony_folders

        user = self.get_object()
        rows = ceremony_folders.user_folders(user) if user.role == Role.USER else []
        return Response(AccountFolderSerializer(rows, many=True).data)

    @extend_schema(
        summary="Foydalanuvchi papkasi nomini o'zgartirish",
        request=FolderRenameSerializer,
        responses=FolderResultSerializer,
    )
    @action(detail=True, methods=["patch"], url_path=r"folders/(?P<ceremony_id>[0-9a-fA-F-]{36})")
    def rename_folder(self, request, pk=None, ceremony_id=None):
        from apps.ceremonies import folders as ceremony_folders
        from apps.ceremonies import ownership

        user = self.get_object()
        ceremony = ownership.accessible_ceremonies(user).filter(pk=ceremony_id).first() if user.role == Role.USER else None
        if ceremony is None:
            raise NotFound()
        body = FolderRenameSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        name = ceremony_folders.rename(request, user, ceremony, body.validated_data["name"])
        return Response({"folder_name": name or ceremony.title, "is_custom": bool(name)})

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
