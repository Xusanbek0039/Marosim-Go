"""Partner applications from the marosimgo.uz landing page.

* ``GET /public/partner-applications/challenge/`` then ``POST /public/partner-applications/`` — anyone
  (no account): a studio or venue asks to join. Layers against bots: IP throttle (``partner_apply``),
  signed one-time proof-of-work challenge with a minimum fill time (``challenge``), a hidden
  ``website`` honeypot (answered 201 like a real request, nothing is stored), at most
  ``PHONE_LIMIT`` applications per phone a day, and the pluggable ``bot_protection`` guard.
* ``/admin/support/applications/`` — staff with ``support.view`` (and the SUPER_ADMIN) review them on
  the "Yordam" page: list, filter, change status, keep a note.
"""

import django_filters
from django.core.exceptions import ValidationError as DjangoValidationError
from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts import bot_protection
from apps.accounts import phone as phone_utils
from apps.accounts.access import AccessNote
from apps.accounts.permissions import HasAdminPermission
from apps.venues.models import Region

from . import challenge
from .models import ApplicationKind, ApplicationStatus, PartnerApplication

UUID_RE = "[0-9a-fA-F-]{36}"
PHONE_LIMIT = 3  # applications per phone number in 24 hours


# ================================================================ serializers
class ApplicationCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=ApplicationKind.choices)
    full_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=30, help_text="O'zbekiston raqami, masalan +998901234567.")
    business_name = serializers.CharField(max_length=200, help_text="Studiya yoki to'yxona nomi.")
    region = serializers.ChoiceField(choices=Region.choices, required=False, allow_blank=True, default="")
    message = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    #: Honeypot: hidden on the page, real people leave it empty.
    website = serializers.CharField(required=False, allow_blank=True, default="", write_only=True)
    challenge = serializers.CharField(max_length=500, help_text="`challenge/` dan olingan token.")
    proof = serializers.CharField(max_length=64, help_text="sha256(`token:proof`) `difficulty` ta nol bit bilan boshlanadi.")

    def validate_phone_number(self, value: str) -> str:
        try:
            return phone_utils.normalize(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from None


class ApplicationSerializer(serializers.ModelSerializer):
    handled_by_name = serializers.SerializerMethodField()
    region_label = serializers.SerializerMethodField()

    class Meta:
        model = PartnerApplication
        fields = [
            "id",
            "kind",
            "status",
            "full_name",
            "phone_number",
            "business_name",
            "region",
            "region_label",
            "message",
            "staff_note",
            "handled_by_name",
            "handled_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_handled_by_name(self, obj) -> str | None:
        return (obj.handled_by.full_name or "—") if obj.handled_by else None

    def get_region_label(self, obj) -> str:
        return Region(obj.region).label if obj.region in Region.values else ""


class ApplicationUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ApplicationStatus.choices, required=False)
    staff_note = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class ApplicationReceivedSerializer(serializers.Serializer):
    received = serializers.BooleanField(help_text="Doim true: ariza qabul qilindi (shaxsiy ma'lumot qaytarilmaydi).")


class ChallengeSerializer(serializers.Serializer):
    token = serializers.CharField()
    difficulty = serializers.IntegerField(help_text="sha256 natijasi shuncha nol bit bilan boshlanishi kerak.")
    min_seconds = serializers.IntegerField(help_text="Forma kamida shuncha soniya ochiq turishi kerak.")


class ApplicationSummarySerializer(serializers.Serializer):
    new = serializers.IntegerField()
    in_review = serializers.IntegerField()


# ================================================================ public
@extend_schema_view(
    create=extend_schema(
        summary="Hamkorlik arizasi (studiya / to'yxona) — landing sahifadan",
        tags=["public"],
        request=ApplicationCreateSerializer,
        responses={201: ApplicationReceivedSerializer},
    )
)
class PublicApplicationViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "partner_apply"
    serializer_class = ApplicationCreateSerializer
    access_notes = {
        "create": AccessNote(
            conditions=(
                "IP bo'yicha cheklangan (partner_apply); bir martalik proof-of-work topshiriq, kamida 3 s; "
                "bitta raqamdan kuniga 3 ta; javobda shaxsiy ma'lumot yo'q.",
            )
        ),
        "challenge": AccessNote(conditions=("IP bo'yicha cheklangan (partner_challenge).",)),
    }

    def get_throttles(self):
        self.throttle_scope = "partner_challenge" if self.action == "challenge" else "partner_apply"
        return super().get_throttles()

    @extend_schema(
        summary="Bot tekshiruvi uchun bir martalik topshiriq (proof-of-work)",
        tags=["public"],
        responses=ChallengeSerializer,
    )
    @action(detail=False, methods=["get"])
    def challenge(self, request):
        response = Response(challenge.issue())
        response["Cache-Control"] = "no-store"
        return response

    def create(self, request):
        bot_protection.verify(request)
        body = ApplicationCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = dict(body.validated_data)
        challenge.verify(data.pop("challenge"), data.pop("proof"))
        if data.pop("website", ""):
            return Response({"received": True}, status=status.HTTP_201_CREATED)  # honeypot: silently dropped
        since = timezone.now() - timedelta(hours=24)
        if PartnerApplication.objects.filter(phone_number=data["phone_number"], created_at__gte=since).count() >= PHONE_LIMIT:
            raise serializers.ValidationError(
                {"phone_number": ["Bu raqamdan bugun ariza yuborilgan. Tez orada siz bilan bog'lanamiz."]}
            )
        PartnerApplication.objects.create(**{k: v.strip() if isinstance(v, str) else v for k, v in data.items()})
        return Response({"received": True}, status=status.HTTP_201_CREATED)


# ================================================================ staff
class ApplicationFilter(django_filters.FilterSet):
    kind = django_filters.ChoiceFilter(choices=ApplicationKind.choices)
    status = django_filters.ChoiceFilter(choices=ApplicationStatus.choices)
    region = django_filters.ChoiceFilter(choices=Region.choices)

    class Meta:
        model = PartnerApplication
        fields = ["kind", "status", "region"]


@extend_schema_view(
    list=extend_schema(summary="Hamkorlik arizalari (studiya / to'yxona)", tags=["admin-support"]),
    retrieve=extend_schema(summary="Ariza tafsiloti", tags=["admin-support"]),
    partial_update=extend_schema(
        summary="Ariza holati va izohi",
        tags=["admin-support"],
        request=ApplicationUpdateSerializer,
        responses=ApplicationSerializer,
    ),
)
class StaffApplicationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = ApplicationSerializer
    permission_classes = [HasAdminPermission]
    permission_module = "support"
    action_permissions = {"partial_update": "support.view", "summary": "support.view"}
    http_method_names = ["get", "patch", "head", "options"]
    queryset = PartnerApplication.objects.none()
    lookup_value_regex = UUID_RE
    filterset_class = ApplicationFilter
    search_fields = ["full_name", "phone_number", "business_name", "message"]
    ordering_fields = ["created_at", "handled_at"]
    ordering = ["-created_at"]
    access_notes = {"*": AccessNote(ownership="Barcha arizalar (support.view ruxsati bor adminlar va SUPER_ADMIN).")}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PartnerApplication.objects.none()
        return PartnerApplication.objects.select_related("handled_by")

    def partial_update(self, request, *args, **kwargs):
        row = self.get_object()
        body = ApplicationUpdateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        for field, value in body.validated_data.items():
            setattr(row, field, value.strip() if isinstance(value, str) else value)
        row.handled_by, row.handled_at = request.user, timezone.now()
        row.save()
        return Response(ApplicationSerializer(row).data)

    @extend_schema(summary="Yangi arizalar soni", tags=["admin-support"], responses=ApplicationSummarySerializer)
    @action(detail=False, methods=["get"], pagination_class=None, filter_backends=[])
    def summary(self, request):
        qs = PartnerApplication.objects.all()
        return Response(
            {
                "new": qs.filter(status=ApplicationStatus.NEW).count(),
                "in_review": qs.filter(status=ApplicationStatus.IN_REVIEW).count(),
            }
        )
