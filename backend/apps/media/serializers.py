from drf_spectacular.utils import OpenApiExample, extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from .models import MIME_TYPES, CeremonyMedia, MediaDeletionRequest


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Video yuklashni boshlash",
            value={"filename": "IMG_2041.MOV", "mime_type": "video/quicktime", "size_bytes": 734003200},
            request_only=True,
        )
    ]
)
class UploadStartSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255, help_text="Faqat ko'rsatish uchun; Drive'da fayl nomi = media id.")
    mime_type = serializers.ChoiceField(choices=sorted(MIME_TYPES))
    size_bytes = serializers.IntegerField(min_value=1)
    md5 = serializers.RegexField(
        r"^[0-9a-fA-F]{32}$",
        required=False,
        allow_blank=True,
        help_text="Ixtiyoriy: yakunda Drive checksum'i bilan solishtiriladi.",
    )


def _name(user) -> str | None:
    return (user.full_name or None) if user else None


class PendingDeletionSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MediaDeletionRequest
        fields = ["id", "reason", "requested_by_name", "created_at"]
        read_only_fields = fields

    def get_requested_by_name(self, obj) -> str | None:
        return _name(obj.requested_by)


class MediaSerializer(serializers.ModelSerializer):
    """Studio view of a media item. Drive ids and the session URI are never included."""

    uploaded_by_name = serializers.SerializerMethodField()
    deletion_request = serializers.SerializerMethodField(
        help_text="Kutilayotgan o'chirish so'rovi (admin tasdig'ini kutmoqda) yoki null."
    )

    class Meta:
        model = CeremonyMedia
        fields = [
            "id",
            "kind",
            "status",
            "original_name",
            "mime_type",
            "size_bytes",
            "width",
            "height",
            "duration_ms",
            "error_code",
            "uploaded_by_name",
            "deletion_request",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields

    def get_uploaded_by_name(self, obj) -> str | None:
        return _name(obj.uploaded_by)

    @extend_schema_field(PendingDeletionSerializer(allow_null=True))
    def get_deletion_request(self, obj):
        pending = getattr(obj, "pending_deletions", None)
        if pending is None:  # not prefetched (single object responses)
            pending = list(obj.deletion_requests.filter(status="PENDING").select_related("requested_by"))
        return PendingDeletionSerializer(pending[0]).data if pending else None


class UploadSessionSerializer(serializers.Serializer):
    media = MediaSerializer()
    upload_url = serializers.URLField(
        allow_null=True,
        help_text=(
            "Google Drive resumable session URI — baytlar shu manzilga PUT qilinadi (Authorization kerak emas). "
            "Faqat yuklashni boshlagan foydalanuvchiga va UPLOADING holatida qaytariladi; uni log'ga yozmang."
        ),
    )
    session_expires_at = serializers.DateTimeField(allow_null=True)
    received_bytes = serializers.IntegerField(allow_null=True, help_text="Google qabul qilgan baytlar (jonli).")
    chunk_size_multiple = serializers.IntegerField(help_text="Oxirgisidan boshqa har bir bo'lak shu songa karrali.")


class DeletionRequestCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, help_text="Nega o'chirilishi kerak (admin ko'radi).")


class DecisionSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class _MediaBriefSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CeremonyMedia
        fields = ["id", "kind", "status", "original_name", "mime_type", "size_bytes", "uploaded_by_name", "completed_at"]
        read_only_fields = fields

    def get_uploaded_by_name(self, obj) -> str | None:
        return _name(obj.uploaded_by)


class _CeremonyBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    event_date = serializers.DateField(allow_null=True)


class _StudioBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class _UserBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(source="full_name", allow_null=True)
    phone_number = serializers.CharField(allow_null=True)


class AdminDeletionRequestSerializer(serializers.ModelSerializer):
    """Admin view of a deletion request with enough context to decide."""

    media = _MediaBriefSerializer(read_only=True)
    ceremony = _CeremonyBriefSerializer(source="media.ceremony", read_only=True)
    studio = _StudioBriefSerializer(source="media.ceremony.studio", read_only=True)
    requested_by = _UserBriefSerializer(read_only=True, allow_null=True)
    decided_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MediaDeletionRequest
        fields = [
            "id",
            "status",
            "reason",
            "media",
            "ceremony",
            "studio",
            "requested_by",
            "decided_by_name",
            "decided_at",
            "decision_note",
            "created_at",
        ]
        read_only_fields = fields

    def get_decided_by_name(self, obj) -> str | None:
        return _name(obj.decided_by)
