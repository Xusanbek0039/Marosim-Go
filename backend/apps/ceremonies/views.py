"""Studio, Super Admin and couple endpoints for ceremonies.

Row-level scope (who sees which ceremony) lives in ``services`` and is applied in every
``get_queryset``: a ceremony outside your scope is a 404, never a 403, so its existence is not
confirmed. Write actions additionally require an OWNER/MANAGER membership (or SUPER_ADMIN).
"""

from django.db import transaction
from django.db.models import Count, Prefetch
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.access import AccessNote
from apps.audit.services import AuditAction, diff, record, snapshot
from apps.studios.models import StudioMembership
from apps.studios.services import active_memberships

from . import services
from .models import AccessStatus, Ceremony, CeremonyParticipant, CeremonyStatus
from .permissions import IsClientUser, IsStudioMember, IsStudioMemberOrSuperAdmin
from .serializers import (
    CeremonySerializer,
    InvitationSerializer,
    MyCeremonySerializer,
    ParticipantSerializer,
    StudioMembershipMeSerializer,
)

AUDITED_FIELDS = ["title", "event_type", "event_date", "description", "status"]
STUDIO_SCOPE = "STUDIO: faqat faol a'zolik bo'lgan studiyalarning marosimlari; SUPER_ADMIN: barchasi."
MANAGE_CONDITION = "STUDIO a'zoligi OWNER yoki MANAGER bo'lishi shart (UPLOADER — faqat ko'rish)."
STATUS_FILTER = OpenApiParameter("status", str, enum=[s.value for s in CeremonyStatus], required=False)


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
    lookup_value_regex = "[0-9a-fA-F-]{36}"
    permission_classes = [IsStudioMemberOrSuperAdmin]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    search_fields = ["title", "description", "studio__name"]
    ordering_fields = ["event_date", "created_at", "title", "status"]
    ordering = ["-event_date"]
    access_notes = {
        "*": AccessNote(ownership=STUDIO_SCOPE),
        "create": AccessNote(conditions=(MANAGE_CONDITION, "SUPER_ADMIN studio_id ni ko'rsatishi shart.")),
        "partial_update": AccessNote(conditions=(MANAGE_CONDITION, "Holat o'tishlari cheklangan.")),
        "participants": AccessNote(conditions=("POST: " + MANAGE_CONDITION,)),
        "remove_participant": AccessNote(conditions=(MANAGE_CONDITION,)),
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ceremony.objects.none()
        qs = services.ceremonies_for(self.request.user)
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs

    def get_throttles(self):
        if self.action == "participants" and self.request.method == "POST":
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

    @extend_schema(
        methods=["GET"],
        summary="Marosim ishtirokchilari",
        tags=["ceremonies"],
        responses=ParticipantSerializer(many=True),
    )
    @extend_schema(
        methods=["POST"],
        summary="Ishtirokchini telefon orqali taklif qilish",
        description=(
            "Javob raqam ro'yxatdan o'tganmi-yo'qmi bildirmaydi. Ism faqat taklif qabul qilingandan keyin ko'rinadi."
        ),
        tags=["ceremonies"],
        request=ParticipantSerializer,
        responses={201: ParticipantSerializer},
    )
    @action(detail=True, methods=["get", "post"], pagination_class=None, filter_backends=[])
    def participants(self, request, pk=None):
        ceremony = self.get_object()
        if request.method == "GET":
            rows = ceremony.participants.exclude(access_status=AccessStatus.REVOKED).select_related("user")
            return Response(ParticipantSerializer(rows, many=True).data)
        serializer = ParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        participant = services.invite(
            request, ceremony, serializer.validated_data["phone_number"], serializer.validated_data["participant_type"]
        )
        return Response(ParticipantSerializer(participant).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Ishtirokchini olib tashlash (kirish bekor qilinadi)", tags=["ceremonies"], responses={204: None}
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"participants/(?P<participant_id>[0-9a-fA-F-]{36})",
        url_name="remove-participant",
    )
    def remove_participant(self, request, pk=None, participant_id=None):
        ceremony = self.get_object()
        participant = ceremony.participants.filter(pk=participant_id).first()
        if participant is None:
            from rest_framework.exceptions import NotFound

            raise NotFound()
        services.revoke(request, participant)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ couple
def _with_participants(qs):
    return qs.prefetch_related(
        Prefetch("participants", queryset=CeremonyParticipant.objects.select_related("user").order_by("created_at"))
    )


@extend_schema_view(
    list=extend_schema(summary="Menga biriktirilgan marosimlar", tags=["me"]),
    retrieve=extend_schema(summary="Menga biriktirilgan marosim", tags=["me"]),
)
class MyCeremonyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MyCeremonySerializer
    queryset = Ceremony.objects.none()
    lookup_value_regex = "[0-9a-fA-F-]{36}"
    permission_classes = [IsClientUser]
    filter_backends = []
    access_notes = {
        "*": AccessNote(
            ownership="Faqat so'rovchi ACTIVE ishtirokchi bo'lgan, DRAFT bo'lmagan marosimlar.",
        )
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Ceremony.objects.none()
        ids = services.participations_for(self.request.user).values_list("ceremony_id", flat=True)
        return _with_participants(Ceremony.objects.filter(pk__in=ids).select_related("studio"))


@extend_schema_view(list=extend_schema(summary="Menga kelgan takliflar", tags=["me"]))
class InvitationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = InvitationSerializer
    queryset = CeremonyParticipant.objects.none()
    lookup_value_regex = "[0-9a-fA-F-]{36}"
    permission_classes = [IsClientUser]
    filter_backends = []
    pagination_class = None
    access_notes = {"*": AccessNote(ownership="Faqat so'rovchining telefon raqamiga yuborilgan takliflar.")}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CeremonyParticipant.objects.none()
        return services.invitations_for(self.request.user)

    @extend_schema(summary="Taklifni qabul qilish", tags=["me"], request=None, responses=MyCeremonySerializer)
    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        participant = self.get_object()
        services.accept(request, participant)
        ceremony = _with_participants(
            Ceremony.objects.filter(pk=participant.ceremony_id).select_related("studio")
        ).get()
        return Response(MyCeremonySerializer(ceremony, context={"request": request}).data)

    @extend_schema(summary="Taklifni rad etish", tags=["me"], request=None, responses={204: None})
    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        services.decline(request, self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)
