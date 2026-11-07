from datetime import date, timedelta

from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiExample, extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from apps.accounts.models import Role
from apps.accounts.serializers import PhoneNumberField
from apps.studios.models import Studio

from . import services
from .models import STUDIO_TRANSITIONS, AccessStatus, Ceremony, CeremonyParticipant, CeremonyStatus

MAX_FUTURE = timedelta(days=5 * 365)


class StudioBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Studio
        fields = ["id", "name", "profile_picture", "address"]
        read_only_fields = fields


class MyStudioSerializer(serializers.ModelSerializer):
    """A studio as seen by one of its members (no responsible user PII)."""

    class Meta:
        model = Studio
        fields = ["id", "name", "description", "profile_picture", "address", "is_active", "created_at"]
        read_only_fields = fields


class StudioMembershipMeSerializer(serializers.Serializer):
    role = serializers.CharField()
    can_manage = serializers.BooleanField()
    studio = MyStudioSerializer()
    ceremonies_count = serializers.IntegerField()


# ------------------------------------------------------------- studio side
@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Marosim yaratish",
            value={"title": "Dilnoza & Jasur to'yi", "event_date": "2026-09-12", "description": "Toshkent, Navro'z"},
            request_only=True,
        )
    ]
)
class CeremonySerializer(serializers.ModelSerializer):
    studio = StudioBriefSerializer(read_only=True)
    studio_id = serializers.PrimaryKeyRelatedField(
        source="studio",
        queryset=Studio.objects.filter(deleted_at__isnull=True, is_active=True),
        write_only=True,
        required=False,
        help_text="Super Admin uchun majburiy; studiya a'zosi bitta studiyada bo'lsa ixtiyoriy.",
    )
    participants_summary = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Ceremony
        fields = [
            "id",
            "studio",
            "studio_id",
            "title",
            "event_type",
            "event_date",
            "description",
            "status",
            "participants_summary",
            "can_manage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"description": {"required": False, "allow_blank": True}}

    def _user(self):
        return self.context["request"].user

    @extend_schema_field(serializers.DictField(child=serializers.IntegerField()))
    def get_participants_summary(self, obj) -> dict:
        counts = obj.participants.aggregate(
            invited=Count("id", filter=Q(access_status=AccessStatus.INVITED)),
            active=Count("id", filter=Q(access_status=AccessStatus.ACTIVE)),
        )
        return counts

    def get_can_manage(self, obj) -> bool:
        return services.can_manage(self._user(), obj)

    def validate_title(self, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Sarlavha kiritilishi shart.")
        return value

    def validate_description(self, value: str) -> str:
        return value.strip()

    def validate_event_date(self, value: date) -> date:
        if value > date.today() + MAX_FUTURE:
            raise serializers.ValidationError("Sana juda uzoq kelajakda.")
        return value

    def validate(self, attrs):
        user = self._user()
        creating = self.instance is None
        if creating:
            studio = attrs.get("studio")
            if user.role == Role.SUPER_ADMIN:
                if studio is None:
                    raise serializers.ValidationError({"studio_id": ["Studiyani tanlang."]})
            else:
                managed = services.studio_ids(user, managing_only=True)
                if studio is None:
                    if len(managed) != 1:
                        raise serializers.ValidationError({"studio_id": ["Qaysi studiya uchunligini tanlang."]})
                    attrs["studio"] = Studio.objects.get(pk=managed[0])
                elif studio.pk not in managed:
                    # Same message as a missing studio: do not confirm other studios exist.
                    raise serializers.ValidationError({"studio_id": ["Studiya topilmadi."]})
        else:
            attrs.pop("studio", None)  # a ceremony never moves between studios

        new_status = attrs.get("status")
        if new_status is not None:
            current = self.instance.status if self.instance else CeremonyStatus.DRAFT
            if creating and new_status != CeremonyStatus.DRAFT and user.role != Role.SUPER_ADMIN:
                raise serializers.ValidationError({"status": ["Yangi marosim DRAFT holatida yaratiladi."]})
            if (
                not creating
                and new_status != current
                and user.role != Role.SUPER_ADMIN
                and new_status not in STUDIO_TRANSITIONS.get(current, frozenset())
            ):
                raise serializers.ValidationError({"status": [f"{current} → {new_status} o'tishi mumkin emas."]})
        return attrs


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Kelinni taklif qilish",
            value={"phone_number": "+998901234567", "participant_type": "BRIDE"},
            request_only=True,
        )
    ]
)
class ParticipantSerializer(serializers.ModelSerializer):
    """Studio view of an invitation. The person's name appears only after they accept."""

    phone_number = PhoneNumberField()
    display_name = serializers.SerializerMethodField()
    invited_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = CeremonyParticipant
        fields = [
            "id",
            "phone_number",
            "participant_type",
            "access_status",
            "display_name",
            "invited_at",
            "responded_at",
        ]
        read_only_fields = ["id", "access_status", "display_name", "invited_at", "responded_at"]

    def get_display_name(self, obj) -> str | None:
        if obj.access_status == AccessStatus.ACTIVE and obj.user_id:
            return obj.user.full_name or None
        return None


# --------------------------------------------------------------- couple side
class CoupleMemberSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CeremonyParticipant
        fields = ["participant_type", "full_name"]
        read_only_fields = fields

    def get_full_name(self, obj) -> str | None:
        return obj.user.full_name or None if obj.user_id else None


class MyCeremonySerializer(serializers.ModelSerializer):
    """A ceremony as its bride/groom/guest sees it: no phone numbers, no internal fields."""

    studio = StudioBriefSerializer(read_only=True)
    my_role = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()

    class Meta:
        model = Ceremony
        fields = [
            "id",
            "title",
            "event_type",
            "event_date",
            "description",
            "status",
            "studio",
            "my_role",
            "participants",
        ]
        read_only_fields = fields

    def get_my_role(self, obj) -> str | None:
        user = self.context["request"].user
        row = next((p for p in obj.participants.all() if p.user_id == user.pk), None)
        return row.participant_type if row else None

    @extend_schema_field(CoupleMemberSerializer(many=True))
    def get_participants(self, obj):
        active = [p for p in obj.participants.all() if p.access_status == AccessStatus.ACTIVE]
        return CoupleMemberSerializer(active, many=True).data


class InvitationSerializer(serializers.ModelSerializer):
    """Just enough for the invitee to recognise the event before accepting."""

    ceremony_id = serializers.UUIDField(source="ceremony.id", read_only=True)
    ceremony_title = serializers.CharField(source="ceremony.title", read_only=True)
    event_date = serializers.DateField(source="ceremony.event_date", read_only=True)
    studio_name = serializers.CharField(source="ceremony.studio.name", read_only=True)
    invited_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = CeremonyParticipant
        fields = ["id", "participant_type", "ceremony_id", "ceremony_title", "event_date", "studio_name", "invited_at"]
        read_only_fields = fields
