import django_filters
from django.db import transaction
from rest_framework import viewsets

from apps.accounts.permissions import HasAdminPermission
from apps.audit.services import AuditAction, diff, record, snapshot

from .models import Studio
from .serializers import StudioSerializer

AUDITED_FIELDS = ["name", "profile_picture", "address", "responsible_user", "is_active"]


class StudioFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter()
    responsible_user = django_filters.UUIDFilter(field_name="responsible_user_id")
    created_after = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Studio
        fields = ["is_active", "responsible_user", "created_after", "created_before"]


class StudioViewSet(viewsets.ModelViewSet):
    serializer_class = StudioSerializer
    permission_classes = [HasAdminPermission]
    permission_module = "studios"
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
        record(self.request, AuditAction.CREATE, studio, changes=snapshot(studio, AUDITED_FIELDS))

    @transaction.atomic
    def perform_update(self, serializer):
        before = snapshot(serializer.instance, AUDITED_FIELDS)
        was_active = serializer.instance.is_active
        studio = serializer.save()
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
