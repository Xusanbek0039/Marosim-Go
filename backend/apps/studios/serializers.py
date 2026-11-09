from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.accounts.serializers import PhoneNumberField, UserSummarySerializer
from apps.core.uploads import process_image
from apps.reviews.models import TargetKind
from apps.reviews.serializers import StatsSerializer
from apps.reviews.services import empty_stats, stats_map

from .models import Studio, StudioImage


class StudioImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudioImage
        fields = ["id", "image", "position", "created_at"]
        read_only_fields = fields


class StudioImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()


class StudioSerializer(serializers.ModelSerializer):
    responsible_user = UserSummarySerializer(read_only=True)
    responsible_user_id = serializers.PrimaryKeyRelatedField(
        source="responsible_user",
        queryset=User.objects.alive().filter(role=Role.STUDIO, is_active=True),
        write_only=True,
        error_messages={
            "does_not_exist": "Mas'ul shaxs topilmadi yoki u faol STUDIO rolidagi foydalanuvchi emas.",
        },
    )
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    images = StudioImageSerializer(many=True, read_only=True)
    phone_number = PhoneNumberField(required=False, allow_blank=True)

    class Meta:
        model = Studio
        fields = [
            "id",
            "name",
            "description",
            "profile_picture",
            "address",
            "phone_number",
            "images",
            "responsible_user",
            "responsible_user_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        value = " ".join(value.split())
        qs = Studio.objects.filter(deleted_at__isnull=True, name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu nomdagi studiya allaqachon mavjud.")
        return value

    def validate_description(self, value: str) -> str:
        return value.strip()

    def validate_address(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Manzil kiritilishi shart.")
        return value

    def validate_profile_picture(self, value):
        return process_image(value) if value else value


# ------------------------------------------------------------------ public
class PublicStudioSerializer(serializers.ModelSerializer):
    """What customers see about a studio: the business and its portfolio, never its staff or clients."""

    images = StudioImageSerializer(many=True, read_only=True)
    stats = serializers.SerializerMethodField()

    class Meta:
        model = Studio
        fields = ["id", "name", "description", "profile_picture", "address", "phone_number", "images", "stats"]
        read_only_fields = fields

    @extend_schema_field(StatsSerializer)
    def get_stats(self, studio) -> dict:
        stats = self.context.get("stats")
        if stats is None:
            stats = stats_map(TargetKind.STUDIO, [studio.pk])
        return stats.get(studio.pk, empty_stats())


class StudioScheduleSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    busy = serializers.DictField(
        child=serializers.IntegerField(), help_text="{YYYY-MM-DD: shu kuni marosimlar soni} — bo'sh kunlar yo'q."
    )


class StudioCalendarEntrySerializer(serializers.Serializer):
    """Panel view of a studio's ceremonies in a date range."""

    id = serializers.UUIDField()
    title = serializers.CharField()
    event_type = serializers.CharField()
    event_date = serializers.DateField()
    status = serializers.CharField()
