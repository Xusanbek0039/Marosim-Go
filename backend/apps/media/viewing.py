"""Couple / guest side of ceremony media: ``/api/v1/me/ceremonies/{ceremony_id}/media/…``.

Every request re-reads the caller's role from the database (``ownership.role_in``): a share that
expired or was revoked a second ago is already a 404. Bytes are streamed from Google Drive through
the server (the Drive file stays private to the platform account; no Drive id or link is exposed).

* OWNER — list, thumbnail, stream, download.
* VIEWER — list, thumbnail, stream (inline only). No download endpoint (user decision 2026-11-07).
"""

import re

from django.core.cache import cache
from django.http import HttpResponse, StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from apps.accounts.access import AccessNote
from apps.audit.services import AuditAction, record
from apps.ceremonies import ownership
from apps.ceremonies.models import AccessRole
from apps.ceremonies.permissions import IsClientUser
from apps.storage.google import GoogleError
from apps.storage.services import StorageError, access_credentials, gateway

from .models import MIME_TYPES, CeremonyMedia, MediaKind, MediaStatus
from .services import _storage_error

MEMBER_SCOPE = (
    "Faqat so'rovchi ACCEPTED egasi yoki muddati tugamagan ko'ruvchisi bo'lgan marosimning READY fayllari; "
    "boshqasi 404. Huquq har so'rovda qayta tekshiriladi."
)
#: One satisfiable single range ("bytes=0-", "bytes=100-199", "bytes=-500"); anything else is ignored.
RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")
THUMB_SIZES = (240, 480, 960)
THUMB_TTL = 10 * 60
BINARY_ACTIONS = {"thumbnail", "stream", "download"}


class MyMediaSerializer(serializers.ModelSerializer):
    """What an owner / viewer sees: no Drive ids, uploader identity or upload internals."""

    can_download = serializers.SerializerMethodField()

    class Meta:
        model = CeremonyMedia
        fields = [
            "id",
            "kind",
            "mime_type",
            "size_bytes",
            "width",
            "height",
            "duration_ms",
            "completed_at",
            "can_download",
        ]
        read_only_fields = fields

    def get_can_download(self, obj) -> bool:
        return self.context["role"] == AccessRole.OWNER


def _safe_range(raw: str | None) -> str | None:
    match = RANGE_RE.match((raw or "").strip())
    if not match or match.groups() == ("", ""):
        return None
    start, end = match.groups()
    if start and end and int(start) > int(end):
        return None
    return f"bytes={start}-{end}"


def _download_name(media: CeremonyMedia) -> str:
    """ASCII-only, id-based file name: the original name may carry personal data."""
    prefix = "video" if media.kind == MediaKind.VIDEO else "rasm"
    return f"marosimgo-{prefix}-{media.pk.hex[:8]}{MIME_TYPES.get(media.mime_type, '')}"


class MyMediaViewSet(viewsets.GenericViewSet):
    serializer_class = MyMediaSerializer
    queryset = CeremonyMedia.objects.none()
    permission_classes = [IsClientUser]
    pagination_class = None
    filter_backends = []
    access_notes = {
        "*": AccessNote(ownership=MEMBER_SCOPE),
        "stream": AccessNote(
            conditions=("HTTP Range qo'llab-quvvatlanadi (video uchun)", "Content-Disposition: inline")
        ),
        "download": AccessNote(
            conditions=("Faqat marosim EGASI; ko'ruvchi — 403", "Har bir yuklab olish audit qilinadi")
        ),
    }

    # Images / video are requested by <img> and <video> with Accept headers no JSON renderer matches.
    def perform_content_negotiation(self, request, force=False):
        return super().perform_content_negotiation(request, force=force or self.action in BINARY_ACTIONS)

    # ---------------------------------------------------------------- lookups
    def _ceremony_and_role(self):
        user = self.request.user
        ceremony = ownership.accessible_ceremonies(user).filter(pk=self.kwargs["ceremony_id"]).first()
        role = ownership.role_in(user, ceremony) if ceremony else None
        if role is None:
            raise NotFound()
        return ceremony, role

    def _media(self, ceremony) -> CeremonyMedia:
        media = CeremonyMedia.objects.filter(
            ceremony=ceremony, pk=self.kwargs["media_id"], status=MediaStatus.READY
        ).first()
        if media is None or not media.drive_file_id:
            raise NotFound()
        return media

    def _stream(self, media: CeremonyMedia, disposition: str) -> StreamingHttpResponse | HttpResponse:
        try:
            stream = gateway().open_media(
                access_credentials(), media.drive_file_id, _safe_range(self.request.headers.get("Range"))
            )
        except (StorageError, GoogleError) as exc:
            raise _storage_error(exc) from None
        if stream.status == 416:
            stream.close()
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{media.size_bytes}"
            return response

        def body():
            try:
                yield from stream.chunks
            finally:
                stream.close()

        response = StreamingHttpResponse(body(), status=stream.status, content_type=media.mime_type)
        for key, value in stream.headers.items():
            response[key] = value
        response["Accept-Ranges"] = "bytes"
        response["Content-Disposition"] = f'{disposition}; filename="{_download_name(media)}"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    # ---------------------------------------------------------------- actions
    @extend_schema(summary="Marosim rasm va videolari", tags=["me"], responses=MyMediaSerializer(many=True))
    def list(self, request, ceremony_id=None):
        ceremony, role = self._ceremony_and_role()
        rows = CeremonyMedia.objects.filter(ceremony=ceremony, status=MediaStatus.READY).order_by("completed_at", "id")
        return Response(MyMediaSerializer(rows, many=True, context={"role": role}).data)

    @extend_schema(
        summary="Kichik rasm (preview)",
        tags=["me"],
        parameters=[OpenApiParameter("size", int, enum=[*THUMB_SIZES], required=False)],
        responses={(200, "image/*"): OpenApiResponse(OpenApiTypes.BINARY), 404: None},
    )
    def thumbnail(self, request, ceremony_id=None, media_id=None):
        ceremony, _ = self._ceremony_and_role()
        media = self._media(ceremony)
        size = int(request.query_params.get("size") or 480)
        if size not in THUMB_SIZES:
            size = 480
        key = f"media-thumb:{media.pk}:{size}"
        hit = cache.get(key)
        if hit is None:
            try:
                hit = gateway().thumbnail(access_credentials(), media.drive_file_id, size) or (b"", "")
            except (StorageError, GoogleError) as exc:
                raise _storage_error(exc) from None
            cache.set(key, hit, THUMB_TTL)
        content, content_type = hit
        if not content:
            raise NotFound("Preview hali tayyor emas.")
        response = HttpResponse(content, content_type=content_type)
        response["Cache-Control"] = "private, max-age=600"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @extend_schema(
        summary="Faylni ko'rish (oqim, Range)",
        tags=["me"],
        responses={(200, "*/*"): OpenApiResponse(OpenApiTypes.BINARY), 206: OpenApiResponse(OpenApiTypes.BINARY)},
    )
    def stream(self, request, ceremony_id=None, media_id=None):
        ceremony, _ = self._ceremony_and_role()
        return self._stream(self._media(ceremony), "inline")

    @extend_schema(
        summary="Faylni yuklab olish (faqat ega)",
        tags=["me"],
        responses={(200, "*/*"): OpenApiResponse(OpenApiTypes.BINARY), 403: None},
    )
    def download(self, request, ceremony_id=None, media_id=None):
        ceremony, role = self._ceremony_and_role()
        if role != AccessRole.OWNER:
            raise PermissionDenied("Yuklab olish faqat marosim egalari uchun. Siz faqat ko'ra olasiz.")
        media = self._media(ceremony)
        response = self._stream(media, "attachment")
        if response.status_code in (200, 206) and not request.headers.get("Range"):
            record(request, AuditAction.MEDIA_DOWNLOAD, media, changes={"ceremony": str(ceremony.pk)})
        return response
