import django_filters
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from apps.accounts.access import AccessNote
from apps.accounts.permissions import HasAdminPermission
from apps.audit.services import AuditAction, diff, record, snapshot

from .models import Studio
from .serializers import StudioSerializer
from .services import sync_owner_membership

AUDITED_FIELDS = ["name", "description", "profile_picture", "address", "responsible_user", "is_active"]


class StudioFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter()
    responsible_user = django_filters.UUIDFilter(field_name="responsible_user_id")
    created_after = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Studio
        fields = ["is_active", "responsible_user", "created_after", "created_before"]


@extend_schema_view(
    list=extend_schema(summary="Studiyalar ro'yxati"),
    create=extend_schema(summary="Studiya qo'shish"),
    retrieve=extend_schema(summary="Studiya ma'lumotlari"),
    partial_update=extend_schema(summary="Studiyani tahrirlash"),
    destroy=extend_schema(summary="Studiyani o'chirish (soft delete)"),
)
class StudioViewSet(viewsets.ModelViewSet):
    """Panel management of studios. Not the STUDIO role's own API (that comes with StudioMembership)."""

    serializer_class = StudioSerializer
    permission_classes = [HasAdminPermission]
    permission_module = "studios"
    access_notes = {
        "*": AccessNote(ownership="Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi.")
    }
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filterset_class = StudioFilter
    search_fields = [
        "name",
        "address",
        "responsible_user__first_name",
        "responsible_user__last_name",
        "responsible_user__email",
    ]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Studio.objects.filter(deleted_at__isnull=True).select_related("responsible_user")

    @transaction.atomic
    def perform_create(self, serializer):
        studio = serializer.save()
        sync_owner_membership(studio)
        record(self.request, AuditAction.CREATE, studio, changes=snapshot(studio, AUDITED_FIELDS))

    @transaction.atomic
    def perform_update(self, serializer):
        before = snapshot(serializer.instance, AUDITED_FIELDS)
        was_active = serializer.instance.is_active
        previous_owner_id = serializer.instance.responsible_user_id
        studio = serializer.save()
        sync_owner_membership(studio, previous_owner_id)
        changes = diff(before, snapshot(studio, AUDITED_FIELDS))
        if was_active != studio.is_active:
            record(self.request, AuditAction.ACTIVATE if studio.is_active else AuditAction.DEACTIVATE, studio)
            changes.pop("is_active", None)
        if changes:
            record(self.request, AuditAction.UPDATE, studio, changes=changes)

    @transaction.atomic
    def perform_destroy(self, instance):
        instance.soft_delete()
        record(self.request, AuditAction.DELETE, instance)
