"""Help tickets.

* ``/support/tickets/`` — the author's own tickets (USER, STUDIO, VENUE_OWNER, ADMIN; others' are 404).
* ``/admin/support/tickets/`` — the staff queue: SUPER_ADMIN everything; ADMIN with ``support.view``
  the tickets of USER / STUDIO / VENUE_OWNER, plus with ``support.monitor`` also the admins' tickets
  to the Super Admin (read only).
"""

import django_filters
from django.db.models import Count, OuterRef, Subquery
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.access import AccessNote
from apps.accounts.models import Role
from apps.accounts.permissions import HasAdminPermission

from . import services
from .models import SupportMessage, SupportTicket, TicketAudience, TicketStatus
from .permissions import IsSupportAuthor
from .serializers import (
    MessageCreateSerializer,
    SupportSummarySerializer,
    TicketCreateSerializer,
    TicketDetailSerializer,
    TicketSerializer,
)

UUID_RE = "[0-9a-fA-F-]{36}"


def _annotated(qs):
    last = SupportMessage.objects.filter(ticket=OuterRef("pk")).order_by("-created_at").values("body")[:1]
    return (
        qs.select_related("author", "studio", "venue", "handled_by", "closed_by")
        .annotate(message_count=Count("messages"), last_body=Subquery(last))
        .order_by("-last_message_at", "-created_at")  # GROUP BY drops Meta.ordering
    )


def _summary(qs) -> dict:
    counts = dict(qs.values_list("status").annotate(n=Count("id")).order_by())
    return {
        "open": counts.get(TicketStatus.OPEN, 0),
        "answered": counts.get(TicketStatus.ANSWERED, 0),
        "closed": counts.get(TicketStatus.CLOSED, 0),
    }


class _TicketActions:
    """Shared detail response; subclasses set ``staff_view``."""

    staff_view = False

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "staff_view": self.staff_view}

    def get_serializer_class(self):
        return TicketSerializer if self.action == "list" else TicketDetailSerializer

    def _detail(self, ticket, code=status.HTTP_200_OK):
        row = self.get_queryset().get(pk=ticket.pk)
        return Response(TicketDetailSerializer(row, context=self.get_serializer_context()).data, status=code)


# ================================================================ author
@extend_schema_view(
    list=extend_schema(summary="Mening yordam xatlarim", tags=["support"]),
    retrieve=extend_schema(summary="Yordam xati (yozishmalar bilan)", tags=["support"]),
)
class MySupportTicketViewSet(_TicketActions, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSupportAuthor]
    queryset = SupportTicket.objects.none()
    lookup_value_regex = UUID_RE
    filter_backends = []
    access_notes = {
        "*": AccessNote(ownership="Faqat o'zi yozgan xatlar (boshqalarniki 404)."),
        "create": AccessNote(
            conditions=("ADMIN xati Super Admin'ga boradi; boshqalarniki — support.view ruxsati bor adminlarga.",)
        ),
    }

    def get_throttles(self):
        if self.action in ("create", "messages"):
            self.throttle_scope = "support_write"
            return [*super().get_throttles(), ScopedRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SupportTicket.objects.none()
        return _annotated(SupportTicket.objects.filter(author=self.request.user))

    @extend_schema(
        summary="Yordam xati yuborish",
        tags=["support"],
        request=TicketCreateSerializer,
        responses={201: TicketDetailSerializer},
    )
    def create(self, request):
        body = TicketCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        ticket = services.open_ticket(request, body.validated_data["subject"], body.validated_data["body"])
        return self._detail(ticket, status.HTTP_201_CREATED)

    @extend_schema(
        summary="Xatga qo'shimcha yozish (yopilgan xat qayta ochiladi)",
        tags=["support"],
        request=MessageCreateSerializer,
        responses={201: TicketDetailSerializer},
    )
    @action(detail=True, methods=["post"])
    def messages(self, request, pk=None):
        body = MessageCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        ticket = self.get_object()
        services.author_reply(request, ticket, body.validated_data["body"])
        return self._detail(ticket, status.HTTP_201_CREATED)

    @extend_schema(
        summary="Xatni yopish (muammo hal bo'ldi)", tags=["support"], request=None, responses=TicketDetailSerializer
    )
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self._detail(services.close(request, self.get_object()))

    @extend_schema(
        summary="Xatlarim soni (javob kelganlar — menyu belgisi uchun)",
        tags=["support"],
        responses=SupportSummarySerializer,
    )
    @action(detail=False, methods=["get"], pagination_class=None)
    def summary(self, request):
        return Response(_summary(SupportTicket.objects.filter(author=request.user)))


# ================================================================ staff
class StaffTicketFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=TicketStatus.choices)
    audience = django_filters.ChoiceFilter(choices=TicketAudience.choices)
    author_role = django_filters.ChoiceFilter(
        choices=[(r.value, r.label) for r in (Role.USER, Role.STUDIO, Role.VENUE_OWNER, Role.ADMIN)]
    )
    studio = django_filters.UUIDFilter(field_name="studio_id")
    venue = django_filters.UUIDFilter(field_name="venue_id")

    class Meta:
        model = SupportTicket
        fields = ["status", "audience", "author_role", "studio", "venue"]


@extend_schema_view(
    list=extend_schema(summary="Kelgan yordam xatlari", tags=["admin-support"]),
    retrieve=extend_schema(summary="Yordam xati (yozishmalar, kim javob bergani)", tags=["admin-support"]),
)
class StaffSupportTicketViewSet(
    _TicketActions, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    staff_view = True
    permission_classes = [HasAdminPermission]
    permission_module = "support"
    action_permissions = {"messages": "support.view", "close": "support.view", "summary": "support.view"}
    queryset = SupportTicket.objects.none()
    lookup_value_regex = UUID_RE
    filterset_class = StaffTicketFilter
    search_fields = [
        "subject",
        "author__first_name",
        "author__last_name",
        "author__phone_number",
        "studio__name",
        "venue__name",
    ]
    ordering_fields = ["last_message_at", "created_at"]
    ordering = ["-last_message_at"]
    access_notes = {
        "*": AccessNote(
            ownership=(
                "SUPER_ADMIN — barchasi; ADMIN (support.view) — foydalanuvchi / studiya / to'yxona xatlari; "
                "support.monitor bilan — adminlarning Super Admin'ga xatlari ham (faqat o'qish)."
            )
        ),
        "messages": AccessNote(
            conditions=("Adminlarning xatlariga faqat SUPER_ADMIN javob beradi; o'z xatiga javob berilmaydi.",)
        ),
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SupportTicket.objects.none()
        return _annotated(services.staff_tickets(self.request.user))

    @extend_schema(
        summary="Javob yozish",
        tags=["admin-support"],
        request=MessageCreateSerializer,
        responses={201: TicketDetailSerializer},
    )
    @action(detail=True, methods=["post"])
    def messages(self, request, pk=None):
        body = MessageCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        ticket = self.get_object()
        services.staff_reply(request, ticket, body.validated_data["body"])
        return self._detail(ticket, status.HTTP_201_CREATED)

    @extend_schema(summary="Xatni yopish", tags=["admin-support"], request=None, responses=TicketDetailSerializer)
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self._detail(services.close(request, self.get_object()))

    @extend_schema(
        summary="Javob kutayotgan xatlar soni (javob bera oladiganlari)",
        tags=["admin-support"],
        responses=SupportSummarySerializer,
    )
    @action(detail=False, methods=["get"], pagination_class=None, filter_backends=[])
    def summary(self, request):
        qs = SupportTicket.objects.all()
        if request.user.role != Role.SUPER_ADMIN:
            qs = qs.filter(audience=TicketAudience.STAFF)
        return Response(_summary(qs))
