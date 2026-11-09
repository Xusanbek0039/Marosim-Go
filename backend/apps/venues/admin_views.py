"""Super Admin / Admin panel management of venues: ``/api/v1/admin/venues/…``.

SUPER_ADMIN may do everything; an ADMIN only what a Super Admin granted (``venues.*`` codes,
re-read on every request, so a revoked permission stops working immediately). The public
``/api/v1/venues/`` path stays free for the customer-facing search (Phase F).
"""

import django_filters
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.access import AccessNote
from apps.accounts.permissions import HasAdminPermission
from apps.audit.services import AuditAction, diff, record, snapshot

from . import scheduling, services
from .models import (
    OPEN_STATUSES,
    BookingStatus,
    HallSession,
    PublicationStatus,
    Region,
    Venue,
    VenueHall,
    VenueImage,
    VenueMembership,
)
from .serializers import (
    AdminVenueSerializer,
    BookingDecisionSerializer,
    HallSessionSerializer,
    OwnerBookingCreateSerializer,
    OwnerBookingSerializer,
    OwnerBookingUpdateSerializer,
    OwnerCalendarSerializer,
    VenueHallSerializer,
    VenueImageSerializer,
    VenueImageUploadSerializer,
)
from .views import UUID_RE

ALL_VENUES = "Barcha o'chirilmagan to'yxonalar (get_queryset); to'yxona hisoblari bu API'ga kira olmaydi."
PUBLISH = "venues.publish"
SCHEDULE = "venues.schedule"


class VenueFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter()
    publication_status = django_filters.ChoiceFilter(choices=PublicationStatus.choices)
    region = django_filters.ChoiceFilter(choices=Region.choices)

    class Meta:
        model = Venue
        fields = ["is_active", "publication_status", "region"]


@extend_schema_view(
    list=extend_schema(summary="To'yxonalar ro'yxati (panel)", tags=["admin-venues"]),
    create=extend_schema(summary="To'yxona qo'shish (egasi bilan)", tags=["admin-venues"]),
    retrieve=extend_schema(summary="To'yxona ma'lumotlari (panel)", tags=["admin-venues"]),
    partial_update=extend_schema(summary="To'yxonani tahrirlash / bloklash / holat", tags=["admin-venues"]),
    destroy=extend_schema(summary="To'yxonani o'chirish (soft delete)", tags=["admin-venues"]),
)
class AdminVenueViewSet(viewsets.ModelViewSet):
    serializer_class = AdminVenueSerializer
    queryset = Venue.objects.none()
    permission_classes = [HasAdminPermission]
    permission_module = "venues"
    action_permissions = {
        "add_hall": "venues.update",
        "update_hall": "venues.update",
        "images": "venues.update",
        "delete_image": "venues.update",
        # schedule: venues.view sees every venue's calendar, changes need venues.schedule
        "calendar": "venues.view",
        "bookings": "venues.view",
        "hall_sessions": "venues.view",
        "create_booking": SCHEDULE,
        "update_booking": SCHEDULE,
        "confirm_booking": SCHEDULE,
        "reject_booking": SCHEDULE,
        "cancel_booking": SCHEDULE,
        "add_hall_session": SCHEDULE,
        "update_hall_session": SCHEDULE,
    }
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    lookup_value_regex = UUID_RE
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filterset_class = VenueFilter
    search_fields = ["name", "address", "district", "phone_number"]
    ordering_fields = ["name", "created_at", "base_price", "capacity_max"]
    ordering = ["-created_at"]
    access_notes = {
        "*": AccessNote(ownership=ALL_VENUES),
        "partial_update": AccessNote(conditions=("publication_status o'zgarishi uchun qo'shimcha `venues.publish`",)),
        "images": AccessNote(conditions=(f"Ko'pi bilan {services.MAX_GALLERY_IMAGES} ta rasm, har biri 5 MB gacha",)),
    }

    def get_queryset(self):
        return (
            Venue.objects.filter(deleted_at__isnull=True)
            .prefetch_related(
                Prefetch("halls", queryset=VenueHall.objects.filter(deleted_at__isnull=True)),
                "images",
                Prefetch("memberships", queryset=VenueMembership.objects.select_related("user").order_by("created_at")),
            )
            .order_by("-created_at")
        )

    def _ensure_publish(self, data) -> None:
        if "publication_status" in data and not self.request.user.has_admin_permission(PUBLISH):
            raise PermissionDenied("Ommaga chiqarish holatini o'zgartirish uchun `venues.publish` ruxsati kerak.")

    @transaction.atomic
    def perform_create(self, serializer):
        self._ensure_publish(serializer.validated_data)
        data = dict(serializer.validated_data)
        owner = data.pop("owner_id")
        status_value = data.pop("publication_status", None)
        is_active = data.pop("is_active", True)
        venue = services.create_venue(self.request, owner, **data)
        changed = {}
        if status_value and status_value != venue.publication_status:
            changed["publication_status"] = status_value
        if not is_active:
            changed["is_active"] = False
        if changed:
            Venue.objects.filter(pk=venue.pk).update(**changed)
            venue.refresh_from_db()
        serializer.instance = venue

    @transaction.atomic
    def perform_update(self, serializer):
        self._ensure_publish(serializer.validated_data)
        serializer.validated_data.pop("owner_id", None)  # ownership changes go through members (owner app)
        before = snapshot(serializer.instance, services.VENUE_AUDITED_FIELDS)
        was_active = serializer.instance.is_active
        venue = serializer.save()
        changes = diff(before, snapshot(venue, services.VENUE_AUDITED_FIELDS))
        if was_active != venue.is_active:
            record(self.request, AuditAction.ACTIVATE if venue.is_active else AuditAction.DEACTIVATE, venue)
            changes.pop("is_active", None)
        if changes:
            record(self.request, AuditAction.UPDATE, venue, changes=changes)

    @transaction.atomic
    def perform_destroy(self, instance):
        instance.soft_delete()
        record(self.request, AuditAction.DELETE, instance)

    # ------------------------------------------------------------- halls
    @extend_schema(
        summary="Zal qo'shish (panel)",
        tags=["admin-venues"],
        request=VenueHallSerializer,
        responses={201: VenueHallSerializer},
    )
    @action(detail=True, methods=["post"], url_path="halls", url_name="halls", filter_backends=[])
    def add_hall(self, request, pk=None):
        venue = self.get_object()
        serializer = VenueHallSerializer(data=request.data, context={"venue": venue})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            hall = serializer.save(venue=venue)
            record(request, AuditAction.CREATE, hall, changes=snapshot(hall, services.HALL_AUDITED_FIELDS))
        return Response(VenueHallSerializer(hall, context={"venue": venue}).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Zalni tahrirlash (panel)",
        tags=["admin-venues"],
        request=VenueHallSerializer,
        responses=VenueHallSerializer,
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
        serializer = VenueHallSerializer(hall, data=request.data, partial=True, context={"venue": venue})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            before = snapshot(hall, services.HALL_AUDITED_FIELDS)
            hall = serializer.save()
            changes = diff(before, snapshot(hall, services.HALL_AUDITED_FIELDS))
            if changes:
                record(request, AuditAction.UPDATE, hall, changes=changes)
        return Response(VenueHallSerializer(hall, context={"venue": venue}).data)

    # ------------------------------------------------------------ gallery
    @extend_schema(
        summary="Galereyaga rasm qo'shish (panel)",
        tags=["admin-venues"],
        request={"multipart/form-data": VenueImageUploadSerializer},
        responses={201: VenueImageSerializer},
    )
    @action(detail=True, methods=["post"], filter_backends=[])
    def images(self, request, pk=None):
        venue = self.get_object()
        upload = VenueImageUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        image = services.add_gallery_image(request, venue, upload.validated_data["image"])
        return Response(VenueImageSerializer(image, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Galereyadan rasmni o'chirish (panel)", tags=["admin-venues"], responses={204: None})
    @action(
        detail=True,
        methods=["delete"],
        url_path=rf"images/(?P<image_id>{UUID_RE})",
        url_name="delete-image",
        filter_backends=[],
    )
    def delete_image(self, request, pk=None, image_id=None):
        venue = self.get_object()
        services.delete_gallery_image(request, get_object_or_404(VenueImage, pk=image_id, venue=venue))
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ----------------------------------------------------------- schedule
    # Same rules as the owner's calendar (``scheduling``), but for every venue: the panel sees and
    # fixes any venue's schedule (e.g. a stuck request); every change is audited under the admin.
    def _hall(self, venue, hall_id):
        return get_object_or_404(VenueHall, pk=hall_id, venue=venue, deleted_at__isnull=True)

    def _booking(self, venue, booking_id):
        return get_object_or_404(scheduling.owner_bookings(venue), pk=booking_id)

    @extend_schema(
        summary="To'yxona jadvali: zallar, smenalar va yozuvlar (panel)",
        tags=["admin-venues"],
        parameters=[
            OpenApiParameter("from", OpenApiTypes.DATE, required=True),
            OpenApiParameter("to", OpenApiTypes.DATE, required=True, description="Ko'pi bilan 62 kun."),
        ],
        responses=OwnerCalendarSerializer,
    )
    @action(detail=True, methods=["get"], pagination_class=None, filter_backends=[])
    def calendar(self, request, pk=None):
        venue = self.get_object()
        start, end = scheduling.parse_range(request.query_params)
        halls = venue.halls.filter(deleted_at__isnull=True).prefetch_related(
            Prefetch("sessions", queryset=HallSession.objects.order_by("starts_at"))
        )
        bookings = scheduling.owner_bookings(venue).filter(date__gte=start, date__lte=end, status__in=OPEN_STATUSES)
        data = {"date_from": start, "date_to": end, "halls": halls, "bookings": bookings}
        return Response(OwnerCalendarSerializer(data).data)

    @extend_schema(
        methods=["GET"], summary="Zal smenalari (panel)", tags=["admin-venues"], responses=HallSessionSerializer(many=True)
    )
    @action(
        detail=True,
        methods=["get"],
        url_path=rf"halls/(?P<hall_id>{UUID_RE})/sessions",
        url_name="hall-sessions",
        pagination_class=None,
        filter_backends=[],
    )
    def hall_sessions(self, request, pk=None, hall_id=None):
        hall = self._hall(self.get_object(), hall_id)
        return Response(HallSessionSerializer(hall.sessions.order_by("starts_at"), many=True).data)

    @extend_schema(
        methods=["POST"],
        summary="Zalga smena qo'shish (panel)",
        tags=["admin-venues"],
        request=HallSessionSerializer,
        responses={201: HallSessionSerializer},
    )
    @hall_sessions.mapping.post
    def add_hall_session(self, request, pk=None, hall_id=None):
        hall = self._hall(self.get_object(), hall_id)
        serializer = HallSessionSerializer(data=request.data, context={"hall": hall})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            session = serializer.save(hall=hall)
            record(request, AuditAction.CREATE, session, changes=dict(serializer.data))
        return Response(HallSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Smenani tahrirlash / o'chirish-yoqish (panel)",
        tags=["admin-venues"],
        request=HallSessionSerializer,
        responses=HallSessionSerializer,
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path=rf"halls/(?P<hall_id>{UUID_RE})/sessions/(?P<session_id>{UUID_RE})",
        url_name="update-hall-session",
        filter_backends=[],
    )
    def update_hall_session(self, request, pk=None, hall_id=None, session_id=None):
        hall = self._hall(self.get_object(), hall_id)
        session = get_object_or_404(HallSession, pk=session_id, hall=hall)
        serializer = HallSessionSerializer(session, data=request.data, partial=True, context={"hall": hall})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            session = serializer.save()
            record(request, AuditAction.UPDATE, session, changes=dict(serializer.data))
        return Response(HallSessionSerializer(session).data)

    @extend_schema(
        methods=["GET"],
        summary="Bronlar va so'rovlar (panel)",
        tags=["admin-venues"],
        parameters=[
            OpenApiParameter("status", str, description="REQUESTED / CONFIRMED / BLOCKED / REJECTED / CANCELLED"),
            OpenApiParameter("from", OpenApiTypes.DATE),
            OpenApiParameter("to", OpenApiTypes.DATE),
        ],
        responses=OwnerBookingSerializer(many=True),
    )
    @action(detail=True, methods=["get"], pagination_class=None, filter_backends=[])
    def bookings(self, request, pk=None):
        rows = scheduling.owner_bookings(self.get_object())
        params = request.query_params
        if params.get("status") in BookingStatus.values:
            rows = rows.filter(status=params["status"])
        if params.get("from"):
            rows = rows.filter(date__gte=scheduling.parse_date(params["from"], "from"))
        if params.get("to"):
            rows = rows.filter(date__lte=scheduling.parse_date(params["to"], "to"))
        rows = rows.order_by("date", "session__starts_at")[:500]
        return Response(OwnerBookingSerializer(rows, many=True).data)

    @extend_schema(
        methods=["POST"],
        summary="Jadvalga yozuv qo'shish (panel)",
        tags=["admin-venues"],
        request=OwnerBookingCreateSerializer,
        responses={201: OwnerBookingSerializer},
    )
    @bookings.mapping.post
    def create_booking(self, request, pk=None):
        venue = self.get_object()
        serializer = OwnerBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        session = get_object_or_404(
            HallSession, pk=data.pop("session"), hall__venue=venue, hall__deleted_at__isnull=True
        )
        booking = scheduling.venue_create_entry(request, session, data.pop("date"), **data)
        return Response(OwnerBookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Yozuv tafsilotlarini tahrirlash (panel)",
        tags=["admin-venues"],
        request=OwnerBookingUpdateSerializer,
        responses=OwnerBookingSerializer,
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path=rf"bookings/(?P<booking_id>{UUID_RE})",
        url_name="update-booking",
        filter_backends=[],
    )
    def update_booking(self, request, pk=None, booking_id=None):
        booking = self._booking(self.get_object(), booking_id)
        serializer = OwnerBookingUpdateSerializer(booking, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            booking = serializer.save()
            record(request, AuditAction.UPDATE, booking, changes={"fields": sorted(serializer.validated_data)})
        return Response(OwnerBookingSerializer(booking).data)

    def _decide(self, request, booking_id, fn):
        venue = self.get_object()
        booking = self._booking(venue, booking_id)
        body = BookingDecisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        booking = fn(booking, body.validated_data.get("venue_note", ""))
        return Response(OwnerBookingSerializer(scheduling.owner_bookings(venue).get(pk=booking.pk)).data)

    @extend_schema(
        summary="So'rovni tasdiqlash (panel)",
        tags=["admin-venues"],
        request=BookingDecisionSerializer,
        responses=OwnerBookingSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path=rf"bookings/(?P<booking_id>{UUID_RE})/confirm",
        url_name="confirm-booking",
        filter_backends=[],
    )
    def confirm_booking(self, request, pk=None, booking_id=None):
        return self._decide(request, booking_id, lambda b, _note: scheduling.confirm(request, b))

    @extend_schema(
        summary="So'rovni rad etish (panel)",
        tags=["admin-venues"],
        request=BookingDecisionSerializer,
        responses=OwnerBookingSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path=rf"bookings/(?P<booking_id>{UUID_RE})/reject",
        url_name="reject-booking",
        filter_backends=[],
    )
    def reject_booking(self, request, pk=None, booking_id=None):
        return self._decide(request, booking_id, lambda b, note: scheduling.reject(request, b, note))

    @extend_schema(
        summary="Yozuvni bekor qilish (panel)",
        tags=["admin-venues"],
        request=BookingDecisionSerializer,
        responses=OwnerBookingSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path=rf"bookings/(?P<booking_id>{UUID_RE})/cancel",
        url_name="cancel-booking",
        filter_backends=[],
    )
    def cancel_booking(self, request, pk=None, booking_id=None):
        return self._decide(request, booking_id, lambda b, _note: scheduling.cancel(request, b, by_requester=False))
