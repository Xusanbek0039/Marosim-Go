"""Subscription endpoints.

* ``/subscriptions/plans/`` — public price list.
* ``/me/subscriptions/`` — own USER subscriptions and business-owner badge purchases.
* ``/admin/subscriptions/``, ``/admin/subscription-plans/``, ``/admin/subscription-settings/`` —
  Super Admin always, ADMIN only with the ``subscriptions.*`` codes the Super Admin granted.
"""

import django_filters
from django.db.models import Q, Sum
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.access import AccessNote
from apps.accounts.models import PlatformPolicy, Role
from apps.accounts.permissions import HasAdminPermission
from apps.audit.services import AuditAction, diff, record, snapshot

from . import services
from .models import PlanAudience, Subscription, SubscriptionPlan, SubscriptionSettings, SubscriptionStatus
from .permissions import IsSubscriberAccount
from .serializers import (
    AdminNoteSerializer,
    AdminSubscriptionSerializer,
    BusinessTargetSerializer,
    GrantSerializer,
    MySubscriptionSerializer,
    MySubscriptionStatusSerializer,
    PaymentSerializer,
    PlanCreateSerializer,
    PlanSerializer,
    SettingsSerializer,
    SubscriptionRequestSerializer,
    SubscriptionTargetSerializer,
    SummarySerializer,
)

UUID_RE = "[0-9a-fA-F-]{36}"
PLAN_FIELDS = ["code", "name", "audience", "duration_months", "price", "max_viewers", "is_active", "position"]


# ---------------------------------------------------------------- public
@extend_schema_view(
    list=extend_schema(
        summary="Obuna tariflari",
        tags=["subscriptions"],
        parameters=[OpenApiParameter("audience", str, enum=PlanAudience.values)],
    )
)
class PlanListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = []
    queryset = SubscriptionPlan.objects.filter(is_active=True)

    def get_queryset(self):
        audience = self.request.query_params.get("audience", PlanAudience.USER)
        if audience not in PlanAudience.values:
            raise ValidationError({"audience": ["Noto'g'ri tarif turi."]})
        return super().get_queryset().filter(audience=audience)


# -------------------------------------------------------------------- me
@extend_schema_view(
    list=extend_schema(summary="Mening obuna so'rovlarim va obunalarim", tags=["me"]),
    create=extend_schema(
        summary="Obuna so'rovi yuborish (to'lov admin tomonidan tasdiqlanadi)",
        tags=["me"],
        request=SubscriptionRequestSerializer,
        responses={201: MySubscriptionSerializer},
    ),
)
class MySubscriptionViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = MySubscriptionSerializer
    permission_classes = [IsSubscriberAccount]
    pagination_class = None
    filter_backends = []
    queryset = Subscription.objects.none()
    lookup_value_regex = UUID_RE
    access_notes = {
        "*": AccessNote(ownership="Faqat so'rovchining o'z obunalari; boshqasiniki 404."),
        "create": AccessNote(
            ownership="", conditions=("Bir hisob yoki biznes uchun bir vaqtda bitta kutilayotgan so'rov.",)
        ),
        "status": AccessNote(ownership=""),
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Subscription.objects.none()
        return Subscription.objects.filter(user=self.request.user).select_related("plan", "studio", "venue")

    @extend_schema(
        summary="Galichka sotib olish mumkin bo'lgan o'z bizneslarim",
        tags=["me"],
        responses=SubscriptionTargetSerializer(many=True),
    )
    @action(detail=False, methods=["get"])
    def targets(self, request):
        from apps.studios.models import Studio
        from apps.venues.models import Venue

        user = request.user
        rows = []
        if user.role == Role.STUDIO:
            rows = [
                {"id": s.pk, "name": s.name, "kind": "studio"}
                for s in Studio.objects.filter(responsible_user=user, is_active=True, deleted_at__isnull=True)
            ]
        elif user.role == Role.VENUE_OWNER:
            rows = [
                {"id": v.pk, "name": v.name, "kind": "venue"}
                for v in Venue.objects.filter(
                    memberships__user=user,
                    memberships__role="OWNER",
                    memberships__is_active=True,
                    is_active=True,
                    deleted_at__isnull=True,
                )
            ]
        return Response(SubscriptionTargetSerializer(rows, many=True).data)

    def create(self, request, *args, **kwargs):
        body = SubscriptionRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        sub = services.request_subscription(request, request.user, **body.validated_data)
        return Response(MySubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Kutilayotgan so'rovni bekor qilish", tags=["me"], request=None, responses=MySubscriptionSerializer
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        sub = services.cancel(request, self.get_object(), by_user=True)
        return Response(MySubscriptionSerializer(sub).data)

    @extend_schema(
        summary="Obuna holati, limitlar, tariflar va to'lov ma'lumotlari",
        tags=["me"],
        responses=MySubscriptionStatusSerializer,
        parameters=[
            OpenApiParameter("studio", str, description="STUDIO: o'z studiyangiz UUID si"),
            OpenApiParameter("venue", str, description="VENUE_OWNER: o'z to'yxonangiz UUID si"),
        ],
    )
    @action(detail=False, methods=["get"])
    def status(self, request):
        user = request.user
        audience = {
            Role.USER: PlanAudience.USER,
            Role.STUDIO: PlanAudience.STUDIO,
            Role.VENUE_OWNER: PlanAudience.VENUE,
        }[user.role]
        studio = venue = None
        if audience != PlanAudience.USER:
            # Validate both UUID syntax and ownership before looking up any subscription.
            target = BusinessTargetSerializer(
                data={
                    **{key: request.query_params[key] for key in ("studio", "venue") if key in request.query_params},
                }
            )
            target.is_valid(raise_exception=True)
            studio, venue = target.validated_data.get("studio"), target.validated_data.get("venue")
            from types import SimpleNamespace

            services.ensure_target(user, SimpleNamespace(audience=audience), studio, venue)
        scope = services.target_filter(user, studio, venue)
        now = timezone.now()
        active = (
            Subscription.objects.filter(**scope, status=SubscriptionStatus.ACTIVE, starts_at__lte=now, ends_at__gt=now)
            .select_related("plan")
            .first()
        )
        data = {
            "active": active,
            "pending": Subscription.objects.filter(**scope, status=SubscriptionStatus.PENDING)
            .select_related("plan")
            .first(),
            "paid_until": services.paid_until(user, studio, venue),
            "clean_access": audience == PlanAudience.USER and active is not None,
            "is_verified": active is not None,
            "purchase_enabled": f"{user.role}.subscriptions" not in PlatformPolicy.load().disabled_features,
            "viewer_limit": services.viewer_limit(user),
            "payment_instructions": SubscriptionSettings.load().payment_instructions,
            "plans": SubscriptionPlan.objects.filter(is_active=True, audience=audience),
        }
        return Response(MySubscriptionStatusSerializer(data).data)


# ----------------------------------------------------------------- admin
class SubscriptionFilter(django_filters.FilterSet):
    audience = django_filters.ChoiceFilter(field_name="plan__audience", choices=PlanAudience.choices)
    state = django_filters.ChoiceFilter(
        choices=[(s, s) for s in ("PENDING", "ACTIVE", "EXPIRED", "SCHEDULED", "REJECTED", "CANCELLED")],
        method="filter_state",
    )
    user = django_filters.UUIDFilter(field_name="user_id")

    class Meta:
        model = Subscription
        fields = ["state", "user", "plan", "audience"]

    def filter_state(self, qs, name, value):
        now = timezone.now()
        if value == "ACTIVE":
            return qs.filter(status=SubscriptionStatus.ACTIVE, starts_at__lte=now, ends_at__gt=now)
        if value == "SCHEDULED":
            return qs.filter(status=SubscriptionStatus.ACTIVE, starts_at__gt=now)
        if value == "EXPIRED":
            return qs.filter(status=SubscriptionStatus.ACTIVE, ends_at__lte=now)
        return qs.filter(status=value)


ALL = "Barcha foydalanuvchilarning obunalari (faqat ruxsati borlar)."


@extend_schema_view(
    list=extend_schema(summary="Obunalar va to'lovlar", tags=["admin-subscriptions"]),
    retrieve=extend_schema(summary="Obuna tafsiloti", tags=["admin-subscriptions"]),
    create=extend_schema(
        summary="Foydalanuvchiga obuna berish (to'lov qayd etiladi)",
        tags=["admin-subscriptions"],
        request=GrantSerializer,
        responses={201: AdminSubscriptionSerializer},
    ),
)
class AdminSubscriptionViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    serializer_class = AdminSubscriptionSerializer
    permission_classes = [HasAdminPermission]
    permission_module = "subscriptions"
    action_permissions = {
        "approve": "subscriptions.update",
        "reject": "subscriptions.update",
        "cancel": "subscriptions.update",
        "summary": "subscriptions.view",
    }
    queryset = Subscription.objects.none()
    lookup_value_regex = UUID_RE
    filterset_class = SubscriptionFilter
    search_fields = [
        "user__first_name",
        "user__last_name",
        "user__phone_number",
        "payment_reference",
        "studio__name",
        "venue__name",
    ]
    ordering_fields = ["created_at", "ends_at", "price"]
    ordering = ["-created_at"]
    access_notes = {"*": AccessNote(ownership=ALL)}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Subscription.objects.none()
        return Subscription.objects.select_related("plan", "user", "decided_by", "studio", "venue")

    def create(self, request, *args, **kwargs):
        body = GrantSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = dict(body.validated_data)
        sub = services.grant(request, data.pop("user"), data.pop("plan"), **data)
        return Response(AdminSubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)

    def _respond(self, sub):
        return Response(AdminSubscriptionSerializer(self.get_queryset().get(pk=sub.pk)).data)

    @extend_schema(
        summary="To'lovni qayd etib tasdiqlash",
        tags=["admin-subscriptions"],
        request=PaymentSerializer,
        responses=AdminSubscriptionSerializer,
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        body = PaymentSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return self._respond(services.approve(request, self.get_object(), **body.validated_data))

    @extend_schema(
        summary="So'rovni rad etish",
        tags=["admin-subscriptions"],
        request=AdminNoteSerializer,
        responses=AdminSubscriptionSerializer,
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        body = AdminNoteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return self._respond(services.reject(request, self.get_object(), body.validated_data.get("admin_note", "")))

    @extend_schema(
        summary="Obunani bekor qilish",
        tags=["admin-subscriptions"],
        request=AdminNoteSerializer,
        responses=AdminSubscriptionSerializer,
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        body = AdminNoteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        sub = services.cancel(
            request, self.get_object(), by_user=False, admin_note=body.validated_data.get("admin_note", "")
        )
        return self._respond(sub)

    @extend_schema(
        summary="Obunalar statistikasi (so'rovlar, faollar, tushum)",
        tags=["admin-subscriptions"],
        responses=SummarySerializer,
    )
    @action(detail=False, methods=["get"], pagination_class=None, filter_backends=[])
    def summary(self, request):
        now = timezone.now()
        month_start = timezone.localtime(now).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        paid = Subscription.objects.filter(status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED]).filter(
            paid_amount__isnull=False
        )
        data = {
            "pending": Subscription.objects.filter(status=SubscriptionStatus.PENDING).count(),
            "active": Subscription.objects.filter(
                Q(status=SubscriptionStatus.ACTIVE, starts_at__lte=now, ends_at__gt=now)
            )
            .values("user")
            .distinct()
            .count(),
            "revenue_month": paid.filter(paid_at__gte=month_start).aggregate(s=Sum("paid_amount"))["s"] or 0,
            "revenue_total": paid.aggregate(s=Sum("paid_amount"))["s"] or 0,
        }
        return Response(SummarySerializer(data).data)


@extend_schema_view(
    list=extend_schema(summary="Tariflar (barchasi)", tags=["admin-subscriptions"]),
    create=extend_schema(summary="Tarif qo'shish", tags=["admin-subscriptions"], request=PlanCreateSerializer),
    partial_update=extend_schema(summary="Tarif narxi / muddati / limitini o'zgartirish", tags=["admin-subscriptions"]),
)
class AdminPlanViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = PlanSerializer
    permission_classes = [HasAdminPermission]
    permission_module = "subscriptions"
    action_permissions = {"create": "subscriptions.plans", "partial_update": "subscriptions.plans"}
    queryset = SubscriptionPlan.objects.all()
    lookup_value_regex = UUID_RE
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None
    filter_backends = []
    access_notes = {
        "*": AccessNote(ownership=""),
        "partial_update": AccessNote(conditions=("Yangi narx faqat keyingi so'rovlarga ta'sir qiladi.",)),
    }

    def get_serializer_class(self):
        return PlanCreateSerializer if self.action == "create" else PlanSerializer

    def perform_create(self, serializer):
        plan = serializer.save()
        record(self.request, AuditAction.CREATE, plan, changes=snapshot(plan, PLAN_FIELDS))

    def perform_update(self, serializer):
        before = snapshot(serializer.instance, PLAN_FIELDS)
        plan = serializer.save()
        changes = diff(before, snapshot(plan, PLAN_FIELDS))
        if changes:
            record(self.request, AuditAction.UPDATE, plan, changes=changes)


@extend_schema_view(
    retrieve=extend_schema(summary="To'lov ma'lumotlari (mijozga ko'rsatiladi)", tags=["admin-subscriptions"]),
    partial_update=extend_schema(summary="To'lov ma'lumotlarini o'zgartirish", tags=["admin-subscriptions"]),
)
class AdminSettingsViewSet(viewsets.GenericViewSet):
    serializer_class = SettingsSerializer
    permission_classes = [HasAdminPermission]
    permission_module = "subscriptions"
    action_permissions = {"partial_update": "subscriptions.plans"}
    queryset = SubscriptionSettings.objects.none()
    access_notes = {"*": AccessNote(ownership="")}

    def retrieve(self, request):
        return Response(SettingsSerializer(SubscriptionSettings.load()).data)

    def partial_update(self, request):
        obj = SubscriptionSettings.load()
        serializer = SettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record(
            request,
            AuditAction.UPDATE,
            obj,
            changes={"payment_instructions": True},
            target_label="Obuna to'lov ma'lumotlari",
        )
        return Response(serializer.data)
