"""Customer-facing studio catalog (``/api/v1/public/studios/…``) and the studio's own portfolio
(``/api/v1/studios/me/{studio_id}/images/…``).

Public endpoints show only active studios, their portfolio, rating and *how busy* each day is —
never ceremony titles, customers or staff.
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.access import AccessNote
from apps.ceremonies.permissions import IsStudioMember
from apps.reviews.models import TargetKind
from apps.reviews.services import stats_map
from apps.venues.scheduling import parse_range

from . import services
from .models import MAX_PORTFOLIO_IMAGES, StudioImage, StudioMembership
from .serializers import (
    PublicStudioSerializer,
    StudioImageSerializer,
    StudioImageUploadSerializer,
    StudioScheduleSerializer,
)

UUID_RE = r"[0-9a-fA-F-]{36}"
PUBLIC_ONLY = "Faqat faol studiyalar; xodimlar, mijozlar va marosim nomlari qaytmaydi."


class PublicStudioViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicStudioSerializer
    lookup_value_regex = UUID_RE
    pagination_class = None
    filter_backends = []
    access_notes = {"*": AccessNote(conditions=(PUBLIC_ONLY,))}

    def get_queryset(self):
        return services.public_studios().prefetch_related("images")

    @extend_schema(
        summary="Studiyalar (ommaviy katalog, reyting bo'yicha)",
        tags=["studios-public"],
        parameters=[OpenApiParameter("q", str, description="Nomi / manzili")],
        responses=PublicStudioSerializer(many=True),
    )
    def list(self, request):
        studios = self.get_queryset()
        q = request.query_params.get("q", "").strip()
        if q:
            studios = studios.filter(Q(name__icontains=q) | Q(address__icontains=q))
        studios = list(studios[:200])
        stats = stats_map(TargetKind.STUDIO, [s.pk for s in studios])
        studios.sort(key=lambda s: (-(stats[s.pk]["rating_avg"] or 0), -stats[s.pk]["like_count"], s.name))
        return Response(self.get_serializer(studios, many=True, context={"request": request, "stats": stats}).data)

    @extend_schema(summary="Studiya (ommaviy profil va portfolio)", tags=["studios-public"])
    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(
        summary="Studiya band kunlari (kalendar)",
        tags=["studios-public"],
        parameters=[
            OpenApiParameter("from", OpenApiTypes.DATE, required=True),
            OpenApiParameter("to", OpenApiTypes.DATE, required=True, description="Ko'pi bilan 62 kun."),
        ],
        responses=StudioScheduleSerializer,
    )
    @action(detail=True, methods=["get"])
    def schedule(self, request, pk=None):
        studio = self.get_object()
        start, end = parse_range(request.query_params)
        data = {"date_from": start, "date_to": end, "busy": services.busy_days(studio, start, end)}
        return Response(StudioScheduleSerializer(data).data)


# ------------------------------------------------------- studio's own portfolio
OWN_STUDIO = "Faqat so'rovchi faol a'zo bo'lgan studiya; yuklash/o'chirish — OWNER yoki MANAGER. Boshqasi 404."


def _membership(request, studio_id):
    membership = get_object_or_404(services.active_memberships(request.user), studio_id=studio_id)
    if request.method not in ("GET", "HEAD", "OPTIONS") and membership.role not in StudioMembership.MANAGING_ROLES:
        raise PermissionDenied("Portfolioni faqat studiya egasi yoki menejeri o'zgartira oladi.")
    return membership


class StudioMePortfolioView(APIView):
    permission_classes = [IsStudioMember]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    access_notes = {
        "*": AccessNote(ownership=OWN_STUDIO),
        "POST": AccessNote(conditions=(f"Ko'pi bilan {MAX_PORTFOLIO_IMAGES} ta rasm, har biri 5 MB gacha",)),
    }

    @extend_schema(summary="Studiya portfoliosi", tags=["studio"], responses=StudioImageSerializer(many=True))
    def get(self, request, studio_id):
        membership = _membership(request, studio_id)
        images = membership.studio.images.all()
        return Response(StudioImageSerializer(images, many=True, context={"request": request}).data)

    @extend_schema(
        summary="Portfolioga rasm qo'shish",
        tags=["studio"],
        request={"multipart/form-data": StudioImageUploadSerializer},
        responses={201: StudioImageSerializer},
    )
    def post(self, request, studio_id):
        membership = _membership(request, studio_id)
        upload = StudioImageUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        image = services.add_portfolio_image(request, membership.studio, upload.validated_data["image"])
        return Response(StudioImageSerializer(image, context={"request": request}).data, status=status.HTTP_201_CREATED)


class StudioMePortfolioImageView(APIView):
    permission_classes = [IsStudioMember]
    access_notes = {"*": AccessNote(ownership=OWN_STUDIO)}

    @extend_schema(summary="Portfoliodan rasmni o'chirish", tags=["studio"], responses={204: None})
    def delete(self, request, studio_id, image_id):
        membership = _membership(request, studio_id)
        services.delete_portfolio_image(request, get_object_or_404(StudioImage, pk=image_id, studio=membership.studio))
        return Response(status=status.HTTP_204_NO_CONTENT)
