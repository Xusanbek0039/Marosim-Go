"""Subscription endpoints.

* ``/subscriptions/plans/`` — public price list.
* ``/me/subscriptions/`` — the couple's own requests (USER only; others' rows are 404).
* ``/admin/subscriptions/``, ``/admin/subscription-plans/``, ``/admin/subscription-settings/`` —
  Super Admin always, ADMIN only with the ``subscriptions.*`` codes the Super Admin granted.
"""

import django_filters
from django.db.models import Q, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.access import AccessNote
from apps.accounts.permissions import HasAdminPermission
from apps.audit.services import AuditAction, diff, record, snapshot
from apps.ceremonies.permissions import IsClientUser

from . import services
from .models import Subscription, SubscriptionPlan, SubscriptionSettings, SubscriptionStatus
from .serializers import (
    AdminNoteSerializer,
    AdminSubscriptionSerializer,
    GrantSerializer,
    MySubscriptionSerializer,
    MySubscriptionStatusSerializer,
    PaymentSerializer,
    PlanCreateSerializer,
    PlanSerializer,
    SettingsSerializer,
    SubscriptionRequestSerializer,
    SummarySerializer,
)

UUID_RE = "[0-9a-fA-F-]{36}"
PLAN_FIELDS = ["code", "name", "duration_months", "price", "max_viewers", "is_active", "position"]


# ---------------------------------------------------------------- public
@extend_schema_view(list=extend_schema(summary="Obuna tariflari", tags=["subscriptions"]))
class PlanListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = []
    queryset = SubscriptionPlan.objects.filter(is_active=True)


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
    permission_classes = [IsClientUser]
    pagination_class = None
    filter_backends = []
    queryset = Subscription.objects.none()
    lookup_value_regex = UUID_RE
    access_notes = {
        "*": AccessNote(ownership="Faqat so'rovchining o'z obunalari; boshqasiniki 404."),
        "create": AccessNote(ownership="", conditions=("Bir vaqtda bitta kutilayotgan so'rov.",)),
        "status": AccessNote(ownership=""),
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Subscription.objects.none()
        return Subscription.objects.filter(user=self.request.user).select_related("plan")

    def create(self, request, *args, **kwargs):
        body = SubscriptionRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        sub = services.request_subscription(
            request, request.user, body.validated_data["plan"], body.validated_data.get("user_note", "").strip()
        )
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
    )
    @action(detail=False, methods=["get"])
    def status(self, request):
        user = request.user
        data = {
            "active": services.active_subscription(user),
            "pending": Subscription.objects.filter(user=user, status=SubscriptionStatus.PENDING)
            .select_related("plan")
            .first(),
            "paid_until": services.paid_until(user),
            "clean_access": services.has_clean_access(user),
            "viewer_limit": services.viewer_limit(user),
            "payment_instructions": SubscriptionSettings.load().payment_instructions,
            "plans": SubscriptionPlan.objects.filter(is_active=True),
        }
        return Response(MySubscriptionStatusSerializer(data).data)


# ----------------------------------------------------------------- admin
class SubscriptionFilter(django_filters.FilterSet):
    state = django_filters.ChoiceFilter(
        choices=[(s, s) for s in ("PENDING", "ACTIVE", "EXPIRED", "SCHEDULED", "REJECTED", "CANCELLED")],
        method="filter_state",
    )
    user = django_filters.UUIDFilter(field_name="user_id")

    class Meta:
        model = Subscription
        fields = ["state", "user", "plan"]

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
    search_fields = ["user__first_name", "user__last_name", "user__phone_number", "payment_reference"]
    ordering_fields = ["created_at", "ends_at", "price"]
    ordering = ["-created_at"]
    access_notes = {"*": AccessNote(ownership=ALL)}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Subscription.objects.none()
        return Subscription.objects.select_related("plan", "user", "decided_by")

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
