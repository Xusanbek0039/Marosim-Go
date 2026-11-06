from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.accounts.serializers import UserSummarySerializer
from apps.core.uploads import process_image

from .models import Studio


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

    class Meta:
        model = Studio
        fields = [
            "id",
            "name",
            "profile_picture",
            "address",
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

    def validate_address(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Manzil kiritilishi shart.")
        return value

    def validate_profile_picture(self, value):
        return process_image(value) if value else value
