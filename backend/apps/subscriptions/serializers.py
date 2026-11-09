from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import CLIENT_ROLES, User
from apps.studios.models import Studio
from apps.venues.models import Venue

from . import services
from .models import PaymentMethod, Subscription, SubscriptionPlan, SubscriptionSettings

STATES = ["PENDING", "ACTIVE", "SCHEDULED", "EXPIRED", "REJECTED", "CANCELLED"]


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "code",
            "name",
            "audience",
            "duration_months",
            "price",
            "currency",
            "max_viewers",
            "is_active",
            "position",
        ]
        read_only_fields = ["id", "code", "currency", "audience"]
        extra_kwargs = {
            "duration_months": {"min_value": 1, "max_value": 120},
            "max_viewers": {"min_value": 1, "max_value": 1000},
            "position": {"max_value": 1000},
        }


class PlanCreateSerializer(PlanSerializer):
    class Meta(PlanSerializer.Meta):
        read_only_fields = ["id", "currency"]

    def validate_code(self, value: str) -> str:
        value = value.strip().upper()
        if not value.replace("_", "").isalnum():
            raise serializers.ValidationError("Kod faqat harf, raqam va _ dan iborat bo'lsin.")
        if SubscriptionPlan.objects.filter(code=value).exists():
            raise serializers.ValidationError("Bu kod bilan tarif allaqachon mavjud.")
        return value


class _PlanBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()


class MySubscriptionSerializer(serializers.ModelSerializer):
    """What the couple sees about their own purchase (no admin identity)."""

    plan = _PlanBriefSerializer(read_only=True)
    state = serializers.SerializerMethodField()
    studio_name = serializers.CharField(source="studio.name", read_only=True, default=None)
    venue_name = serializers.CharField(source="venue.name", read_only=True, default=None)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "studio",
            "venue",
            "studio_name",
            "venue_name",
            "status",
            "state",
            "price",
            "currency",
            "duration_months",
            "max_viewers",
            "starts_at",
            "ends_at",
            "user_note",
            "admin_note",
            "paid_amount",
            "created_at",
            "decided_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ChoiceField(choices=STATES))
    def get_state(self, obj) -> str:
        return services.state_of(obj)


class BusinessTargetSerializer(serializers.Serializer):
    studio = serializers.PrimaryKeyRelatedField(
        queryset=Studio.objects.filter(deleted_at__isnull=True, is_active=True), required=False, allow_null=True
    )
    venue = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.filter(deleted_at__isnull=True, is_active=True), required=False, allow_null=True
    )


class SubscriptionRequestSerializer(BusinessTargetSerializer):
    plan = serializers.PrimaryKeyRelatedField(queryset=SubscriptionPlan.objects.filter(is_active=True))
    user_note = serializers.CharField(
        max_length=500, required=False, allow_blank=True, help_text="Masalan: qaysi karta orqali, chek raqami."
    )


class MySubscriptionStatusSerializer(serializers.Serializer):
    active = MySubscriptionSerializer(allow_null=True)
    pending = MySubscriptionSerializer(allow_null=True)
    paid_until = serializers.DateTimeField(allow_null=True)
    clean_access = serializers.BooleanField(help_text="Logosiz ko'rish va yuklab olish")
    is_verified = serializers.BooleanField()
    purchase_enabled = serializers.BooleanField()
    viewer_limit = serializers.IntegerField()
    payment_instructions = serializers.CharField()
    plans = PlanSerializer(many=True)


class SubscriptionTargetSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    kind = serializers.ChoiceField(choices=["studio", "venue"])


# ------------------------------------------------------------------ admin
class _UserBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    phone_number = serializers.CharField()


class AdminSubscriptionSerializer(MySubscriptionSerializer):
    user = _UserBriefSerializer(read_only=True)
    decided_by = _UserBriefSerializer(read_only=True, allow_null=True)

    class Meta(MySubscriptionSerializer.Meta):
        fields = MySubscriptionSerializer.Meta.fields + [
            "user",
            "payment_method",
            "payment_reference",
            "paid_at",
            "decided_by",
        ]
        read_only_fields = fields


class PaymentSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, required=False, allow_blank=True)
    paid_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    payment_reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    paid_at = serializers.DateTimeField(required=False, allow_null=True)
    admin_note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class GrantSerializer(PaymentSerializer, BusinessTargetSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role__in=CLIENT_ROLES, is_active=True, deleted_at__isnull=True), source="user"
    )
    plan = serializers.PrimaryKeyRelatedField(queryset=SubscriptionPlan.objects.filter(is_active=True))


class AdminNoteSerializer(serializers.Serializer):
    admin_note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionSettings
        fields = ["payment_instructions", "updated_at"]
        read_only_fields = ["updated_at"]


class SummarySerializer(serializers.Serializer):
    pending = serializers.IntegerField()
    active = serializers.IntegerField()
    revenue_month = serializers.DecimalField(max_digits=16, decimal_places=2)
    revenue_total = serializers.DecimalField(max_digits=16, decimal_places=2)
