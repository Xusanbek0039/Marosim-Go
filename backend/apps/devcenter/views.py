"""API Developer Center — SUPER_ADMIN only, read-only.

There is no endpoint here that sends requests on the caller's behalf (no SSRF surface).
"""

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.access import ROLE_ORDER
from apps.accounts.permissions import IsSuperAdmin
from apps.monitoring import catalog, contract

from . import services

TAG = ["devcenter"]

OverviewSerializer = inline_serializer(
    "DevcenterOverview",
    fields={
        "api_version": serializers.CharField(),
        "openapi_version": serializers.CharField(),
        "schema_url": serializers.CharField(),
        "docs_url": serializers.CharField(),
        "versions": serializers.ListField(child=serializers.CharField()),
        "totals": serializers.DictField(child=serializers.IntegerField()),
        "roles": serializers.ListField(child=serializers.DictField()),
        "methods": serializers.DictField(child=serializers.IntegerField()),
        "contract": serializers.DictField(child=serializers.IntegerField()),
        "health": serializers.DictField(child=serializers.IntegerField()),
        "tags": serializers.ListField(child=serializers.CharField()),
        "last_change": serializers.DictField(allow_null=True),
    },
)
EndpointsSerializer = inline_serializer(
    "DevcenterEndpoints",
    fields={
        "api_base_url": serializers.CharField(),
        "schema_url": serializers.CharField(),
        "docs_url": serializers.CharField(),
        "openapi_version": serializers.CharField(),
        "api_version": serializers.CharField(),
        "count": serializers.IntegerField(),
        "results": serializers.ListField(child=serializers.DictField()),
    },
)
MobileSerializer = inline_serializer(
    "DevcenterMobileGuide", fields={"apps": serializers.ListField(child=serializers.DictField())}
)
ChangelogSerializer = inline_serializer(
    "DevcenterChangelog",
    fields={"count": serializers.IntegerField(), "results": serializers.ListField(child=serializers.DictField())},
)


class DevcenterBase(APIView):
    permission_classes = [IsSuperAdmin]


class OverviewView(DevcenterBase):
    @extend_schema(summary="Developer Center: umumiy ko'rinish", tags=TAG, responses=OverviewSerializer)
    def get(self, request):
        return Response(services.overview(services.endpoints()))


class EndpointsView(DevcenterBase):
    @extend_schema(
        summary="Developer Center: endpointlar (rol bo'yicha filtr)",
        description="`role` berilsa, faqat o'sha rol chaqira oladigan endpointlar (bitta endpoint bir nechta rolda).",
        tags=TAG,
        parameters=[
            OpenApiParameter("role", str, enum=list(ROLE_ORDER), required=False),
            OpenApiParameter("version", str, required=False),
            OpenApiParameter("method", str, enum=["GET", "POST", "PUT", "PATCH", "DELETE"], required=False),
        ],
        responses=EndpointsSerializer,
    )
    def get(self, request):
        params = request.query_params
        role = params.get("role", "")
        if role and role not in ROLE_ORDER:
            raise serializers.ValidationError({"role": [f"Noma'lum rol. Mumkin: {', '.join(ROLE_ORDER)}"]})
        items = services.filter_endpoints(
            services.endpoints(), role=role, version=params.get("version", ""), method=params.get("method", "")
        )
        schema = catalog.get_schema()
        return Response(
            {
                "api_base_url": settings.PUBLIC_API_BASE_URL,
                "schema_url": "/api/v1/schema/",
                "docs_url": "/api/v1/docs/",
                "openapi_version": schema.get("openapi", ""),
                "api_version": schema.get("info", {}).get("version", ""),
                "count": len(items),
                "results": items,
            }
        )


class MobileGuideView(DevcenterBase):
    @extend_schema(
        summary="Developer Center: User / Studio mobil API",
        description="Mobil ilova funksiyalari real operatsiyalarga bog'langan. `PLANNED` — hali API yo'q.",
        tags=TAG,
        responses=MobileSerializer,
    )
    def get(self, request):
        return Response({"apps": services.mobile_guide(services.endpoints())})


class ChangelogView(DevcenterBase):
    @extend_schema(
        summary="Developer Center: API changelog",
        description="Har bir qabul qilingan kontrakt o'zgarishi (`manage.py api_contract --write`). Yangisi birinchi.",
        tags=TAG,
        responses=ChangelogSerializer,
    )
    def get(self, request):
        entries = list(reversed(contract.load_changelog()))
        return Response({"count": len(entries), "results": entries})
