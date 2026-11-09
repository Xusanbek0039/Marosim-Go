"""``/api/v1/admin/media-deletion-requests/`` — studios' requests to delete a READY file.

SUPER_ADMIN always; ADMIN with ``requests.view`` sees them and with ``requests.media_delete`` decides.
Admins see the file's metadata and the reason, never the private media itself.
"""

import django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.access import AccessNote
from apps.accounts.permissions import HasAdminPermission

from . import deletion
from .models import DeletionRequestStatus, MediaDeletionRequest
from .serializers import AdminDeletionRequestSerializer, DecisionSerializer

UUID_RE = "[0-9a-fA-F-]{36}"


class DeletionRequestFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=DeletionRequestStatus.choices)
    studio = django_filters.UUIDFilter(field_name="media__ceremony__studio_id")

    class Meta:
        model = MediaDeletionRequest
        fields = ["status", "studio"]


@extend_schema_view(
    list=extend_schema(summary="Media o'chirish so'rovlari", tags=["admin-requests"]),
    retrieve=extend_schema(summary="O'chirish so'rovi tafsiloti", tags=["admin-requests"]),
)
class AdminDeletionRequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AdminDeletionRequestSerializer
    permission_classes = [HasAdminPermission]
    permission_module = "requests"
    action_permissions = {
        "approve": "requests.media_delete",
        "reject": "requests.media_delete",
        "summary": "requests.view",
    }
    queryset = MediaDeletionRequest.objects.none()
    lookup_value_regex = UUID_RE
    filterset_class = DeletionRequestFilter
    search_fields = ["reason", "media__original_name", "media__ceremony__title", "media__ceremony__studio__name"]
    ordering_fields = ["created_at", "decided_at"]
    ordering = ["-created_at"]
    access_notes = {"*": AccessNote(ownership="Barcha studiyalarning so'rovlari (faqat ruxsati borlar).")}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return MediaDeletionRequest.objects.none()
        return MediaDeletionRequest.objects.select_related(
            "media__uploaded_by", "media__ceremony__studio", "requested_by", "decided_by"
        )

    def _respond(self, row):
        return Response(AdminDeletionRequestSerializer(self.get_queryset().get(pk=row.pk)).data)

    @extend_schema(
        summary="Tasdiqlash: fayl Drive savatiga o'tadi va ilovadan o'chadi",
        tags=["admin-requests"],
        request=DecisionSerializer,
        responses=AdminDeletionRequestSerializer,
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        body = DecisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return self._respond(deletion.approve(request, self.get_object(), body.validated_data["note"]))

    @extend_schema(
        summary="Rad etish (fayl qoladi)",
        tags=["admin-requests"],
        request=DecisionSerializer,
        responses=AdminDeletionRequestSerializer,
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        body = DecisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return self._respond(deletion.reject(request, self.get_object(), body.validated_data["note"]))

    @extend_schema(
        summary="Kutilayotgan so'rovlar soni (menyu belgisi uchun)",
        tags=["admin-requests"],
        responses={200: {"type": "object", "properties": {"pending": {"type": "integer"}}}},
    )
    @action(detail=False, methods=["get"], pagination_class=None, filter_backends=[])
    def summary(self, request):
        pending = MediaDeletionRequest.objects.filter(status=DeletionRequestStatus.PENDING).count()
        return Response({"pending": pending})
