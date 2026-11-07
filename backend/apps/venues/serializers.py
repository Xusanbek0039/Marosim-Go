from drf_spectacular.utils import OpenApiExample, extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from apps.accounts.serializers import PhoneNumberField
from apps.core.uploads import process_image

from . import services
from .models import MembershipRole, Venue, VenueHall, VenueMembership

#: Explicit ceiling: without it DRF copies the DB's integer range into the schema
#: (SQLite 2**63-1 vs PostgreSQL 2**31-1), so the API contract would depend on the database.
MAX_CAPACITY = 100_000


class VenueHallSerializer(serializers.ModelSerializer):
    effective_base_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = VenueHall
        fields = [
            "id",
            "name",
            "capacity",
            "base_price",
            "effective_base_price",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "capacity": {"min_value": 1, "max_value": MAX_CAPACITY},
            "base_price": {"help_text": "Bo'sh (null) bo'lsa to'yxonaning base_price narxi ishlatiladi."},
        }

    def validate_name(self, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Zal nomi kiritilishi shart.")
        venue = self.context["venue"]
        qs = VenueHall.objects.filter(venue=venue, deleted_at__isnull=True, name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu to'yxonada shu nomdagi zal allaqachon bor.")
        return value


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "To'yxona yaratish",
            value={
                "name": "Navro'z to'yxonasi",
                "address": "Toshkent, Chilonzor 9-kvartal",
                "region": "TASHKENT_CITY",
                "district": "Chilonzor",
                "phone_number": "+998901234567",
                "capacity_min": 100,
                "capacity_max": 600,
                "base_price": "45000000.00",
            },
            request_only=True,
        )
    ]
)
class OwnerVenueSerializer(serializers.ModelSerializer):
    """A venue as seen by its own members. ``is_active`` / ``publication_status`` are read-only here."""

    phone_number = PhoneNumberField(required=False, allow_blank=True)
    cover_image = serializers.ImageField(required=False, allow_null=True)
    halls = serializers.SerializerMethodField()
    membership_role = serializers.SerializerMethodField()
    membership_capabilities = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = [
            "id",
            "name",
            "description",
            "venue_type",
            "address",
            "region",
            "district",
            "latitude",
            "longitude",
            "phone_number",
            "cover_image",
            "capacity_min",
            "capacity_max",
            "base_price",
            "currency",
            "is_active",
            "publication_status",
            "halls",
            "membership_role",
            "membership_capabilities",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "currency", "is_active", "publication_status", "created_at", "updated_at"]
        extra_kwargs = {
            "description": {"required": False, "allow_blank": True},
            "capacity_min": {"max_value": MAX_CAPACITY},
            "capacity_max": {"min_value": 1, "max_value": MAX_CAPACITY},
        }

    # ------------------------------------------------------------ read side
    def _membership(self, venue):
        cache = self.context.setdefault("_memberships", {})
        if venue.pk not in cache:
            cache[venue.pk] = services.membership_of(self.context["request"].user, venue)
        return cache[venue.pk]

    @extend_schema_field(VenueHallSerializer(many=True))
    def get_halls(self, venue):
        halls = [h for h in venue.halls.all() if h.deleted_at is None]
        return VenueHallSerializer(halls, many=True, context={**self.context, "venue": venue}).data

    @extend_schema_field(serializers.ChoiceField(choices=MembershipRole.choices, allow_null=True))
    def get_membership_role(self, venue):
        membership = self._membership(venue)
        return membership.role if membership else None

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_membership_capabilities(self, venue):
        return sorted(services.capabilities_for(self.context["request"].user, venue))

    # ----------------------------------------------------------- write side
    def validate_name(self, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Nomi kiritilishi shart.")
        return value

    def validate_address(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Manzil kiritilishi shart.")
        return value

    def validate_district(self, value: str) -> str:
        return " ".join(value.split())

    def validate_description(self, value: str) -> str:
        return value.strip()

    def validate_cover_image(self, value):
        return process_image(value) if value else value

    def validate(self, attrs):
        cap_min = attrs.get("capacity_min", getattr(self.instance, "capacity_min", 0))
        cap_max = attrs.get("capacity_max", getattr(self.instance, "capacity_max", None))
        if cap_max is not None and cap_min > cap_max:
            raise serializers.ValidationError(
                {"capacity_min": ["capacity_min capacity_max dan katta bo'lmasligi kerak."]}
            )
        lat = attrs.get("latitude", getattr(self.instance, "latitude", None))
        lon = attrs.get("longitude", getattr(self.instance, "longitude", None))
        if (lat is None) != (lon is None):
            raise serializers.ValidationError({"latitude": ["latitude va longitude birga kiritilishi kerak."]})
        return attrs


# ------------------------------------------------------------- members
class MemberUserSerializer(serializers.Serializer):
    """A colleague as other venue owners see them: no JSHSHIR, email or address."""

    id = serializers.UUIDField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    phone_number = serializers.CharField(read_only=True)


class VenueMemberSerializer(serializers.ModelSerializer):
    user = MemberUserSerializer(read_only=True)

    class Meta:
        model = VenueMembership
        fields = ["id", "user", "role", "is_active", "created_at", "updated_at"]
        read_only_fields = fields


class VenueMemberCreateSerializer(serializers.Serializer):
    phone_number = PhoneNumberField(help_text="Faol VENUE_OWNER hisobining login telefon raqami.")
    role = serializers.ChoiceField(choices=MembershipRole.choices)


class VenueMemberUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=MembershipRole.choices, required=False)
    is_active = serializers.BooleanField(required=False)
