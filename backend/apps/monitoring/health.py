"""Public liveness / readiness probes.

Responses carry only coarse ``ok``/``fail`` flags — never hostnames, versions, error messages
or configuration. They are excluded from request metrics (probes would drown real traffic)
and from throttling (load balancers poll them).
"""

import logging
import uuid

from django.core.cache import cache
from django.db import connections
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("apps.monitoring")

LiveSerializer = inline_serializer("HealthLive", fields={"status": serializers.CharField()})
ReadySerializer = inline_serializer(
    "HealthReady",
    fields={
        "status": serializers.ChoiceField(choices=["ok", "degraded", "unavailable"]),
        "checks": serializers.DictField(child=serializers.ChoiceField(choices=["ok", "fail"])),
    },
)


def check_database() -> bool:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone()[0] == 1
    except Exception:  # noqa: BLE001
        logger.warning("readiness: database check failed", exc_info=True)
        return False


def check_cache() -> bool:
    key = f"health:{uuid.uuid4().hex}"
    try:
        cache.set(key, "1", timeout=5)
        ok = cache.get(key) == "1"
        cache.delete(key)
        return ok
    except Exception:  # noqa: BLE001
        logger.warning("readiness: cache check failed", exc_info=True)
        return False


class HealthBase(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []


class LiveView(HealthBase):
    @extend_schema(summary="Liveness — jarayon ishlayaptimi", tags=["health"], responses=LiveSerializer)
    def get(self, request):
        return Response({"status": "ok"})


class ReadyView(HealthBase):
    @extend_schema(
        summary="Readiness — bog'liqliklar (database, cache) tayyormi",
        description="`database` ishlamasa 503 `unavailable`; faqat `cache` ishlamasa 200 `degraded`.",
        tags=["health"],
        responses={200: ReadySerializer, 503: ReadySerializer},
    )
    def get(self, request):
        checks = {"database": check_database(), "cache": check_cache()}
        if not checks["database"]:
            overall, code = "unavailable", status.HTTP_503_SERVICE_UNAVAILABLE
        elif not all(checks.values()):
            overall, code = "degraded", status.HTTP_200_OK
        else:
            overall, code = "ok", status.HTTP_200_OK
        return Response(
            {"status": overall, "checks": {name: "ok" if ok else "fail" for name, ok in checks.items()}},
            status=code,
        )
