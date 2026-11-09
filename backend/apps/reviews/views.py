"""Reviews and likes of venues / studios.

Public:   GET  /venues/{id}/reviews/            · /public/studios/{id}/reviews/
USER:     PUT|DELETE  …/reviews/mine/           (one review per account per business, upsert)
          POST|DELETE …/like/
Panel:    /admin/reviews/  — list, hide / unhide, delete (``reviews.*`` codes).

Only businesses visible to the public may be reviewed or liked (unpublished → 404).
"""

import django_filters
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.access import AccessNote
from apps.accounts.permissions import HasAdminPermission
from apps.audit.services import AuditAction, record
from apps.ceremonies.permissions import IsClientUser

from . import services
from .models import Review, TargetKind
from .serializers import (
    AdminReviewSerializer,
    LikeResultSerializer,
    PublicReviewSerializer,
    ReviewPageSerializer,
    ReviewWriteSerializer,
)

PUBLIC_TARGET = "Faqat ommaga ochiq (faol, tasdiqlangan) to'yxona / faol studiya; boshqasi 404."
OWN_REVIEW = "Faqat so'rovchining o'z sharhi / like'i; boshqalarniki o'zgarmaydi."


def _target(kind: str, pk):
    if kind == TargetKind.VENUE:
        from apps.venues.scheduling import public_venues

        return get_object_or_404(public_venues(), pk=pk)
    from apps.studios.services import public_studios

    return get_object_or_404(public_studios(), pk=pk)


class _TargetView(APIView):
    kind = TargetKind.VENUE  # set by ``as_view(kind=…)``

    def target(self):
        return _target(self.kind, self.kwargs["target_id"])


class TargetReviewsView(_TargetView):
    permission_classes = [AllowAny]
    access_notes = {"*": AccessNote(conditions=(PUBLIC_TARGET, "Yashirilgan sharhlar ko'rinmaydi."))}

    @extend_schema(summary="Sharhlar, reyting va like soni", tags=["reviews"], responses=ReviewPageSerializer)
    def get(self, request, target_id):
        target = self.target()
        user = request.user if request.user.is_authenticated else None
        data = {
            "summary": services.summary(self.kind, target, user),
            "results": services.visible_reviews(self.kind, target)[: services.PUBLIC_REVIEW_LIMIT],
        }
        return Response(ReviewPageSerializer(data).data)


class MyReviewView(_TargetView):
    permission_classes = [IsClientUser]
    access_notes = {"*": AccessNote(ownership=OWN_REVIEW, conditions=(PUBLIC_TARGET,))}

    @extend_schema(
        summary="Baho va izoh qoldirish / yangilash",
        tags=["reviews"],
        request=ReviewWriteSerializer,
        responses=PublicReviewSerializer,
    )
    def put(self, request, target_id):
        target = self.target()
        body = ReviewWriteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        review = services.upsert_review(request, self.kind, target, **body.validated_data)
        return Response(PublicReviewSerializer(review).data)

    @extend_schema(summary="O'z sharhimni o'chirish", tags=["reviews"], responses={204: None})
    def delete(self, request, target_id):
        services.delete_own_review(request, self.kind, self.target())
        return Response(status=status.HTTP_204_NO_CONTENT)


class LikeView(_TargetView):
    permission_classes = [IsClientUser]
    access_notes = {"*": AccessNote(ownership=OWN_REVIEW, conditions=(PUBLIC_TARGET,))}

    @extend_schema(summary="Like bosish", tags=["reviews"], request=None, responses=LikeResultSerializer)
    def post(self, request, target_id):
        count = services.set_like(self.kind, self.target(), request.user, True)
        return Response({"liked": True, "like_count": count})

    @extend_schema(summary="Like'ni olib tashlash", tags=["reviews"], responses=LikeResultSerializer)
    def delete(self, request, target_id):
        count = services.set_like(self.kind, self.target(), request.user, False)
        return Response({"liked": False, "like_count": count})


# ------------------------------------------------------------------- panel
class AdminReviewFilter(django_filters.FilterSet):
    kind = django_filters.ChoiceFilter(choices=TargetKind.choices, method="filter_kind")
    venue = django_filters.UUIDFilter(field_name="venue_id")
    studio = django_filters.UUIDFilter(field_name="studio_id")
    is_hidden = django_filters.BooleanFilter()
    rating = django_filters.NumberFilter()

    class Meta:
        model = Review
        fields = ["kind", "venue", "studio", "is_hidden", "rating"]

    def filter_kind(self, qs, name, value):
        return qs.filter(venue__isnull=False) if value == TargetKind.VENUE else qs.filter(studio__isnull=False)


@extend_schema_view(
    list=extend_schema(summary="Barcha sharhlar (moderatsiya)", tags=["admin-reviews"]),
    retrieve=extend_schema(summary="Sharh tafsiloti", tags=["admin-reviews"]),
    partial_update=extend_schema(summary="Sharhni yashirish / ko'rsatish", tags=["admin-reviews"]),
    destroy=extend_schema(summary="Sharhni o'chirish", tags=["admin-reviews"]),
)
class AdminReviewViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AdminReviewSerializer
    queryset = Review.objects.none()
    permission_classes = [HasAdminPermission]
    permission_module = "reviews"
    action_permissions = {"partial_update": "reviews.moderate", "destroy": "reviews.moderate"}
    http_method_names = ["get", "patch", "delete", "head", "options"]
    filterset_class = AdminReviewFilter
    search_fields = ["text", "venue__name", "studio__name", "author__first_name", "author__last_name"]
    ordering_fields = ["created_at", "rating"]
    ordering = ["-created_at"]
    access_notes = {"*": AccessNote(ownership="Barcha to'yxona va studiya sharhlari (yashirilganlari ham).")}

    def get_queryset(self):
        return Review.objects.select_related("venue", "studio", "author").order_by("-created_at")

    def perform_update(self, serializer):
        is_hidden = serializer.validated_data.get("is_hidden")
        if is_hidden is not None:
            services.moderate(self.request, serializer.instance, is_hidden=is_hidden)

    def perform_destroy(self, instance):
        record(self.request, AuditAction.DELETE, instance, target_label=f"Review {instance.pk}")
        instance.delete()
