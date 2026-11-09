from drf_spectacular.utils import OpenApiExample, extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.accounts.serializers import PhoneNumberField
from apps.core.uploads import process_image
from apps.reviews.models import TargetKind
from apps.reviews.serializers import StatsSerializer
from apps.reviews.services import empty_stats, stats_map
from apps.subscriptions.badges import PaidBadgeSerializer

from . import scheduling, services
from .models import (
    BookingEventType,
    BookingStatus,
    HallBooking,
    HallSession,
    MembershipRole,
    PublicationStatus,
    Venue,
    VenueHall,
    VenueImage,
    VenueMembership,
)

#: Explicit ceiling: without it DRF copies the DB's integer range into the schema
#: (SQLite 2**63-1 vs PostgreSQL 2**31-1), so the API contract would depend on the database.
MAX_CAPACITY = 100_000


class VenueImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueImage
        fields = ["id", "image", "position", "created_at"]
        read_only_fields = fields


class VenueImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField(help_text="JPG / PNG / WEBP, 5 MB gacha. WEBP'ga qayta kodlanadi, EXIF o'chiriladi.")


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

    def create(self, validated_data):
        hall = super().create(validated_data)
        scheduling.create_default_sessions(hall)  # every new hall starts with Nahor / Kunduzgi / Kechki
        return hall


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
class OwnerVenueSerializer(PaidBadgeSerializer, serializers.ModelSerializer):
    """A venue as seen by its own members. ``is_active`` / ``publication_status`` are read-only here."""

    phone_number = PhoneNumberField(required=False, allow_blank=True)
    cover_image = serializers.ImageField(required=False, allow_null=True)
    halls = serializers.SerializerMethodField()
    images = VenueImageSerializer(many=True, read_only=True)
    membership_role = serializers.SerializerMethodField()
    membership_capabilities = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = [
            "is_verified",
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
            "images",
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


# ------------------------------------------------------------- admin panel
class VenueOwnerBriefSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField(source="id")
    user_id = serializers.UUIDField(source="user.id")
    full_name = serializers.CharField(source="user.full_name")
    phone_number = serializers.CharField(source="user.phone_number")
    role = serializers.ChoiceField(choices=MembershipRole.choices)
    is_active = serializers.BooleanField()


class AdminVenueSerializer(OwnerVenueSerializer):
    """A venue in the Super Admin / Admin panel: everything, incl. block and publication status.

    Changing ``publication_status`` additionally needs ``venues.publish`` (checked in the view).
    """

    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=Role.VENUE_OWNER, is_active=True, deleted_at__isnull=True),
        write_only=True,
        required=False,
        help_text="Yaratishda majburiy: to'yxona egasi (faol VENUE_OWNER hisobi).",
    )
    members = serializers.SerializerMethodField()

    class Meta(OwnerVenueSerializer.Meta):
        fields = [
            f for f in OwnerVenueSerializer.Meta.fields if f not in ("membership_role", "membership_capabilities")
        ] + ["owner_id", "members"]
        read_only_fields = ["id", "currency", "created_at", "updated_at"]

    @extend_schema_field(VenueOwnerBriefSerializer(many=True))
    def get_members(self, venue):
        rows = [m for m in venue.memberships.all()]
        return VenueOwnerBriefSerializer(rows, many=True).data

    def validate_publication_status(self, value):
        if value not in PublicationStatus.values:
            raise serializers.ValidationError("Noma'lum holat.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is None and "owner_id" not in attrs:
            raise serializers.ValidationError({"owner_id": ["To'yxona egasini tanlang."]})
        return attrs


# ------------------------------------------------------------ schedule
class HallSessionSerializer(serializers.ModelSerializer):
    """A hall's recurring slot. ``context["hall"]`` is required for writes (overlap check)."""

    class Meta:
        model = HallSession
        fields = ["id", "name", "starts_at", "ends_at", "is_active"]
        read_only_fields = ["id"]

    def validate_name(self, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Smena nomi kiritilishi shart.")
        return value

    def validate(self, attrs):
        starts = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        active = attrs.get("is_active", getattr(self.instance, "is_active", True))
        if active and starts is not None and ends is not None:
            scheduling.validate_session_window(
                self.context["hall"], starts, ends, exclude_pk=getattr(self.instance, "pk", None)
            )
        return attrs


class _HallBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class _SessionBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    starts_at = serializers.TimeField()
    ends_at = serializers.TimeField()


class _RequesterSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    phone_number = serializers.CharField()


class OwnerBookingSerializer(serializers.ModelSerializer):
    """A calendar entry as the venue sees it: incl. the couple's contact and the internal note."""

    hall = _HallBriefSerializer(read_only=True)
    session = _SessionBriefSerializer(read_only=True)
    requester = _RequesterSerializer(read_only=True, allow_null=True)

    class Meta:
        model = HallBooking
        fields = [
            "id",
            "hall",
            "session",
            "date",
            "status",
            "source",
            "event_type",
            "guest_count",
            "requester",
            "contact_name",
            "contact_phone",
            "note",
            "venue_note",
            "quoted_price",
            "currency",
            "decided_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OwnerBookingCreateSerializer(serializers.Serializer):
    session = serializers.UUIDField()
    date = serializers.DateField()
    status = serializers.ChoiceField(
        choices=[BookingStatus.CONFIRMED, BookingStatus.BLOCKED],
        default=BookingStatus.CONFIRMED,
        help_text="CONFIRMED — to'yxonaning o'z mijozi; BLOCKED — smena yopiq (ta'mir, dam olish…).",
    )
    event_type = serializers.ChoiceField(choices=BookingEventType.choices, required=False)
    guest_count = serializers.IntegerField(min_value=1, max_value=MAX_CAPACITY, required=False, allow_null=True)
    contact_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    contact_phone = PhoneNumberField(required=False, allow_blank=True)
    venue_note = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class OwnerBookingUpdateSerializer(serializers.ModelSerializer):
    contact_phone = PhoneNumberField(required=False, allow_blank=True)

    class Meta:
        model = HallBooking
        fields = ["event_type", "guest_count", "contact_name", "contact_phone", "venue_note"]
        extra_kwargs = {"guest_count": {"min_value": 1, "max_value": MAX_CAPACITY}}


class BookingDecisionSerializer(serializers.Serializer):
    venue_note = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class OwnerCalendarHallSerializer(serializers.ModelSerializer):
    sessions = HallSessionSerializer(many=True, read_only=True)

    class Meta:
        model = VenueHall
        fields = ["id", "name", "capacity", "is_active", "sessions"]
        read_only_fields = fields


class OwnerCalendarSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    halls = OwnerCalendarHallSerializer(many=True)
    bookings = OwnerBookingSerializer(many=True)


# -------------------------------------------------------------- public
class PublicVenueSerializer(PaidBadgeSerializer, serializers.ModelSerializer):
    """What anyone may see about an approved venue — the business, never its customers."""

    images = VenueImageSerializer(many=True, read_only=True)
    stats = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = [
            "is_verified",
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
            "images",
            "stats",
        ]
        read_only_fields = fields

    @extend_schema_field(StatsSerializer)
    def get_stats(self, venue) -> dict:
        """Rating / likes; list views pass a precomputed ``stats`` map in the context (no N+1)."""
        stats = self.context.get("stats")
        if stats is None:
            stats = stats_map(TargetKind.VENUE, [venue.pk])
        return stats.get(venue.pk, empty_stats())


class PublicSlotSerializer(_SessionBriefSerializer):
    is_free = serializers.BooleanField()


class PublicHallSlotsSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    capacity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=14, decimal_places=2)
    slots = PublicSlotSerializer(many=True)


class VenueSearchResultSerializer(serializers.Serializer):
    venue = PublicVenueSerializer()
    halls = PublicHallSlotsSerializer(many=True)
    free_slots = serializers.IntegerField()


class PublicHallSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    capacity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=14, decimal_places=2)
    sessions = _SessionBriefSerializer(many=True)


class PublicVenueDetailSerializer(serializers.Serializer):
    venue = PublicVenueSerializer()
    halls = PublicHallSerializer(many=True)


class VenueAvailabilitySerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    free = serializers.DictField(
        child=serializers.DictField(child=serializers.ListField(child=serializers.UUIDField())),
        help_text="{hall_id: {YYYY-MM-DD: [bo'sh smena id'lari]}} — band yoki o'tgan kunlar ro'yxatda yo'q.",
    )


# ----------------------------------------------------- my (couple) bookings
class _VenueBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    address = serializers.CharField()
    phone_number = serializers.CharField()


class MyBookingSerializer(serializers.ModelSerializer):
    venue = _VenueBriefSerializer(source="hall.venue", read_only=True)
    hall = _HallBriefSerializer(read_only=True)
    session = _SessionBriefSerializer(read_only=True)

    class Meta:
        model = HallBooking
        fields = [
            "id",
            "venue",
            "hall",
            "session",
            "date",
            "status",
            "event_type",
            "guest_count",
            "contact_phone",
            "note",
            "quoted_price",
            "currency",
            "decided_at",
            "created_at",
        ]
        read_only_fields = fields


class MyBookingCreateSerializer(serializers.Serializer):
    session = serializers.UUIDField(help_text="Zal smenasining id'si (qidiruv natijasidagi slots[].id).")
    date = serializers.DateField()
    event_type = serializers.ChoiceField(choices=BookingEventType.choices, required=False)
    guest_count = serializers.IntegerField(min_value=1, max_value=MAX_CAPACITY, required=False, allow_null=True)
    contact_phone = PhoneNumberField(required=False, allow_blank=True)
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True)
