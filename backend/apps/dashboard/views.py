from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import CLIENT_ROLES, Role, User
from apps.accounts.permissions import HasAdminPermission
from apps.accounts.serializers import UserSummarySerializer
from apps.studios.models import Studio

OverviewSerializer = inline_serializer(
    "DashboardOverview",
    fields={
        "totals": serializers.DictField(child=serializers.IntegerField()),
        "role_distribution": serializers.ListField(child=serializers.DictField()),
        "recent_profiles": UserSummarySerializer(many=True),
        "generated_at": serializers.DateTimeField(),
    },
)


class DashboardOverviewView(APIView):
    permission_classes = [HasAdminPermission]
    required_permission = "dashboard.view"

    @extend_schema(responses=OverviewSerializer)
    def get(self, request):
        alive = User.objects.alive()
        since = timezone.now() - timedelta(days=30)
        client_roles = [r.value for r in CLIENT_ROLES]

        users = alive.filter(role__in=client_roles).aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
            new_30d=Count("id", filter=Q(created_at__gte=since)),
        )
        studios = Studio.objects.filter(deleted_at__isnull=True).aggregate(
            total=Count("id"), active=Count("id", filter=Q(is_active=True))
        )
        by_role = dict(alive.values_list("role").annotate(n=Count("id")).values_list("role", "n"))

        visible_roles = list(client_roles)
        if request.user.role == Role.SUPER_ADMIN:
            visible_roles.append(Role.ADMIN.value)
        recent = alive.filter(role__in=visible_roles).order_by("-created_at")[:6]

        return Response(
            {
                "totals": {
                    "users": users["total"],
                    "active_users": users["active"],
                    "inactive_users": users["total"] - users["active"],
                    "new_users_30d": users["new_30d"],
                    "admins": by_role.get(Role.ADMIN, 0),
                    "studios": studios["total"],
                    "active_studios": studios["active"],
                },
                "role_distribution": [
                    {"role": role.value, "label": role.label, "count": by_role.get(role.value, 0)} for role in Role
                ],
                "recent_profiles": UserSummarySerializer(recent, many=True, context={"request": request}).data,
                "generated_at": timezone.now(),
            }
        )
