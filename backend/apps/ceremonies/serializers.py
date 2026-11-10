from datetime import date, timedelta

from django.db.models import Prefetch
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from apps.accounts.models import Role
from apps.accounts.serializers import PhoneNumberField
from apps.studios.models import Studio
from apps.subscriptions.badges import PaidBadgeSerializer

from . import ownership, services
from .invitations import LEGACY_FROM_OWNER_TYPE
from .models import (
    STUDIO_TRANSITIONS,
    AccessDuration,
    AccessRole,
    Ceremony,
    CeremonyInvitation,
    CeremonyOwnership,
    CeremonyStatus,
    CeremonyViewerAccess,
    IdentifierType,
    InvitationStatus,
    InviterKind,
    OwnershipStatus,
    OwnerType,
    ParticipantType,
)

MAX_FUTURE = timedelta(days=5 * 365)
LEGACY_TYPES = ParticipantType.choices  # v1 vocabulary (BRIDE / GROOM / OTHER)


class StudioBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Studio
        fields = ["id", "name", "profile_picture", "address"]
        read_only_fields = fields


class MyStudioSerializer(PaidBadgeSerializer, serializers.ModelSerializer):
    """A studio as seen by one of its members (no responsible user PII)."""

    class Meta:
        model = Studio
        fields = ["is_verified", "id", "name", "description", "profile_picture", "address", "is_active", "created_at"]
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
        """Owners only (viewers are the owners' private sharing): open owner invitations / accepted owners."""
        invited = obj.invitations.filter(
            requested_role=AccessRole.OWNER, status=InvitationStatus.PENDING, expires_at__gt=timezone.now()
        ).count()
        active = obj.ownerships.filter(status=OwnershipStatus.ACCEPTED).count()
        return {"invited": invited, "active": active}

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


# ------------------------------------------------------------ shared bits
def effective_status(invitation: CeremonyInvitation) -> str:
    """PENDING past its expiry is reported as EXPIRED even before the sweeper marks it."""
    if invitation.status == InvitationStatus.PENDING and invitation.expires_at <= timezone.now():
        return InvitationStatus.EXPIRED
    return invitation.status


def ownership_of(invitation: CeremonyInvitation) -> CeremonyOwnership | None:
    try:
        return invitation.ownership
    except CeremonyOwnership.DoesNotExist:
        return None


def inviter_display(invitation: CeremonyInvitation) -> str | None:
    if invitation.inviter_kind == InviterKind.STUDIO:
        return invitation.ceremony.studio.name
    if invitation.inviter_kind == InviterKind.SUPER_ADMIN:
        return "MarosimGo"
    return _name(invitation.invited_by)


def _name(user) -> str | None:
    return (user.full_name or None) if user else None


def _dt(value):
    return serializers.DateTimeField().to_representation(value) if value else None


# ------------------------------------------------- studio: v1 participants
@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Kelinni taklif qilish",
            value={"phone_number": "+998901234567", "participant_type": "BRIDE"},
            request_only=True,
        )
    ]
)
class ParticipantSerializer(serializers.Serializer):
    """v1 shape of a studio OWNER invitation (deprecated ``/participants/``). The number comes back
    masked; the person's name appears only once their ownership is ACCEPTED."""

    id = serializers.UUIDField(read_only=True)
    phone_number = PhoneNumberField(help_text="Javobda maskalangan: +99890***4567")
    participant_type = serializers.ChoiceField(choices=LEGACY_TYPES)
    access_status = serializers.ChoiceField(choices=["INVITED", "ACTIVE", "DECLINED", "REVOKED"], read_only=True)
    display_name = serializers.CharField(read_only=True, allow_null=True)
    invited_at = serializers.DateTimeField(read_only=True)
    responded_at = serializers.DateTimeField(read_only=True, allow_null=True)

    def to_representation(self, invitation: CeremonyInvitation):
        row = ownership_of(invitation)
        if invitation.status == InvitationStatus.PENDING:
            legacy = "INVITED"
        elif invitation.status == InvitationStatus.ACCEPTED:
            legacy = {OwnershipStatus.ACCEPTED: "ACTIVE", OwnershipStatus.PENDING: "INVITED"}.get(
                row.status if row else None, "REVOKED"
            )
        elif invitation.status == InvitationStatus.DECLINED:
            legacy = "DECLINED"
        else:
            legacy = "REVOKED"
        return {
            "id": str(invitation.pk),
            "phone_number": invitation.recipient_hint,
            "participant_type": LEGACY_FROM_OWNER_TYPE[invitation.owner_type],
            "access_status": legacy,
            "display_name": _name(row.user) if row and row.status == OwnershipStatus.ACCEPTED else None,
            "invited_at": _dt(invitation.created_at),
            "responded_at": _dt(invitation.responded_at),
        }


# ------------------------------------------------------- studio: owners
@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Kelinni telefon orqali taklif qilish",
            value={"identifier_type": "PHONE", "identifier": "+998901234567", "owner_type": "BRIDE"},
            request_only=True,
        )
    ]
)
class OwnerInviteSerializer(serializers.Serializer):
    identifier_type = serializers.ChoiceField(choices=IdentifierType.choices)
    identifier = serializers.CharField(
        write_only=True, max_length=32, help_text="Telefon (+998XXXXXXXXX) yoki 14 xonali JSHSHIR. Javobda qaytmaydi."
    )
    owner_type = serializers.ChoiceField(choices=OwnerType.choices)


class StudioOwnerRowSerializer(serializers.ModelSerializer):
    """An OWNER invitation and what became of it, as the studio sees it (masked identifier only)."""

    status = serializers.SerializerMethodField()
    ownership_status = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    invited_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = CeremonyInvitation
        fields = [
            "id",
            "identifier_type",
            "recipient_hint",
            "owner_type",
            "status",
            "ownership_status",
            "display_name",
            "inviter_kind",
            "invited_at",
            "expires_at",
            "responded_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ChoiceField(choices=InvitationStatus.choices))
    def get_status(self, obj) -> str:
        return effective_status(obj)

    @extend_schema_field(serializers.ChoiceField(choices=OwnershipStatus.choices, allow_null=True))
    def get_ownership_status(self, obj) -> str | None:
        row = ownership_of(obj)
        return row.status if row else None

    def get_display_name(self, obj) -> str | None:
        row = ownership_of(obj)
        return _name(row.user) if row and row.status == OwnershipStatus.ACCEPTED else None


# --------------------------------------------------------------- user side
class OwnerBriefSerializer(serializers.ModelSerializer):
    participant_type = serializers.SerializerMethodField(help_text="v1 qiymati (BRIDE / GROOM / OTHER)")
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CeremonyOwnership
        fields = ["participant_type", "owner_type", "full_name"]
        read_only_fields = fields

    @extend_schema_field(serializers.ChoiceField(choices=LEGACY_TYPES))
    def get_participant_type(self, obj) -> str:
        return LEGACY_FROM_OWNER_TYPE[obj.owner_type]

    def get_full_name(self, obj) -> str | None:
        return _name(obj.user)


def with_owners(qs):
    """Prefetch accepted owners for ``MyCeremonySerializer``."""
    return qs.select_related("studio").prefetch_related(
        Prefetch(
            "ownerships",
            queryset=CeremonyOwnership.objects.filter(status=OwnershipStatus.ACCEPTED)
            .select_related("user")
            .order_by("accepted_at"),
            to_attr="accepted_owners",
        )
    )


class MyCeremonySerializer(serializers.ModelSerializer):
    """A ceremony as an owner / viewer sees it: no phone numbers, JSHSHIR or internal fields."""

    studio = StudioBriefSerializer(read_only=True)
    access_role = serializers.SerializerMethodField()
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
            "access_role",
            "my_role",
            "participants",
        ]
        read_only_fields = fields

    def _mine(self, obj):
        user = self.context["request"].user
        return next((o for o in obj.accepted_owners if o.user_id == user.pk), None)

    @extend_schema_field(serializers.ChoiceField(choices=AccessRole.choices))
    def get_access_role(self, obj) -> str:
        return AccessRole.OWNER if self._mine(obj) else AccessRole.VIEWER

    @extend_schema_field(serializers.ChoiceField(choices=LEGACY_TYPES, allow_null=True))
    def get_my_role(self, obj) -> str | None:
        """v1: owner's participant type; ``null`` for viewers (see ``access_role``)."""
        mine = self._mine(obj)
        return LEGACY_FROM_OWNER_TYPE[mine.owner_type] if mine else None

    @extend_schema_field(OwnerBriefSerializer(many=True))
    def get_participants(self, obj):
        return OwnerBriefSerializer(obj.accepted_owners, many=True).data


class InvitationSerializer(serializers.ModelSerializer):
    """What the invitee sees before answering. While the invitation still needs a verified phone,
    the ceremony details are withheld, so a squatted number reveals nothing."""

    participant_type = serializers.SerializerMethodField(help_text="v1 qiymati; VIEWER uchun null")
    ceremony_id = serializers.UUIDField(source="ceremony.id", read_only=True)
    ceremony_title = serializers.SerializerMethodField()
    event_date = serializers.SerializerMethodField()
    studio_name = serializers.SerializerMethodField()
    inviter_display = serializers.SerializerMethodField()
    invited_at = serializers.DateTimeField(source="created_at", read_only=True)
    phone_verification_required = serializers.SerializerMethodField()
    requires_owner_approval = serializers.SerializerMethodField()

    class Meta:
        model = CeremonyInvitation
        fields = [
            "id",
            "requested_role",
            "owner_type",
            "access_duration",
            "participant_type",
            "ceremony_id",
            "ceremony_title",
            "event_date",
            "studio_name",
            "inviter_display",
            "invited_at",
            "expires_at",
            "phone_verification_required",
            "requires_owner_approval",
        ]
        read_only_fields = fields

    def _hidden(self, obj) -> bool:
        return ownership.requires_verified_phone(obj) and not self.context["request"].user.is_phone_verified

    @extend_schema_field(serializers.ChoiceField(choices=LEGACY_TYPES, allow_null=True))
    def get_participant_type(self, obj) -> str | None:
        return LEGACY_FROM_OWNER_TYPE[obj.owner_type] if obj.owner_type else None

    def get_ceremony_title(self, obj) -> str | None:
        return None if self._hidden(obj) else obj.ceremony.title

    def get_event_date(self, obj) -> date | None:
        return None if self._hidden(obj) else obj.ceremony.event_date

    def get_studio_name(self, obj) -> str | None:
        return None if self._hidden(obj) else obj.ceremony.studio.name

    def get_inviter_display(self, obj) -> str | None:
        return None if self._hidden(obj) else inviter_display(obj)

    def get_phone_verification_required(self, obj) -> bool:
        return self._hidden(obj)

    def get_requires_owner_approval(self, obj) -> bool:
        """OWNER: after accepting, the ceremony's current owners must approve."""
        return obj.requested_role == AccessRole.OWNER and bool(ownership.approvers_for(obj.ceremony))


class AcceptResultSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["ACCEPTED", "PENDING_APPROVAL"],
        help_text="PENDING_APPROVAL: egalik marosimning mavjud egalari tasdiqlagandan keyin ochiladi.",
    )
    access_role = serializers.ChoiceField(choices=AccessRole.choices)
    ceremony = MyCeremonySerializer(allow_null=True, help_text="Kirish ochilgan bo'lsa (va marosim DRAFT emas).")


# ----------------------------------------------------------------- owner side
class MemberOwnerSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    is_me = serializers.SerializerMethodField()

    class Meta:
        model = CeremonyOwnership
        fields = ["id", "owner_type", "full_name", "is_me", "accepted_at"]
        read_only_fields = fields

    def get_full_name(self, obj) -> str | None:
        return _name(obj.user)

    def get_is_me(self, obj) -> bool:
        return obj.user_id == self.context["request"].user.pk


class MemberViewerSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    granted_by_name = serializers.SerializerMethodField()
    granted_by_me = serializers.SerializerMethodField()
    can_revoke = serializers.SerializerMethodField()

    class Meta:
        model = CeremonyViewerAccess
        fields = ["id", "full_name", "granted_by_name", "granted_by_me", "can_revoke", "accepted_at", "expires_at"]
        read_only_fields = fields

    def get_full_name(self, obj) -> str | None:
        return _name(obj.user)

    def get_granted_by_name(self, obj) -> str | None:
        return _name(obj.granted_by)

    def get_granted_by_me(self, obj) -> bool:
        return obj.granted_by_id == self.context["request"].user.pk

    def get_can_revoke(self, obj) -> bool:
        return ownership.can_revoke_viewer(self.context["request"].user, obj)


class MembersSerializer(serializers.Serializer):
    owners = MemberOwnerSerializer(many=True)
    viewers = MemberViewerSerializer(many=True)
    pending_owner_requests = serializers.IntegerField()
    viewer_limit = serializers.IntegerField(help_text="So'rovchi nechta odamga ruxsat bera oladi (obunaga qarab).")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Ko'ruvchini telefon orqali taklif qilish",
            value={"identifier_type": "PHONE", "identifier": "+998901234567", "requested_role": "VIEWER"},
            request_only=True,
        ),
        OpenApiExample(
            "Ota-onani ega sifatida taklif qilish",
            value={
                "identifier_type": "PHONE",
                "identifier": "+998907654321",
                "requested_role": "OWNER",
                "owner_type": "FAMILY_OWNER",
            },
            request_only=True,
        ),
    ]
)
class OwnerInvitationCreateSerializer(serializers.Serializer):
    identifier_type = serializers.ChoiceField(choices=IdentifierType.choices)
    identifier = serializers.CharField(
        write_only=True, max_length=32, help_text="Telefon (+998XXXXXXXXX) yoki 14 xonali JSHSHIR. Javobda qaytmaydi."
    )
    requested_role = serializers.ChoiceField(choices=AccessRole.choices)
    owner_type = serializers.ChoiceField(
        choices=OwnerType.choices, required=False, allow_blank=True, help_text="Faqat OWNER uchun majburiy."
    )
    access_duration = serializers.ChoiceField(
        choices=AccessDuration.choices,
        required=False,
        allow_blank=True,
        help_text="Faqat VIEWER uchun majburiy: qabul qilingandan keyin ko'rish muddati (24H / 3D / 1W / 1M).",
    )


class OwnerInvitationSerializer(serializers.ModelSerializer):
    """One row of a ceremony's invitation history, as an owner sees it (masked identifier only)."""

    status = serializers.SerializerMethodField()
    invited_by_display = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    can_revoke = serializers.SerializerMethodField()
    can_resend = serializers.SerializerMethodField()
    invited_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = CeremonyInvitation
        fields = [
            "id",
            "identifier_type",
            "recipient_hint",
            "requested_role",
            "owner_type",
            "access_duration",
            "status",
            "inviter_kind",
            "invited_by_display",
            "is_mine",
            "can_revoke",
            "can_resend",
            "send_count",
            "invited_at",
            "expires_at",
            "responded_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ChoiceField(choices=InvitationStatus.choices))
    def get_status(self, obj) -> str:
        return effective_status(obj)

    def get_invited_by_display(self, obj) -> str | None:
        return inviter_display(obj)

    def get_is_mine(self, obj) -> bool:
        return obj.invited_by_id == self.context["request"].user.pk

    def get_can_revoke(self, obj) -> bool:
        return ownership.can_revoke_invitation(self.context["request"].user, obj)

    def get_can_resend(self, obj) -> bool:
        return ownership.can_resend_invitation(self.context["request"].user, obj)


class ApprovalBriefSerializer(serializers.Serializer):
    approver_name = serializers.CharField(allow_null=True)
    is_me = serializers.BooleanField()
    decision = serializers.CharField()
    decided_at = serializers.DateTimeField(allow_null=True)


class OwnerRequestSerializer(serializers.ModelSerializer):
    """A PENDING ownership: who accepted which OWNER invitation, and the approvals so far."""

    candidate_name = serializers.SerializerMethodField()
    recipient_hint = serializers.SerializerMethodField()
    invited_by_display = serializers.SerializerMethodField()
    approvals = serializers.SerializerMethodField()
    can_decide = serializers.SerializerMethodField()

    class Meta:
        model = CeremonyOwnership
        fields = [
            "id",
            "owner_type",
            "status",
            "candidate_name",
            "recipient_hint",
            "invited_by_display",
            "approvals",
            "can_decide",
            "created_at",
        ]
        read_only_fields = fields

    def get_candidate_name(self, obj) -> str | None:
        return _name(obj.user)

    def get_recipient_hint(self, obj) -> str | None:
        return obj.invitation.recipient_hint if obj.invitation_id else None

    def get_invited_by_display(self, obj) -> str | None:
        return inviter_display(obj.invitation) if obj.invitation_id else None

    @extend_schema_field(ApprovalBriefSerializer(many=True))
    def get_approvals(self, obj):
        me = self.context["request"].user.pk
        return [
            {
                "approver_name": _name(a.approver),
                "is_me": a.approver_id == me,
                "decision": a.decision,
                "decided_at": _dt(a.decided_at),
            }
            for a in obj.approvals.select_related("approver")
        ]

    def get_can_decide(self, obj) -> bool:
        return ownership.can_decide_owner_request(self.context["request"].user, obj)
