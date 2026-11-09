"""Studio media endpoints: ``/api/v1/ceremonies/{ceremony_id}/media/…``.

The ceremony is resolved through the studio scope (``ceremonies.services.ceremonies_for``): another
studio's ceremony is a 404. Upload itself goes client → Google; see ``services``.
"""

from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.access import AccessNote
from apps.ceremonies import services as ceremony_services
from apps.ceremonies.permissions import IsStudioMemberOrSuperAdmin

from . import deletion, services
from .models import CeremonyMedia, DeletionRequestStatus, MediaDeletionRequest, MediaKind, MediaStatus
from .serializers import (
    DeletionRequestCreateSerializer,
    MediaSerializer,
    PendingDeletionSerializer,
    UploadSessionSerializer,
    UploadStartSerializer,
)

STUDIO_SCOPE = "STUDIO: faqat faol a'zolik bo'lgan studiyaning marosimi (boshqasi 404); SUPER_ADMIN: barchasi."
UPLOAD_CONDITION = "Har qanday faol studiya a'zosi (OWNER / MANAGER / UPLOADER) yoki SUPER_ADMIN."


def _session_payload(request, media: CeremonyMedia, uri: str | None = None, received: int | None = None) -> dict:
    mine = media.uploaded_by_id == request.user.pk
    return {
        "media": media,
        "upload_url": (uri or services.session_uri(media)) if mine else None,
        "session_expires_at": media.session_expires_at if media.status == MediaStatus.UPLOADING else None,
        "received_bytes": received,
        "chunk_size_multiple": services.CHUNK_MULTIPLE,
    }


@extend_schema_view(
    list=extend_schema(
        summary="Marosimning yuklangan fayllari va holati",
        tags=["media"],
        parameters=[
            OpenApiParameter(
                "status", str, enum=[s.value for s in MediaStatus if s != MediaStatus.DELETED], required=False
            ),
            OpenApiParameter("kind", str, enum=[k.value for k in MediaKind], required=False),
        ],
    )
)
class StudioMediaViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = MediaSerializer
    queryset = CeremonyMedia.objects.none()
    permission_classes = [IsStudioMemberOrSuperAdmin]
    filter_backends = []
    access_notes = {
        "*": AccessNote(ownership=STUDIO_SCOPE),
        "start_upload": AccessNote(
            conditions=(
                UPLOAD_CONDITION,
                "Google Drive ulangan bo'lishi shart (aks holda 503 storage_unavailable).",
                "Arxivlangan marosimga yuklab bo'lmaydi; tur va hajm cheklangan.",
            )
        ),
        "upload_status": AccessNote(conditions=("upload_url faqat yuklashni boshlagan foydalanuvchiga qaytadi.",)),
        "complete": AccessNote(conditions=(UPLOAD_CONDITION, "Fayl Drive'dan qayta o'qilib tekshiriladi.")),
        "cancel": AccessNote(conditions=("Yuklashni boshlagan a'zo yoki studiya OWNER/MANAGER.",)),
        "dismiss": AccessNote(
            conditions=(
                "Yuklashni boshlagan a'zo yoki studiya OWNER/MANAGER.",
                "Faqat tugallanmagan fayl (UPLOADING / FAILED / CANCELLED / EXPIRED); tayyor fayl — so'rov orqali.",
            )
        ),
        "request_delete": AccessNote(
            conditions=(UPLOAD_CONDITION, "Faqat READY fayl; bir faylga bitta kutilayotgan so'rov.")
        ),
        "cancel_delete": AccessNote(conditions=("So'rovni yuborgan a'zo yoki studiya OWNER/MANAGER.",)),
    }

    def get_throttles(self):
        if self.action == "start_upload":
            self.throttle_scope = "media_upload"
            return [*super().get_throttles(), ScopedRateThrottle()]
        return super().get_throttles()

    def ceremony(self):
        if not hasattr(self, "_ceremony"):
            row = ceremony_services.ceremonies_for(self.request.user).filter(pk=self.kwargs["ceremony_id"]).first()
            if row is None:
                raise NotFound()
            self._ceremony = row
        return self._ceremony

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CeremonyMedia.objects.none()
        pending = MediaDeletionRequest.objects.filter(status=DeletionRequestStatus.PENDING).select_related(
            "requested_by"
        )
        qs = (
            CeremonyMedia.objects.filter(ceremony=self.ceremony())
            .exclude(status=MediaStatus.DELETED)
            .select_related("uploaded_by", "ceremony__studio")
            .prefetch_related(Prefetch("deletion_requests", queryset=pending, to_attr="pending_deletions"))
        )
        params = self.request.query_params
        if params.get("status") in MediaStatus.values:
            qs = qs.filter(status=params["status"])
        if params.get("kind") in MediaKind.values:
            qs = qs.filter(kind=params["kind"])
        return qs

    def _media(self) -> CeremonyMedia:
        row = self.get_queryset().filter(pk=self.kwargs["media_id"]).first()
        if row is None:
            raise NotFound()
        return row

    @extend_schema(
        summary="Media yuklashni boshlash (Google Drive resumable sessiya)",
        description=(
            "Javobdagi `upload_url` ga fayl baytlari to'g'ridan-to'g'ri yuboriladi (PUT, `Content-Range` bilan "
            "bo'laklab; uzilsa davom ettiriladi). So'ng `complete/` chaqiriladi. Backend hech qachon OAuth "
            "tokenini bermaydi; Drive fayli public qilinmaydi."
        ),
        tags=["media"],
        request=UploadStartSerializer,
        responses={201: UploadSessionSerializer},
    )
    def start_upload(self, request, ceremony_id=None):
        serializer = UploadStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        media, uri = services.start_upload(request, self.ceremony(), **serializer.validated_data)
        data = UploadSessionSerializer(_session_payload(request, media, uri, 0)).data
        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Yuklash holati (Google'dan jonli progress)", tags=["media"], responses=UploadSessionSerializer
    )
    def upload_status(self, request, ceremony_id=None, media_id=None):
        media = self._media()
        received = services.progress(media)
        media.refresh_from_db()
        return Response(UploadSessionSerializer(_session_payload(request, media, received=received)).data)

    @extend_schema(
        summary="Yuklashni yakunlash va tekshirish",
        tags=["media"],
        request=None,
        responses=UploadSessionSerializer,
    )
    def complete(self, request, ceremony_id=None, media_id=None):
        media = services.complete(request, self._media())
        payload = _session_payload(request, media, received=media.size_bytes)
        return Response(UploadSessionSerializer(payload).data)

    @extend_schema(summary="Yuklashni bekor qilish", tags=["media"], request=None, responses=UploadSessionSerializer)
    def cancel(self, request, ceremony_id=None, media_id=None):
        media = services.cancel(request, self._media())
        return Response(UploadSessionSerializer(_session_payload(request, media)).data)

    @extend_schema(
        summary="Tugallanmagan yuklashni ro'yxatdan o'chirish",
        description="Ochiq Drive sessiyasi bekor qilinadi. Tayyor (READY) faylga 409 — o'chirish so'rovi yuboriladi.",
        tags=["media"],
        request=None,
        responses={204: None},
    )
    def dismiss(self, request, ceremony_id=None, media_id=None):
        deletion.dismiss(request, self._media())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Tayyor faylni o'chirishni so'rash (admin tasdiqlaydi)",
        tags=["media"],
        request=DeletionRequestCreateSerializer,
        responses={201: PendingDeletionSerializer},
    )
    def request_delete(self, request, ceremony_id=None, media_id=None):
        body = DeletionRequestCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        row = deletion.request_deletion(request, self._media(), body.validated_data["reason"])
        return Response(PendingDeletionSerializer(row).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="O'chirish so'rovini qaytarib olish", tags=["media"], request=None, responses={204: None})
    def cancel_delete(self, request, ceremony_id=None, media_id=None):
        deletion.cancel_request(request, self._media())
        return Response(status=status.HTTP_204_NO_CONTENT)
