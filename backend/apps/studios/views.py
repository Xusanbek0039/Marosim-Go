import django_filters
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.access import AccessNote
from apps.accounts.permissions import HasAdminPermission
from apps.audit.services import AuditAction, diff, record, snapshot

from . import services
from .models import MAX_PORTFOLIO_IMAGES, Studio, StudioImage
from .serializers import (
    StudioCalendarEntrySerializer,
    StudioImageSerializer,
    StudioImageUploadSerializer,
    StudioSerializer,
)
from .services import sync_owner_membership

AUDITED_FIELDS = [
    "name",
    "description",
    "profile_picture",
    "address",
    "phone_number",
    "responsible_user",
    "is_active",
]
UUID_RE = r"[0-9a-fA-F-]{36}"


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
    action_permissions = {"calendar": "studios.view", "images": "studios.update", "delete_image": "studios.update"}
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    access_notes = {
        "*": AccessNote(ownership="Barcha o'chirilmagan studiyalar (get_queryset); STUDIO roli kira olmaydi."),
        "images": AccessNote(conditions=(f"Ko'pi bilan {MAX_PORTFOLIO_IMAGES} ta rasm, har biri 5 MB gacha",)),
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
        return (
            Studio.objects.filter(deleted_at__isnull=True).select_related("responsible_user").prefetch_related("images")
        )

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

    # ---------------------------------------------------------- calendar
    @extend_schema(
        summary="Studiya jadvali: oraliqdagi marosimlar (panel)",
        parameters=[
            OpenApiParameter("from", OpenApiTypes.DATE, required=True),
            OpenApiParameter("to", OpenApiTypes.DATE, required=True, description="Ko'pi bilan 62 kun."),
        ],
        responses=StudioCalendarEntrySerializer(many=True),
    )
    @action(detail=True, methods=["get"], pagination_class=None, filter_backends=[])
    def calendar(self, request, pk=None):
        from apps.ceremonies.models import Ceremony  # ceremonies → studios: lazy import
        from apps.venues.scheduling import parse_range

        studio = self.get_object()
        start, end = parse_range(request.query_params)
        rows = Ceremony.objects.filter(studio=studio, event_date__gte=start, event_date__lte=end).order_by(
            "event_date", "created_at"
        )
        return Response(StudioCalendarEntrySerializer(rows, many=True).data)

    # --------------------------------------------------------- portfolio
    @extend_schema(
        summary="Portfolioga rasm qo'shish (panel)",
        request={"multipart/form-data": StudioImageUploadSerializer},
        responses={201: StudioImageSerializer},
    )
    @action(detail=True, methods=["post"], filter_backends=[])
    def images(self, request, pk=None):
        studio = self.get_object()
        upload = StudioImageUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        image = services.add_portfolio_image(request, studio, upload.validated_data["image"])
        return Response(StudioImageSerializer(image, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Portfoliodan rasmni o'chirish (panel)", responses={204: None})
    @action(
        detail=True,
        methods=["delete"],
        url_path=rf"images/(?P<image_id>{UUID_RE})",
        url_name="delete-image",
        filter_backends=[],
    )
    def delete_image(self, request, pk=None, image_id=None):
        studio = self.get_object()
        services.delete_portfolio_image(request, get_object_or_404(StudioImage, pk=image_id, studio=studio))
        return Response(status=status.HTTP_204_NO_CONTENT)
