"""Venue-owner endpoints (``/api/v1/venue-owner/…``) — mobile REST API for venue accounts.

Row scope lives in ``services.venues_for`` and is applied in ``get_queryset``: a venue without an
active membership of the caller is a 404, never a 403. Writes additionally need the matching
membership capability (``services.ensure_capability``).
"""

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.access import AccessNote
from apps.audit.services import AuditAction, diff, record, snapshot

from . import services
from .models import Capability, Venue, VenueHall, VenueImage, VenueMembership
from .permissions import IsVenueAccount
from .serializers import (
    OwnerVenueSerializer,
    VenueHallSerializer,
    VenueImageSerializer,
    VenueImageUploadSerializer,
    VenueMemberCreateSerializer,
    VenueMemberSerializer,
    VenueMemberUpdateSerializer,
)

VENUE_SCOPE = "Faqat so'rovchi faol a'zo (VenueMembership) bo'lgan, o'chirilmagan to'yxonalar; boshqalari 404."
BLOCKED = "Admin bloklagan to'yxona (is_active=false) a'zolar uchun faqat o'qiladi."
UUID_RE = "[0-9a-fA-F-]{36}"


def _needs(capability: str) -> str:
    return f"A'zolik roli `{capability}` imkoniyatiga ega bo'lishi shart (OWNER/MANAGER…, docs/VENUE_AVAILABILITY.md)."


@extend_schema_view(
    list=extend_schema(summary="Mening to'yxonalarim", tags=["venue-owner"]),
    create=extend_schema(summary="To'yxona yaratish (PRIVATE holatda)", tags=["venue-owner"]),
    retrieve=extend_schema(summary="To'yxona ma'lumotlari (egasi uchun)", tags=["venue-owner"]),
    partial_update=extend_schema(summary="To'yxonani tahrirlash", tags=["venue-owner"]),
)
class VenueOwnerVenueViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OwnerVenueSerializer
    queryset = Venue.objects.none()  # typing only; real rows come from get_queryset
    permission_classes = [IsVenueAccount]
    lookup_value_regex = UUID_RE
    #: delete = gallery images only (there is no destroy mixin: a venue itself cannot be deleted here)
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    search_fields = ["name", "address", "district"]
    ordering_fields = ["name", "created_at", "base_price", "capacity_max"]
    ordering = ["-created_at"]
    access_notes = {
        "*": AccessNote(ownership=VENUE_SCOPE),
        "create": AccessNote(
            ownership="",
            conditions=(
                "Yaratuvchi OWNER a'zo bo'ladi; standart 'Asosiy zal' ochiladi.",
                "publication_status=PRIVATE, is_active — faqat admin o'zgartiradi.",
            ),
        ),
        "partial_update": AccessNote(conditions=(_needs(Capability.EDIT_PROFILE), BLOCKED)),
        "halls": AccessNote(conditions=("POST: " + _needs(Capability.MANAGE_HALLS), BLOCKED)),
        "update_hall": AccessNote(conditions=(_needs(Capability.MANAGE_HALLS), BLOCKED)),
        "members": AccessNote(
            conditions=(
                _needs(Capability.MANAGE_MEMBERS),
                BLOCKED,
                "POST: faqat faol VENUE_OWNER hisobi (telefon bo'yicha); topilmasa — bitta umumiy xato.",
                "Throttle: venue_member_add",
            )
        ),
        "images": AccessNote(
            conditions=(
                "POST: " + _needs(Capability.EDIT_PROFILE),
                BLOCKED,
                f"Ko'pi bilan {services.MAX_GALLERY_IMAGES} ta rasm, har biri 5 MB gacha (JPG/PNG/WEBP)",
            )
        ),
        "delete_image": AccessNote(conditions=(_needs(Capability.EDIT_PROFILE), BLOCKED)),
        "update_member": AccessNote(
            conditions=(_needs(Capability.MANAGE_MEMBERS), BLOCKED, "Oxirgi faol OWNER olib tashlanmaydi.")
        ),
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Venue.objects.none()
        halls = Prefetch("halls", queryset=VenueHall.objects.filter(deleted_at__isnull=True))
        return services.venues_for(self.request.user).prefetch_related(halls, "images")

    def get_throttles(self):
        if self.action == "members" and self.request.method == "POST":
            self.throttle_scope = "venue_member_add"
            return [*super().get_throttles(), ScopedRateThrottle()]
        return super().get_throttles()

    def perform_create(self, serializer):
        serializer.instance = services.create_venue(self.request, self.request.user, **serializer.validated_data)

    @transaction.atomic
    def perform_update(self, serializer):
        services.ensure_capability(self.request.user, serializer.instance, Capability.EDIT_PROFILE)
        before = snapshot(serializer.instance, services.VENUE_AUDITED_FIELDS)
        venue = serializer.save()
        changes = diff(before, snapshot(venue, services.VENUE_AUDITED_FIELDS))
        if changes:
            record(self.request, AuditAction.UPDATE, venue, changes=changes)

    # ------------------------------------------------------------- halls
    @extend_schema(
        methods=["GET"], summary="To'yxona zallari", tags=["venue-owner"], responses=VenueHallSerializer(many=True)
    )
    @extend_schema(
        methods=["POST"],
        summary="Zal qo'shish",
        tags=["venue-owner"],
        request=VenueHallSerializer,
        responses={201: VenueHallSerializer},
    )
    @action(detail=True, methods=["get", "post"], pagination_class=None, filter_backends=[])
    def halls(self, request, pk=None):
        venue = self.get_object()
        if request.method == "GET":
            rows = venue.halls.filter(deleted_at__isnull=True)
            return Response(VenueHallSerializer(rows, many=True, context={"venue": venue}).data)
        services.ensure_capability(request.user, venue, Capability.MANAGE_HALLS)
        serializer = VenueHallSerializer(data=request.data, context={"venue": venue})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            hall = serializer.save(venue=venue)
            record(request, AuditAction.CREATE, hall, changes=snapshot(hall, services.HALL_AUDITED_FIELDS))
        return Response(VenueHallSerializer(hall, context={"venue": venue}).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Zalni tahrirlash", tags=["venue-owner"], request=VenueHallSerializer, responses=VenueHallSerializer
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path=rf"halls/(?P<hall_id>{UUID_RE})",
        url_name="update-hall",
        filter_backends=[],
    )
    def update_hall(self, request, pk=None, hall_id=None):
        venue = self.get_object()
        hall = get_object_or_404(VenueHall, pk=hall_id, venue=venue, deleted_at__isnull=True)
        services.ensure_capability(request.user, venue, Capability.MANAGE_HALLS)
        serializer = VenueHallSerializer(hall, data=request.data, partial=True, context={"venue": venue})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            before = snapshot(hall, services.HALL_AUDITED_FIELDS)
            hall = serializer.save()
            changes = diff(before, snapshot(hall, services.HALL_AUDITED_FIELDS))
            if changes:
                record(request, AuditAction.UPDATE, hall, changes=changes)
        return Response(VenueHallSerializer(hall, context={"venue": venue}).data)

    # ----------------------------------------------------------- members
    @extend_schema(
        methods=["GET"],
        summary="To'yxona a'zolari",
        tags=["venue-owner"],
        responses=VenueMemberSerializer(many=True),
    )
    @extend_schema(
        methods=["POST"],
        summary="A'zo qo'shish (telefon raqam bo'yicha)",
        tags=["venue-owner"],
        request=VenueMemberCreateSerializer,
        responses={201: VenueMemberSerializer},
    )
    @action(detail=True, methods=["get", "post"], pagination_class=None, filter_backends=[])
    def members(self, request, pk=None):
        venue = self.get_object()
        services.ensure_capability(request.user, venue, Capability.MANAGE_MEMBERS)
        if request.method == "GET":
            rows = VenueMembership.objects.filter(venue=venue).select_related("user")
            return Response(VenueMemberSerializer(rows, many=True).data)
        serializer = VenueMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.add_member_by_phone(
            request, venue, serializer.validated_data["phone_number"], serializer.validated_data["role"]
        )
        return Response(VenueMemberSerializer(membership).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="A'zoning rolini / faolligini o'zgartirish",
        tags=["venue-owner"],
        request=VenueMemberUpdateSerializer,
        responses=VenueMemberSerializer,
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path=rf"members/(?P<membership_id>{UUID_RE})",
        url_name="update-member",
        filter_backends=[],
    )
    def update_member(self, request, pk=None, membership_id=None):
        venue = self.get_object()
        services.ensure_capability(request.user, venue, Capability.MANAGE_MEMBERS)
        membership = get_object_or_404(VenueMembership, pk=membership_id, venue=venue)
        serializer = VenueMemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.update_member(request, membership, **serializer.validated_data)
        return Response(VenueMemberSerializer(membership).data)

    # ----------------------------------------------------------- gallery
    @extend_schema(
        methods=["GET"], summary="Galereya rasmlari", tags=["venue-owner"], responses=VenueImageSerializer(many=True)
    )
    @extend_schema(
        methods=["POST"],
        summary="Galereyaga rasm qo'shish",
        tags=["venue-owner"],
        request={"multipart/form-data": VenueImageUploadSerializer},
        responses={201: VenueImageSerializer},
    )
    @action(detail=True, methods=["get", "post"], pagination_class=None, filter_backends=[])
    def images(self, request, pk=None):
        venue = self.get_object()
        if request.method == "GET":
            return Response(VenueImageSerializer(venue.images.all(), many=True, context={"request": request}).data)
        services.ensure_capability(request.user, venue, Capability.EDIT_PROFILE)
        upload = VenueImageUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        image = services.add_gallery_image(request, venue, upload.validated_data["image"])
        return Response(VenueImageSerializer(image, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Galereyadan rasmni o'chirish", tags=["venue-owner"], responses={204: None})
    @action(
        detail=True,
        methods=["delete"],
        url_path=rf"images/(?P<image_id>{UUID_RE})",
        url_name="delete-image",
        filter_backends=[],
    )
    def delete_image(self, request, pk=None, image_id=None):
        venue = self.get_object()
        services.ensure_capability(request.user, venue, Capability.EDIT_PROFILE)
        services.delete_gallery_image(request, get_object_or_404(VenueImage, pk=image_id, venue=venue))
        return Response(status=status.HTTP_204_NO_CONTENT)
