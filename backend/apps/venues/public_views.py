"""Public venue catalog (``/api/v1/venues/…``) and a couple's own hall bookings (``/api/v1/me/venue-bookings/``).

Public endpoints show only approved + active venues (``scheduling.public_venues``) and only whether
a slot is free — never who holds it, contact data of customers or internal notes.
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.access import AccessNote
from apps.ceremonies.permissions import IsClientUser
from apps.reviews.models import TargetKind
from apps.reviews.services import stats_map

from . import scheduling
from .models import HallBooking, HallSession, Region, Venue
from .serializers import (
    MyBookingCreateSerializer,
    MyBookingSerializer,
    PublicVenueDetailSerializer,
    PublicVenueSerializer,
    VenueAvailabilitySerializer,
    VenueSearchResultSerializer,
)
from .views import UUID_RE

PUBLIC_ONLY = "Faqat admin tasdiqlagan (APPROVED) va faol to'yxonalar; mijozlar haqida ma'lumot qaytmaydi."


class PublicVenueViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    queryset = Venue.objects.none()
    lookup_value_regex = UUID_RE
    pagination_class = None
    filter_backends = []
    access_notes = {"*": AccessNote(conditions=(PUBLIC_ONLY,))}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Venue.objects.none()
        return scheduling.public_venues().prefetch_related("images")

    @staticmethod
    def _sessions_of(halls):
        by_hall: dict = {}
        for s in HallSession.objects.filter(hall__in=halls, is_active=True).order_by("starts_at"):
            by_hall.setdefault(s.hall_id, []).append(s)
        return by_hall

    @extend_schema(
        summary="Sana bo'yicha bo'sh to'yxonalarni qidirish",
        tags=["venues"],
        parameters=[
            OpenApiParameter("date", OpenApiTypes.DATE, required=True, description="Masalan 2026-11-20"),
            OpenApiParameter("region", str, enum=Region.values),
            OpenApiParameter("guests", int, description="Mehmonlar soni — sig'imi yetadigan zallar"),
            OpenApiParameter("q", str, description="Nomi / manzili / tumani"),
        ],
        responses=VenueSearchResultSerializer(many=True),
    )
    @action(detail=False, methods=["get"])
    def search(self, request):
        params = request.query_params
        date = scheduling.parse_date(params.get("date"))
        if date < scheduling.today():
            return Response([])
        guests = params.get("guests")
        guests = int(guests) if guests and guests.isdigit() else None
        region = params.get("region", "")
        region = region if region in Region.values else ""
        rows = []
        for venue, halls in scheduling.search(date, region=region, guests=guests, q=params.get("q", "").strip()):
            hall_rows = [
                {
                    "id": hall.pk,
                    "name": hall.name,
                    "capacity": hall.capacity,
                    "price": hall.effective_base_price,
                    "slots": [
                        {"id": s.pk, "name": s.name, "starts_at": s.starts_at, "ends_at": s.ends_at, "is_free": free}
                        for s, free in slots
                    ],
                }
                for hall, slots in halls
            ]
            free = sum(1 for _, slots in halls for _, ok in slots if ok)
            rows.append({"venue": venue, "halls": hall_rows, "free_slots": free})
        rows = rows[:100]
        stats = stats_map(TargetKind.VENUE, [row["venue"].pk for row in rows])
        context = {"request": request, "stats": stats}
        return Response(VenueSearchResultSerializer(rows, many=True, context=context).data)

    @extend_schema(
        summary="To'yxonalar katalogi (reyting va like bo'yicha)",
        tags=["venues"],
        parameters=[
            OpenApiParameter("region", str, enum=Region.values),
            OpenApiParameter("q", str, description="Nomi / manzili / tumani"),
        ],
        responses=PublicVenueSerializer(many=True),
    )
    def list(self, request):
        venues = self.get_queryset()
        region = request.query_params.get("region", "")
        if region in Region.values:
            venues = venues.filter(region=region)
        q = request.query_params.get("q", "").strip()
        if q:
            venues = venues.filter(Q(name__icontains=q) | Q(address__icontains=q) | Q(district__icontains=q))
        venues = list(venues[:200])
        stats = stats_map(TargetKind.VENUE, [v.pk for v in venues])
        venues.sort(key=lambda v: (-(stats[v.pk]["rating_avg"] or 0), -stats[v.pk]["like_count"], v.name))
        return Response(PublicVenueSerializer(venues, many=True, context={"request": request, "stats": stats}).data)

    @extend_schema(
        summary="To'yxona (ommaviy ma'lumot, zallar va smenalar)",
        tags=["venues"],
        responses=PublicVenueDetailSerializer,
    )
    def retrieve(self, request, pk=None):
        venue = self.get_object()
        halls = list(scheduling.public_halls(venue))
        sessions = self._sessions_of(halls)
        data = {
            "venue": venue,
            "halls": [
                {
                    "id": h.pk,
                    "name": h.name,
                    "capacity": h.capacity,
                    "price": h.effective_base_price,
                    "sessions": sessions.get(h.pk, []),
                }
                for h in halls
            ],
        }
        return Response(PublicVenueDetailSerializer(data, context={"request": request}).data)

    @extend_schema(
        summary="To'yxona bo'sh smenalari (kalendar)",
        tags=["venues"],
        parameters=[
            OpenApiParameter("from", OpenApiTypes.DATE, required=True),
            OpenApiParameter("to", OpenApiTypes.DATE, required=True, description="Ko'pi bilan 62 kun."),
        ],
        responses=VenueAvailabilitySerializer,
    )
    @action(detail=True, methods=["get"])
    def availability(self, request, pk=None):
        venue = self.get_object()
        start, end = scheduling.parse_range(request.query_params)
        free = scheduling.venue_availability(venue, start, end)
        return Response(VenueAvailabilitySerializer({"date_from": start, "date_to": end, "free": free}).data)


OWN = "Faqat so'rovchining o'z bronlari; boshqasiniki 404."


@extend_schema_view(
    list=extend_schema(summary="Mening to'yxona bronlarim", tags=["me"]),
    retrieve=extend_schema(summary="Bron tafsiloti", tags=["me"]),
    create=extend_schema(
        summary="To'yxona smenasiga bron so'rovi yuborish",
        tags=["me"],
        request=MyBookingCreateSerializer,
        responses={201: MyBookingSerializer},
    ),
)
class MyVenueBookingViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    serializer_class = MyBookingSerializer
    permission_classes = [IsClientUser]
    queryset = HallBooking.objects.none()
    lookup_value_regex = UUID_RE
    pagination_class = None
    filter_backends = []
    access_notes = {
        "*": AccessNote(ownership=OWN),
        "create": AccessNote(
            ownership="",
            conditions=(
                "Faqat ommaga chiqqan to'yxonaning faol smenasi, bugundan boshlab 2 yilgacha.",
                "Smena band bo'lsa 409; bir vaqtda ko'pi bilan 10 ta ochiq so'rov.",
                "So'rov smenani band qilmaydi — to'yxona tasdiqlaganda band bo'ladi.",
            ),
        ),
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return HallBooking.objects.none()
        return scheduling.my_bookings(self.request.user).order_by("-date", "-created_at")

    def create(self, request, *args, **kwargs):
        body = MyBookingCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = dict(body.validated_data)
        session = get_object_or_404(HallSession.objects.select_related("hall__venue"), pk=data.pop("session"))
        booking = scheduling.request_booking(request, request.user, session, data.pop("date"), **data)
        booking = scheduling.my_bookings(request.user).get(pk=booking.pk)
        return Response(MyBookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Bron / so'rovni bekor qilish", tags=["me"], request=None, responses=MyBookingSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        scheduling.cancel(request, booking, by_requester=True)
        return Response(MyBookingSerializer(scheduling.my_bookings(request.user).get(pk=booking.pk)).data)
