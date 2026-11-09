"""Couple / guest side of ceremony media: ``/api/v1/me/ceremonies/{ceremony_id}/media/…``.

Every request re-reads the caller's role from the database (``ownership.role_in``): a share that
expired or was revoked a second ago is already a 404. Bytes are streamed from Google Drive through
the server (the Drive file stays private to the platform account; no Drive id or link is exposed).

* OWNER with a running subscription — originals without the logo, and download.
* Everyone else (OWNER without a subscription, every VIEWER) — the logo version only, no download
  (user decision 2026-11-08): photos and previews are stamped on the fly, videos are served from the
  burned-in copy (``watermark_jobs``); until that copy exists the video answers 409
  ``watermark_pending``. The original bytes are never sent to them.
"""

import re

from django.core.cache import cache
from django.http import HttpResponse, StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, viewsets
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.response import Response

from apps.accounts.access import AccessNote
from apps.audit.services import AuditAction, record
from apps.ceremonies import ownership
from apps.ceremonies.models import AccessRole
from apps.ceremonies.permissions import IsClientUser
from apps.storage.google import GoogleError
from apps.storage.services import StorageError, access_credentials, gateway
from apps.subscriptions.services import has_clean_access

from . import watermark, watermark_jobs
from .models import MIME_TYPES, CeremonyMedia, MediaKind, MediaStatus, WatermarkStatus
from .services import _storage_error

MEMBER_SCOPE = (
    "Faqat so'rovchi ACCEPTED egasi yoki muddati tugamagan ko'ruvchisi bo'lgan marosimning READY fayllari; "
    "boshqasi 404. Huquq har so'rovda qayta tekshiriladi."
)
#: One satisfiable single range ("bytes=0-", "bytes=100-199", "bytes=-500"); anything else is ignored.
RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")
THUMB_SIZES = (240, 480, 960)
THUMB_TTL = 10 * 60  # server-side cache; browsers get "no-store" like every /api/ response
#: Size of the logo-stamped full view of a photo (built from Drive's preview, not the original).
PHOTO_VIEW_SIZE = 1600
#: Originals up to this size may be stamped directly when Drive has no preview yet.
STAMP_ORIGINAL_MAX = 25 * 1024 * 1024
BROWSER_IMAGES = {"image/jpeg", "image/png", "image/webp"}


class WatermarkPending(APIException):
    status_code = 409
    default_detail = "Video tayyorlanmoqda (logo qo'shilmoqda). Birozdan keyin qayta urinib ko'ring."
    default_code = "watermark_pending"


class SubscriptionRequired(APIException):
    status_code = 403
    default_detail = "Logosiz ko'rish va yuklab olish uchun obuna kerak."
    default_code = "subscription_required"


BINARY_ACTIONS = {"thumbnail", "stream", "download"}


class MyMediaSerializer(serializers.ModelSerializer):
    """What an owner / viewer sees: no Drive ids, uploader identity or upload internals."""

    can_download = serializers.SerializerMethodField()
    watermarked = serializers.SerializerMethodField(help_text="Logo bilan ko'rsatiladi (obuna yo'q yoki ko'ruvchi)")
    processing = serializers.SerializerMethodField(help_text="Video uchun logoli nusxa hali tayyor emas")
    progress = serializers.SerializerMethodField(help_text="Logoli nusxa tayyorlanishi, % (faqat processing paytida)")

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
            "watermarked",
            "processing",
            "progress",
        ]
        read_only_fields = fields

    def get_can_download(self, obj) -> bool:
        return self.context["clean"]

    def get_watermarked(self, obj) -> bool:
        return not self.context["clean"]

    def get_processing(self, obj) -> bool:
        return not self.context["clean"] and obj.kind == MediaKind.VIDEO and obj.wm_status != WatermarkStatus.READY

    def get_progress(self, obj) -> int | None:
        if not self.get_processing(obj) or obj.wm_status != WatermarkStatus.PROCESSING:
            return None
        return obj.wm_progress


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
        "thumbnail": AccessNote(conditions=("Obunasi faol ega bo'lmasa — MarosimGo logosi bilan",)),
        "stream": AccessNote(
            conditions=(
                "HTTP Range qo'llab-quvvatlanadi (video uchun)",
                "Content-Disposition: inline",
                "Obunasi faol ega — original; boshqalar — logoli nusxa (video tayyor bo'lmasa 409 watermark_pending)",
            )
        ),
        "download": AccessNote(
            conditions=(
                "Faqat obunasi faol marosim EGASI; ko'ruvchi — 403, obunasiz ega — 403 subscription_required",
                "Har bir yuklab olish audit qilinadi",
            )
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

    def _clean(self, role) -> bool:
        """Originals without the logo: only an owner whose subscription is running right now."""
        return role == AccessRole.OWNER and has_clean_access(self.request.user)

    def _media(self, ceremony) -> CeremonyMedia:
        media = CeremonyMedia.objects.filter(
            ceremony=ceremony, pk=self.kwargs["media_id"], status=MediaStatus.READY
        ).first()
        if media is None or not media.drive_file_id:
            raise NotFound()
        return media

    def _stream(
        self, media: CeremonyMedia, disposition: str, *, watermarked: bool = False
    ) -> StreamingHttpResponse | HttpResponse:
        file_id = media.wm_drive_file_id if watermarked else media.drive_file_id
        size = media.wm_size_bytes if watermarked else media.size_bytes
        mime = watermark_jobs.WM_MIME if watermarked else media.mime_type
        try:
            stream = gateway().open_media(access_credentials(), file_id, _safe_range(self.request.headers.get("Range")))
        except (StorageError, GoogleError) as exc:
            raise _storage_error(exc) from None
        if stream.status == 416:
            stream.close()
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
            return response

        def body():
            try:
                yield from stream.chunks
            finally:
                stream.close()

        response = StreamingHttpResponse(body(), status=stream.status, content_type=mime)
        for key, value in stream.headers.items():
            response[key] = value
        response["Accept-Ranges"] = "bytes"
        response["Content-Disposition"] = f'{disposition}; filename="{_download_name(media)}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response

    # ---------------------------------------------------------------- actions
    @extend_schema(summary="Marosim rasm va videolari", tags=["me"], responses=MyMediaSerializer(many=True))
    def list(self, request, ceremony_id=None):
        ceremony, role = self._ceremony_and_role()
        rows = CeremonyMedia.objects.filter(ceremony=ceremony, status=MediaStatus.READY).order_by("completed_at", "id")
        clean = self._clean(role)
        if not clean and watermark_jobs.needs_work(rows.filter(kind=MediaKind.VIDEO)):
            watermark_jobs.kick()  # self-healing: a queued video starts processing when someone looks
        return Response(MyMediaSerializer(rows, many=True, context={"role": role, "clean": clean}).data)

    @extend_schema(
        summary="Kichik rasm (preview)",
        tags=["me"],
        parameters=[OpenApiParameter("size", int, enum=[*THUMB_SIZES], required=False)],
        responses={(200, "image/*"): OpenApiResponse(OpenApiTypes.BINARY), 404: None},
    )
    def thumbnail(self, request, ceremony_id=None, media_id=None):
        ceremony, role = self._ceremony_and_role()
        media = self._media(ceremony)
        size = int(request.query_params.get("size") or 480)
        if size not in THUMB_SIZES:
            size = 480
        content, content_type = self._preview(media, size)
        if not content:
            raise NotFound("Preview hali tayyor emas.")
        if not self._clean(role):
            content, content_type = self._stamped(media, size, content)
        response = HttpResponse(content, content_type=content_type)
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def _preview(self, media: CeremonyMedia, size: int) -> tuple[bytes, str]:
        key = f"media-thumb:{media.pk}:{size}"
        hit = cache.get(key)
        if hit is None:
            try:
                hit = gateway().thumbnail(access_credentials(), media.drive_file_id, size) or (b"", "")
            except (StorageError, GoogleError) as exc:
                raise _storage_error(exc) from None
            cache.set(key, hit, THUMB_TTL)
        return hit

    def _stamped(self, media: CeremonyMedia, size: int, content: bytes) -> tuple[bytes, str]:
        key = f"media-thumb-wm:{media.pk}:{size}"
        hit = cache.get(key)
        if hit is None:
            try:
                hit = watermark.stamp_image(content)
            except watermark.WatermarkError:
                raise NotFound("Preview hali tayyor emas.") from None
            cache.set(key, hit, THUMB_TTL)
        return hit

    def _photo_view(self, media: CeremonyMedia) -> HttpResponse:
        """Logo-stamped full view of a photo: Drive's large preview, or the original if it is small."""
        content, _ = self._preview(media, PHOTO_VIEW_SIZE)
        if not content and media.mime_type in BROWSER_IMAGES and media.size_bytes <= STAMP_ORIGINAL_MAX:
            try:
                stream = gateway().open_media(access_credentials(), media.drive_file_id)
            except (StorageError, GoogleError) as exc:
                raise _storage_error(exc) from None
            try:
                content = b"".join(stream.chunks)
            finally:
                stream.close()
        if not content:
            raise NotFound("Rasm hali tayyor emas.")
        body, content_type = self._stamped(media, PHOTO_VIEW_SIZE, content)
        response = HttpResponse(body, content_type=content_type)
        response["Content-Disposition"] = "inline"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @extend_schema(
        summary="Faylni ko'rish (oqim, Range)",
        tags=["me"],
        responses={(200, "*/*"): OpenApiResponse(OpenApiTypes.BINARY), 206: OpenApiResponse(OpenApiTypes.BINARY)},
    )
    def stream(self, request, ceremony_id=None, media_id=None):
        ceremony, role = self._ceremony_and_role()
        media = self._media(ceremony)
        if self._clean(role):
            return self._stream(media, "inline")
        if media.kind == MediaKind.PHOTO:
            return self._photo_view(media)
        if media.wm_status != WatermarkStatus.READY or not media.wm_drive_file_id:
            watermark_jobs.kick()
            raise WatermarkPending()
        return self._stream(media, "inline", watermarked=True)

    @extend_schema(
        summary="Faylni yuklab olish (faqat obunasi faol ega, logosiz original)",
        tags=["me"],
        responses={(200, "*/*"): OpenApiResponse(OpenApiTypes.BINARY), 403: None},
    )
    def download(self, request, ceremony_id=None, media_id=None):
        ceremony, role = self._ceremony_and_role()
        if role != AccessRole.OWNER:
            raise PermissionDenied("Yuklab olish faqat marosim egalari uchun. Siz faqat ko'ra olasiz.")
        if not self._clean(role):
            raise SubscriptionRequired()
        media = self._media(ceremony)
        response = self._stream(media, "attachment")
        if response.status_code in (200, 206) and not request.headers.get("Range"):
            record(request, AuditAction.MEDIA_DOWNLOAD, media, changes={"ceremony": str(ceremony.pk)})
        return response
