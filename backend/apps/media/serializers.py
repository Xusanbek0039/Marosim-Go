from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from .models import MIME_TYPES, CeremonyMedia


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


class MediaSerializer(serializers.ModelSerializer):
    """Studio view of a media item. Drive ids and the session URI are never included."""

    uploaded_by_name = serializers.SerializerMethodField()

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
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields

    def get_uploaded_by_name(self, obj) -> str | None:
        user = obj.uploaded_by
        return (user.full_name or None) if user else None


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
