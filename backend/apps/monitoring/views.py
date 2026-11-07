"""API Monitoring for the Super Admin panel. Every endpoint here is SUPER_ADMIN only.

These are read-only views over recorded metrics and the generated OpenAPI schema. There is
intentionally no endpoint that sends HTTP requests on the caller's behalf (no SSRF surface);
a future "try it" console must call the API directly from the browser with the admin's own
session, against the documented same-origin paths only.
"""

from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import generics, serializers
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSuperAdmin

from . import catalog, services
from .filters import RequestLogFilter
from .models import RequestLog


class RequestLogSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source="created_at")

    class Meta:
        model = RequestLog
        fields = [
            "id",
            "timestamp",
            "method",
            "path",
            "route",
            "status_code",
            "duration_ms",
            "request_id",
            "user_id",
            "error_category",
        ]
        read_only_fields = fields


OverviewSerializer = inline_serializer(
    "MonitoringOverview",
    fields={
        "window": serializers.CharField(),
        "bucket": serializers.CharField(),
        "from": serializers.DateTimeField(),
        "to": serializers.DateTimeField(),
        "totals": serializers.DictField(),
        "series": serializers.ListField(child=serializers.DictField()),
        "top_endpoints": serializers.ListField(child=serializers.DictField()),
        "status_codes": serializers.ListField(child=serializers.DictField()),
        "error_categories": serializers.ListField(child=serializers.DictField()),
        "security": serializers.DictField(child=serializers.IntegerField()),
    },
)
CatalogSerializer = inline_serializer(
    "MonitoringEndpointCatalog",
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


class MonitoringBase:
    permission_classes = [IsSuperAdmin]


class OverviewView(MonitoringBase, APIView):
    @extend_schema(
        summary="API statistikasi (real so'rovlar asosida)",
        tags=["monitoring"],
        parameters=[OpenApiParameter("window", str, enum=list(services.WINDOWS), default=services.DEFAULT_WINDOW)],
        responses=OverviewSerializer,
    )
    def get(self, request):
        window = request.query_params.get("window", services.DEFAULT_WINDOW)
        return Response(services.overview(window, catalog_size=len(catalog.build())))


class RequestLogListView(MonitoringBase, generics.ListAPIView):
    serializer_class = RequestLogSerializer
    queryset = RequestLog.objects.all()
    filterset_class = RequestLogFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]  # structured filters only, no free-text search
    ordering_fields = ["created_at", "duration_ms", "status_code"]
    ordering = ["-created_at"]

    @extend_schema(summary="So'rovlar jurnali", tags=["monitoring"])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class EndpointCatalogView(MonitoringBase, APIView):
    @extend_schema(
        summary="API endpointlar katalogi (OpenAPI'dan avtomatik)",
        tags=["monitoring"],
        responses=CatalogSerializer,
    )
    def get(self, request):
        endpoints = catalog.build()
        stats = services.endpoint_stats()
        empty = {"count": 0, "client_errors": 0, "server_errors": 0, "avg_ms": None, "last_seen": None}
        for endpoint in endpoints:
            live = stats.get((endpoint["method"], endpoint["path"]))
            endpoint["traffic_24h"] = live or empty
            endpoint["status"] = live["status"] if live else "idle"
        schema = catalog.get_schema()
        return Response(
            {
                "api_base_url": settings.PUBLIC_API_BASE_URL,
                "schema_url": "/api/v1/schema/",
                "docs_url": "/api/v1/docs/",
                "openapi_version": schema.get("openapi", ""),
                "api_version": schema.get("info", {}).get("version", ""),
                "count": len(endpoints),
                "results": endpoints,
            }
        )
