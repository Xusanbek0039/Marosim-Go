"""Venue-owner endpoints (``/api/v1/venue-owner/…``) — mobile REST API for venue accounts.

Row scope lives in ``services.venues_for`` and is applied in ``get_queryset``: a venue without an
active membership of the caller is a 404, never a 403. Writes additionally need the matching
membership capability (``services.ensure_capability``).
"""

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.access import AccessNote
from apps.audit.services import AuditAction, diff, record, snapshot

from . import scheduling, services
from .models import (
    OPEN_STATUSES,
    BookingStatus,
    Capability,
    HallSession,
    Venue,
    VenueHall,
    VenueImage,
    VenueMembership,
)
from .permissions import IsVenueAccount
from .serializers import (
    BookingDecisionSerializer,
    HallSessionSerializer,
    OwnerBookingCreateSerializer,
    OwnerBookingSerializer,
    OwnerBookingUpdateSerializer,
    OwnerCalendarSerializer,
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
        "calendar": AccessNote(conditions=("Har qanday faol a'zo (VIEW).", "Oraliq ko'pi bilan 62 kun.")),
        "hall_sessions": AccessNote(conditions=("POST: " + _needs(Capability.MANAGE_SCHEDULE), BLOCKED)),
        "update_hall_session": AccessNote(
            conditions=(_needs(Capability.MANAGE_SCHEDULE), BLOCKED, "Bir zal smenalari vaqt bo'yicha kesishmaydi.")
        ),
        "bookings": AccessNote(
            conditions=(
                "POST CONFIRMED: " + _needs(Capability.MANAGE_BOOKINGS),
                "POST BLOCKED: " + _needs(Capability.MANAGE_SCHEDULE),
                BLOCKED,
                "Band smenaga ikkinchi yozuv — 409 (DB unique index + qator qulfi).",
            )
        ),
        "update_booking": AccessNote(conditions=("BLOCKED: MANAGE_SCHEDULE, boshqalar: MANAGE_BOOKINGS", BLOCKED)),
        "confirm_booking": AccessNote(
            conditions=(
                _needs(Capability.MANAGE_BOOKINGS),
                BLOCKED,
                "Shu smenaga boshqa kutilayotgan so'rovlar avtomatik rad etiladi; band bo'lsa 409.",
            )
        ),
        "reject_booking": AccessNote(conditions=(_needs(Capability.MANAGE_BOOKINGS), BLOCKED)),
        "cancel_booking": AccessNote(conditions=("BLOCKED: MANAGE_SCHEDULE, boshqalar: MANAGE_BOOKINGS", BLOCKED)),
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

    # ---------------------------------------------------------- schedule
    def _hall(self, venue, hall_id):
        return get_object_or_404(VenueHall, pk=hall_id, venue=venue, deleted_at__isnull=True)

    @extend_schema(
        summary="Jadval: zallar, smenalar va shu oraliqdagi barcha yozuvlar",
        tags=["venue-owner"],
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
        methods=["GET"], summary="Zal smenalari", tags=["venue-owner"], responses=HallSessionSerializer(many=True)
    )
    @extend_schema(
        methods=["POST"],
        summary="Zalga smena qo'shish",
        tags=["venue-owner"],
        request=HallSessionSerializer,
        responses={201: HallSessionSerializer},
    )
    @action(
        detail=True,
        methods=["get", "post"],
        url_path=rf"halls/(?P<hall_id>{UUID_RE})/sessions",
        url_name="hall-sessions",
        pagination_class=None,
        filter_backends=[],
    )
    def hall_sessions(self, request, pk=None, hall_id=None):
        venue = self.get_object()
        hall = self._hall(venue, hall_id)
        if request.method == "GET":
            return Response(HallSessionSerializer(hall.sessions.order_by("starts_at"), many=True).data)
        services.ensure_capability(request.user, venue, Capability.MANAGE_SCHEDULE)
        serializer = HallSessionSerializer(data=request.data, context={"hall": hall})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            session = serializer.save(hall=hall)
            record(request, AuditAction.CREATE, session, changes=dict(serializer.data))
        return Response(HallSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Smenani tahrirlash / o'chirish-yoqish",
        tags=["venue-owner"],
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
        venue = self.get_object()
        hall = self._hall(venue, hall_id)
        session = get_object_or_404(HallSession, pk=session_id, hall=hall)
        services.ensure_capability(request.user, venue, Capability.MANAGE_SCHEDULE)
        serializer = HallSessionSerializer(session, data=request.data, partial=True, context={"hall": hall})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            session = serializer.save()
            record(request, AuditAction.UPDATE, session, changes=dict(serializer.data))
        return Response(HallSessionSerializer(session).data)

    # ---------------------------------------------------------- bookings
    def _booking(self, venue, booking_id):
        return get_object_or_404(scheduling.owner_bookings(venue), pk=booking_id)

    @staticmethod
    def _capability_for(entry_status: str) -> str:
        return Capability.MANAGE_SCHEDULE if entry_status == BookingStatus.BLOCKED else Capability.MANAGE_BOOKINGS

    @extend_schema(
        methods=["GET"],
        summary="Bronlar va so'rovlar",
        tags=["venue-owner"],
        parameters=[
            OpenApiParameter("status", str, description="REQUESTED / CONFIRMED / BLOCKED / REJECTED / CANCELLED"),
            OpenApiParameter("from", OpenApiTypes.DATE),
            OpenApiParameter("to", OpenApiTypes.DATE),
        ],
        responses=OwnerBookingSerializer(many=True),
    )
    @extend_schema(
        methods=["POST"],
        summary="Jadvalga yozuv qo'shish (o'z mijozi yoki yopiq smena)",
        tags=["venue-owner"],
        request=OwnerBookingCreateSerializer,
        responses={201: OwnerBookingSerializer},
    )
    @action(detail=True, methods=["get", "post"], pagination_class=None, filter_backends=[])
    def bookings(self, request, pk=None):
        venue = self.get_object()
        if request.method == "GET":
            rows = scheduling.owner_bookings(venue)
            params = request.query_params
            if params.get("status"):
                rows = rows.filter(status=params["status"])
            if params.get("from"):
                rows = rows.filter(date__gte=scheduling.parse_date(params["from"], "from"))
            if params.get("to"):
                rows = rows.filter(date__lte=scheduling.parse_date(params["to"], "to"))
            rows = rows.order_by("date", "session__starts_at")[:500]
            return Response(OwnerBookingSerializer(rows, many=True).data)
        serializer = OwnerBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        services.ensure_capability(request.user, venue, self._capability_for(data["status"]))
        session = get_object_or_404(
            HallSession, pk=data.pop("session"), hall__venue=venue, hall__deleted_at__isnull=True
        )
        booking = scheduling.venue_create_entry(request, session, data.pop("date"), **data)
        return Response(OwnerBookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Yozuv tafsilotlarini tahrirlash",
        tags=["venue-owner"],
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
        venue = self.get_object()
        booking = self._booking(venue, booking_id)
        services.ensure_capability(request.user, venue, self._capability_for(booking.status))
        serializer = OwnerBookingUpdateSerializer(booking, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            booking = serializer.save()
            record(request, AuditAction.UPDATE, booking, changes={"fields": sorted(serializer.validated_data)})
        return Response(OwnerBookingSerializer(booking).data)

    def _decide(self, request, booking_id, fn, capability=None):
        venue = self.get_object()
        booking = self._booking(venue, booking_id)
        services.ensure_capability(request.user, venue, capability or self._capability_for(booking.status))
        body = BookingDecisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        booking = fn(booking, body.validated_data.get("venue_note", ""))
        return Response(OwnerBookingSerializer(scheduling.owner_bookings(venue).get(pk=booking.pk)).data)

    @extend_schema(
        summary="So'rovni tasdiqlash (smena band bo'ladi)",
        tags=["venue-owner"],
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
        return self._decide(
            request, booking_id, lambda b, _note: scheduling.confirm(request, b), Capability.MANAGE_BOOKINGS
        )

    @extend_schema(
        summary="So'rovni rad etish",
        tags=["venue-owner"],
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
        return self._decide(
            request, booking_id, lambda b, note: scheduling.reject(request, b, note), Capability.MANAGE_BOOKINGS
        )

    @extend_schema(
        summary="Yozuvni bekor qilish (smena bo'shaydi)",
        tags=["venue-owner"],
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
