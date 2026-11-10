"""Studio, Super Admin and couple / guest endpoints for ceremonies.

Row-level scope (who sees which ceremony) is applied in every ``get_queryset``: a ceremony outside
your scope is a 404, never a 403, so its existence is not confirmed. Studio-side scope lives in
``services``; owner / viewer access in ``ownership`` (rules) and ``invitations`` (flows).
"""

from django.db import transaction
from django.db.models import Count
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.access import AccessNote
from apps.audit.services import AuditAction, diff, record, snapshot
from apps.studios.models import StudioMembership
from apps.studios.services import active_memberships
from apps.subscriptions.services import viewer_limit

from . import folders, invitations, ownership, services
from .models import (
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
)
from .permissions import IsCeremonyMember, IsCeremonyOwner, IsClientUser, IsStudioMember, IsStudioMemberOrSuperAdmin
from .serializers import (
    FolderRenameSerializer,
    FolderResultSerializer,
    AcceptResultSerializer,
    CeremonySerializer,
    InvitationSerializer,
    MembersSerializer,
    MyCeremonySerializer,
    OwnerInvitationCreateSerializer,
    OwnerInvitationSerializer,
    OwnerInviteSerializer,
    OwnerRequestSerializer,
    ParticipantSerializer,
    StudioMembershipMeSerializer,
    StudioOwnerRowSerializer,
    with_owners,
)

AUDITED_FIELDS = ["title", "event_type", "event_date", "description", "status"]
STUDIO_SCOPE = "STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi."
MANAGE_CONDITION = "STUDIO a'zoligi OWNER yoki MANAGER bo'lishi shart (UPLOADER — faqat ko'rish)."
STATUS_FILTER = OpenApiParameter("status", str, enum=[s.value for s in CeremonyStatus], required=False)
UUID_RE = "[0-9a-fA-F-]{36}"

MEMBER_SCOPE = (
    "Faqat so'rovchi ACCEPTED ega (CEREMONY_OWNER) yoki ACCEPTED ko'ruvchi (CEREMONY_VIEWER) bo'lgan, "
    "DRAFT bo'lmagan marosimlar; boshqasi 404. Huquq har so'rovda DB'dan qayta tekshiriladi."
)
OWNER_ONLY = "Faqat marosimning ACCEPTED egasi (CEREMONY_OWNER); ko'ruvchi — 403."
PHONE_VERIFIED_OWNER = "OWNER taklifini qabul qilish uchun telefon tasdiqlangan bo'lishi shart."
NO_ENUMERATION = "Javob oluvchining akkaunti bor-yo'qligiga bog'liq emas; telefon/JSHSHIR faqat maskalangan qaytadi."


# ------------------------------------------------------------------ studio
class StudioMeView(APIView):
    permission_classes = [IsStudioMember]
    access_notes = {"*": AccessNote(ownership="Faqat so'rovchining faol a'zoliklari va ularning studiyalari.")}

    @extend_schema(
        summary="Mening studiyalarim",
        tags=["studio"],
        responses=StudioMembershipMeSerializer(many=True),
    )
    def get(self, request):
        memberships = active_memberships(request.user).annotate(n=Count("studio__ceremonies"))
        data = [
            {
                "role": m.role,
                "can_manage": m.role in StudioMembership.MANAGING_ROLES,
                "studio": m.studio,
                "ceremonies_count": m.n,
            }
            for m in memberships
        ]
        return Response(StudioMembershipMeSerializer(data, many=True, context={"request": request}).data)


class StudioMeCeremoniesView(ListAPIView):
    permission_classes = [IsStudioMember]
    serializer_class = CeremonySerializer
    search_fields = ["title", "description"]
    ordering_fields = ["event_date", "created_at", "title"]
    ordering = ["-event_date"]
    access_notes = {"*": AccessNote(ownership=STUDIO_SCOPE)}

    @extend_schema(
        summary="Mening studiyamning marosimlari",
        tags=["studio"],
        parameters=[STATUS_FILTER, OpenApiParameter("studio", str, required=False)],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # schema generation
            return Ceremony.objects.none()
        qs = services.ceremonies_for(self.request.user)
        params = self.request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("studio"):
            qs = qs.filter(studio_id=params["studio"]) if _is_uuid(params["studio"]) else qs.none()
        return qs


def _is_uuid(value: str) -> bool:
    import uuid

    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _owner_invitations(ceremony):
    return (
        ceremony.invitations.filter(requested_role=AccessRole.OWNER)
        .select_related("ceremony__studio", "invited_by", "ownership__user")
        .order_by("created_at")
    )


# --------------------------------------------------------------- ceremonies
@extend_schema_view(
    list=extend_schema(summary="Marosimlar ro'yxati", tags=["ceremonies"], parameters=[STATUS_FILTER]),
    create=extend_schema(summary="Marosim yaratish", tags=["ceremonies"]),
    retrieve=extend_schema(summary="Marosim ma'lumotlari", tags=["ceremonies"]),
    partial_update=extend_schema(summary="Marosimni tahrirlash", tags=["ceremonies"]),
)
class CeremonyViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CeremonySerializer
    queryset = Ceremony.objects.none()  # typing only; real rows come from get_queryset
    lookup_value_regex = UUID_RE
    permission_classes = [IsStudioMemberOrSuperAdmin]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    search_fields = ["title", "description", "studio__name"]
    ordering_fields = ["event_date", "created_at", "title", "status"]
    ordering = ["-event_date"]
    access_notes = {
        "*": AccessNote(ownership=STUDIO_SCOPE),
        "create": AccessNote(conditions=(MANAGE_CONDITION, "SUPER_ADMIN studio_id ni ko'rsatishi shart.")),
        "partial_update": AccessNote(conditions=(MANAGE_CONDITION, "Holat o'tishlari cheklangan.")),
        "participants": AccessNote(conditions=("Deprecated: /owners/ ishlating.", "POST: " + MANAGE_CONDITION)),
        "remove_participant": AccessNote(
            conditions=(
                "Deprecated.",
                "Javob kutilayotgan taklif: studiya OWNER/MANAGER bekor qiladi.",
                "Tasdiqlangan egani faqat SUPER_ADMIN olib tashlaydi.",
            )
        ),
        "owners_invite": AccessNote(
            conditions=(
                MANAGE_CONDITION,
                "Marosimda egalar bo'lsa, yangi ega ularning tasdig'idan keyin ochiladi.",
                "JSHSHIR orqali faqat egalar bor bo'lganda (birinchi egalar — telefon orqali).",
                NO_ENUMERATION,
            )
        ),
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ceremony.objects.none()
        qs = services.ceremonies_for(self.request.user)
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs

    def get_throttles(self):
        if self.request.method == "POST" and self.action in ("participants", "owners_invite"):
            self.throttle_scope = "ceremony_invite"
            return [*super().get_throttles(), ScopedRateThrottle()]
        return super().get_throttles()

    @transaction.atomic
    def perform_create(self, serializer):
        ceremony = serializer.save(created_by=self.request.user)
        services.ensure_can_manage(self.request.user, ceremony)
        record(self.request, AuditAction.CREATE, ceremony, changes=snapshot(ceremony, AUDITED_FIELDS))

    @transaction.atomic
    def perform_update(self, serializer):
        services.ensure_can_manage(self.request.user, serializer.instance)
        before = snapshot(serializer.instance, AUDITED_FIELDS)
        ceremony = serializer.save()
        changes = diff(before, snapshot(ceremony, AUDITED_FIELDS))
        if changes:
            record(self.request, AuditAction.UPDATE, ceremony, changes=changes)

    # ------------------------------------------------------------ owners
    @extend_schema(
        summary="Marosim egalari va egalik takliflari",
        tags=["ceremonies"],
        responses=StudioOwnerRowSerializer(many=True),
    )
    @action(detail=True, methods=["get"], pagination_class=None, filter_backends=[])
    def owners(self, request, pk=None):
        rows = _owner_invitations(self.get_object())
        return Response(StudioOwnerRowSerializer(rows, many=True).data)

    @extend_schema(
        summary="Marosim egasini telefon yoki JSHSHIR orqali taklif qilish",
        description=(
            "Javob raqam/JSHSHIR ro'yxatdan o'tganmi-yo'qmi bildirmaydi. Taklif o'zi hech qanday huquq bermaydi: "
            "oluvchi tizimga kirib, tasdiqlangan telefon bilan qabul qilishi kerak; marosimda egalar bo'lsa — "
            "ular ham tasdiqlaydi."
        ),
        tags=["ceremonies"],
        request=OwnerInviteSerializer,
        responses={201: StudioOwnerRowSerializer},
    )
    @action(detail=True, methods=["post"], url_path="owners/invite", url_name="owners-invite")
    def owners_invite(self, request, pk=None):
        ceremony = self.get_object()
        serializer = OwnerInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = invitations.create_invitation(
            request,
            ceremony,
            requested_role=AccessRole.OWNER,
            allowed_kinds=(InviterKind.STUDIO, InviterKind.SUPER_ADMIN),
            **serializer.validated_data,
        )
        return Response(StudioOwnerRowSerializer(invitation).data, status=status.HTTP_201_CREATED)

    # --------------------------------------------------- v1 (deprecated)
    @extend_schema(
        methods=["GET"],
        summary="Marosim ishtirokchilari (deprecated — /owners/)",
        tags=["ceremonies"],
        deprecated=True,
        responses=ParticipantSerializer(many=True),
    )
    @extend_schema(
        methods=["POST"],
        summary="Ishtirokchini telefon orqali taklif qilish (deprecated — /owners/invite/)",
        description="v1 shakli: OWNER taklifini yaratadi (OTHER → OTHER_OWNER). Javobda raqam maskalangan.",
        tags=["ceremonies"],
        deprecated=True,
        request=ParticipantSerializer,
        responses={201: ParticipantSerializer},
    )
    @action(detail=True, methods=["get", "post"], pagination_class=None, filter_backends=[])
    def participants(self, request, pk=None):
        ceremony = self.get_object()
        if request.method == "GET":
            rows = _owner_invitations(ceremony).exclude(status__in=(InvitationStatus.REVOKED, InvitationStatus.EXPIRED))
            data = [r for r in ParticipantSerializer(rows, many=True).data if r["access_status"] != "REVOKED"]
            return Response(data)
        serializer = ParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invitation = invitations.create_invitation(
                request,
                ceremony,
                identifier_type=IdentifierType.PHONE,
                identifier=serializer.validated_data["phone_number"],
                requested_role=AccessRole.OWNER,
                owner_type=invitations.OWNER_TYPE_FROM_LEGACY[serializer.validated_data["participant_type"]],
                allowed_kinds=(InviterKind.STUDIO, InviterKind.SUPER_ADMIN),
            )
        except ValidationError as exc:  # map new field names back to the v1 ones
            _rename_error_fields(exc, {"identifier": "phone_number", "owner_type": "participant_type"})
            raise
        return Response(ParticipantSerializer(invitation).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Ishtirokchini olib tashlash (deprecated)",
        tags=["ceremonies"],
        deprecated=True,
        responses={204: None},
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path=rf"participants/(?P<participant_id>{UUID_RE})",
        url_name="remove-participant",
    )
    def remove_participant(self, request, pk=None, participant_id=None):
        ceremony = self.get_object()
        invitation = _owner_invitations(ceremony).filter(pk=participant_id).first()
        if invitation is None:
            raise NotFound()
        if invitation.status == InvitationStatus.PENDING:
            invitations.revoke_invitation(request, invitation)
        else:
            row = CeremonyOwnership.objects.filter(invitation=invitation).first()
            if row is not None and row.status in (OwnershipStatus.PENDING, OwnershipStatus.ACCEPTED):
                invitations.revoke_ownership(request, row)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _rename_error_fields(exc: ValidationError, mapping: dict) -> None:
    if isinstance(exc.detail, dict):
        exc.detail = {mapping.get(k, k): v for k, v in exc.detail.items()}


# --------------------------------------------------------- owner / viewer
@extend_schema_view(
    list=extend_schema(summary="Menga biriktirilgan marosimlar", tags=["me"]),
    retrieve=extend_schema(summary="Menga biriktirilgan marosim", tags=["me"]),
)
class MyCeremonyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MyCeremonySerializer
    queryset = Ceremony.objects.none()
    lookup_value_regex = UUID_RE
    permission_classes = [IsClientUser]
    filter_backends = []
    access_notes = {
        "*": AccessNote(ownership=MEMBER_SCOPE),
        "members": AccessNote(conditions=(OWNER_ONLY,)),
        "invitations": AccessNote(
            conditions=(
                OWNER_ONLY,
                "POST VIEWER: darhol taklif; POST OWNER: qabul qilingach boshqa egalar tasdiqlaydi.",
                "JSHSHIR — faqat identifikator, autentifikatsiya emas.",
                NO_ENUMERATION,
            )
        ),
        "invitation_revoke": AccessNote(conditions=(OWNER_ONLY, "Faqat taklifni o'zi yuborgan ega.")),
        "invitation_resend": AccessNote(conditions=(OWNER_ONLY, "Faqat taklifni o'zi yuborgan ega.")),
        "viewer_revoke": AccessNote(conditions=(OWNER_ONLY, "Faqat ko'rish huquqini o'zi bergan ega.")),
        "leave": AccessNote(conditions=("Ega yoki ko'ruvchi o'z huquqidan voz kechadi.",)),
        "owner_requests": AccessNote(conditions=(OWNER_ONLY,)),
        "owner_request_approve": AccessNote(
            conditions=(OWNER_ONLY, "Faqat so'rov ochilganda ACCEPTED bo'lgan va hozir ham ega bo'lganlar.")
        ),
        "owner_request_reject": AccessNote(
            conditions=(OWNER_ONLY, "Faqat so'rov ochilganda ACCEPTED bo'lgan va hozir ham ega bo'lganlar.")
        ),
    }

    OWNER_ACTIONS = frozenset(
        {
            "members",
            "invitations",
            "invitation_revoke",
            "invitation_resend",
            "viewer_revoke",
            "owner_requests",
            "owner_request_approve",
            "owner_request_reject",
        }
    )

    def get_permissions(self):
        if self.action in self.OWNER_ACTIONS:
            return [IsCeremonyOwner()]
        if self.action == "leave":
            return [IsCeremonyMember()]
        return super().get_permissions()

    def get_throttles(self):
        if self.request.method == "POST" and self.action in ("invitations", "invitation_resend"):
            self.throttle_scope = "ceremony_invite"
            return [*super().get_throttles(), ScopedRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ceremony.objects.none()
        qs = with_owners(ownership.accessible_ceremonies(self.request.user)).order_by("-event_date")
        return folders.with_folders(qs, self.request.user)

    # ----------------------------------------------------------- folder
    @extend_schema(
        summary="Papka nomini o'zgartirish (faqat o'zim uchun)",
        tags=["me"],
        request=FolderRenameSerializer,
        responses=FolderResultSerializer,
    )
    @action(detail=True, methods=["patch"])
    def folder(self, request, pk=None):
        ceremony = self.get_object()
        body = FolderRenameSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        name = folders.rename(request, request.user, ceremony, body.validated_data["name"])
        return Response({"folder_name": name or ceremony.title, "is_custom": bool(name)})

    def _row(self, qs, row_id):
        row = qs.filter(pk=row_id).first()
        if row is None:
            raise NotFound()
        return row

    # ---------------------------------------------------------- members
    @extend_schema(summary="Marosim egalari va ko'ruvchilari", tags=["me"], responses=MembersSerializer)
    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        ceremony = self.get_object()
        data = {
            "owners": ceremony.ownerships.filter(status=OwnershipStatus.ACCEPTED)
            .select_related("user")
            .order_by("accepted_at"),
            "viewers": ownership.live_viewers()
            .filter(ceremony=ceremony)
            .select_related("user", "granted_by", "ceremony__studio")
            .order_by("accepted_at"),
            "pending_owner_requests": ceremony.ownerships.filter(status=OwnershipStatus.PENDING).count(),
            "viewer_limit": viewer_limit(request.user),
        }
        return Response(MembersSerializer(data, context={"request": request}).data)

    # ------------------------------------------------------ invitations
    @extend_schema(
        methods=["GET"],
        summary="Marosim takliflari tarixi",
        tags=["me"],
        responses=OwnerInvitationSerializer(many=True),
    )
    @extend_schema(
        methods=["POST"],
        summary="VIEWER yoki OWNER taklifi yuborish (telefon / JSHSHIR)",
        description=(
            "Javob oluvchining akkaunti bor-yo'qligini bildirmaydi. VIEWER: oluvchi qabul qilgach galereyani ko'radi. "
            "OWNER: oluvchi qabul qilgach marosimning boshqa egalari tasdiqlaydi (sizning taklifingiz — "
            "sizning tasdig'ingiz)."
        ),
        tags=["me"],
        request=OwnerInvitationCreateSerializer,
        responses={201: OwnerInvitationSerializer},
    )
    @action(detail=True, methods=["get", "post"], pagination_class=None)
    def invitations(self, request, pk=None):
        ceremony = self.get_object()
        if request.method == "GET":
            rows = ceremony.invitations.select_related("ceremony__studio", "invited_by").order_by("-created_at")
            return Response(OwnerInvitationSerializer(rows, many=True, context={"request": request}).data)
        serializer = OwnerInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = invitations.create_invitation(
            request, ceremony, allowed_kinds=(InviterKind.OWNER,), **serializer.validated_data
        )
        data = OwnerInvitationSerializer(invitation, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)

    def _invitation(self, ceremony, invitation_id) -> CeremonyInvitation:
        return self._row(ceremony.invitations.select_related("ceremony__studio", "invited_by"), invitation_id)

    @extend_schema(summary="O'zi yuborgan taklifni bekor qilish", tags=["me"], request=None, responses={204: None})
    @action(
        detail=True,
        methods=["post"],
        url_path=rf"invitations/(?P<invitation_id>{UUID_RE})/revoke",
        url_name="invitation-revoke",
    )
    def invitation_revoke(self, request, pk=None, invitation_id=None):
        invitations.revoke_invitation(request, self._invitation(self.get_object(), invitation_id))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Taklifni qayta yuborish (muddat yangilanadi)",
        tags=["me"],
        request=None,
        responses=OwnerInvitationSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path=rf"invitations/(?P<invitation_id>{UUID_RE})/resend",
        url_name="invitation-resend",
    )
    def invitation_resend(self, request, pk=None, invitation_id=None):
        invitation = invitations.resend(request, self._invitation(self.get_object(), invitation_id))
        return Response(OwnerInvitationSerializer(invitation, context={"request": request}).data)

    @extend_schema(
        summary="O'zi bergan ko'rish huquqini bekor qilish", tags=["me"], request=None, responses={204: None}
    )
    @action(
        detail=True,
        methods=["post"],
        url_path=rf"viewers/(?P<access_id>{UUID_RE})/revoke",
        url_name="viewer-revoke",
    )
    def viewer_revoke(self, request, pk=None, access_id=None):
        ceremony = self.get_object()
        access = self._row(CeremonyViewerAccess.objects.filter(ceremony=ceremony).select_related("ceremony"), access_id)
        invitations.revoke_viewer(request, access)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="Marosimdan chiqish (egalik / ko'rish huquqidan voz kechish)", tags=["me"], request=None)
    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        invitations.leave(request, self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --------------------------------------------------- owner requests
    def _pending_requests(self, ceremony):
        return ceremony.ownerships.filter(status=OwnershipStatus.PENDING).select_related(
            "user", "invitation__ceremony__studio", "invitation__invited_by", "ceremony__studio"
        )

    @extend_schema(
        summary="Tasdiq kutayotgan yangi egalar",
        tags=["me"],
        responses=OwnerRequestSerializer(many=True),
    )
    @action(detail=True, methods=["get"], url_path="owner-requests", url_name="owner-requests")
    def owner_requests(self, request, pk=None):
        rows = self._pending_requests(self.get_object()).order_by("created_at")
        return Response(OwnerRequestSerializer(rows, many=True, context={"request": request}).data)

    def _decide(self, request, request_id, approve: bool):
        ceremony = self.get_object()
        row = self._row(self._pending_requests(ceremony), request_id)
        invitations.decide_owner_request(request, row, approve=approve)
        return Response(OwnerRequestSerializer(row, context={"request": request}).data)

    @extend_schema(summary="Yangi egani tasdiqlash", tags=["me"], request=None, responses=OwnerRequestSerializer)
    @action(
        detail=True,
        methods=["post"],
        url_path=rf"owner-requests/(?P<request_id>{UUID_RE})/approve",
        url_name="owner-request-approve",
    )
    def owner_request_approve(self, request, pk=None, request_id=None):
        return self._decide(request, request_id, approve=True)

    @extend_schema(summary="Yangi egani rad etish", tags=["me"], request=None, responses=OwnerRequestSerializer)
    @action(
        detail=True,
        methods=["post"],
        url_path=rf"owner-requests/(?P<request_id>{UUID_RE})/reject",
        url_name="owner-request-reject",
    )
    def owner_request_reject(self, request, pk=None, request_id=None):
        return self._decide(request, request_id, approve=False)


# ---------------------------------------------------------- invitations
@extend_schema_view(
    list=extend_schema(summary="Menga kelgan takliflar", tags=["me"]),
    retrieve=extend_schema(summary="Taklif tafsilotlari", tags=["me"]),
)
class InvitationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = InvitationSerializer
    queryset = CeremonyInvitation.objects.none()
    lookup_value_regex = UUID_RE
    permission_classes = [IsClientUser]
    filter_backends = []
    pagination_class = None
    access_notes = {
        "*": AccessNote(
            ownership="Faqat so'rovchining telefoni yoki JSHSHIRiga (hash bo'yicha aniq moslik) yuborilgan, "
            "javob kutilayotgan va muddati o'tmagan takliflar; boshqasi 404."
        ),
        "accept": AccessNote(
            conditions=(
                PHONE_VERIFIED_OWNER,
                "Taklif qabul qilinmaguncha hech qanday kirish huquqi berilmaydi.",
                "Muddati o'tgan — 410.",
            )
        ),
    }

    def get_throttles(self):
        if self.action in ("accept", "decline"):
            self.throttle_scope = "invitation_respond"
            return [*super().get_throttles(), ScopedRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CeremonyInvitation.objects.none()
        return ownership.invitations_for(self.request.user).select_related("invited_by")

    def get_object(self):
        """Accept/decline also find invitations that just expired, so the caller gets 410, not 404."""
        if self.action in ("accept", "decline"):
            user = self.request.user
            row = (
                CeremonyInvitation.objects.filter(pk=self.kwargs["pk"], status=InvitationStatus.PENDING)
                .select_related("ceremony__studio")
                .first()
            )
            if row is None or not ownership.is_recipient(user, row) or not ownership.is_client(user):
                raise NotFound()
            return row
        return super().get_object()

    @extend_schema(summary="Taklifni qabul qilish", tags=["me"], request=None, responses=AcceptResultSerializer)
    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        invitation = self.get_object()
        result = invitations.accept(request, invitation)
        granted = result["access_role"] == AccessRole.VIEWER or result["status"] == "ACCEPTED"
        ceremony = (
            with_owners(ownership.accessible_ceremonies(request.user)).filter(pk=invitation.ceremony_id).first()
            if granted
            else None
        )
        data = {"status": result["status"], "access_role": result["access_role"], "ceremony": ceremony}
        return Response(AcceptResultSerializer(data, context={"request": request}).data)

    @extend_schema(summary="Taklifni rad etish", tags=["me"], request=None, responses={204: None})
    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        invitations.decline(request, self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)
