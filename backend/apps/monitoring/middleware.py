"""Request metrics middleware — must be the outermost middleware so the timing covers everything.

Records method, path (no query string), route template, status, duration, request id, user id
and an error category. Nothing else from the request or response is read: no bodies, headers,
cookies or tokens ever reach the monitoring tables.
"""

import logging
import re
import time
import uuid

from django.utils import timezone

from .models import RequestLog, categorize
from .writer import cfg, writer

logger = logging.getLogger("apps.monitoring")

REQUEST_ID_HEADER = "X-Request-ID"
# 9+ digit runs = phone numbers, PINFLs or other identifiers someone put in a URL.
_LONG_DIGITS = re.compile(r"(?<![0-9a-fA-F])(?:%2B|\+)?\d{9,}(?![0-9a-fA-F])")
_NAMED_GROUP = re.compile(r"\(\?P<(\w+)>[^)]*\)")
_CONVERTER = re.compile(r"<(?:\w+:)?(\w+)>")


def safe_path(path: str) -> str:
    return _LONG_DIGITS.sub("[redacted]", path)[:255]


def route_template(resolver_match) -> str:
    """``api/v1/^users/(?P<pk>[^/.]+)/$`` -> ``/api/v1/users/{id}/`` (same spelling as the OpenAPI paths)."""
    if resolver_match is None or not resolver_match.route:
        return ""
    route = resolver_match.route.replace("^", "").replace("$", "").replace("\\.", ".")
    route = _NAMED_GROUP.sub(r"{\1}", route)
    route = _CONVERTER.sub(r"{\1}", route)
    route = route.replace("{pk}", "{id}")
    return f"/{route.lstrip('/')}"[:255]


class RequestMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _tracked(self, path: str) -> bool:
        conf = cfg()
        if not conf["ENABLED"]:
            return False
        if not any(path.startswith(p) for p in conf["INCLUDE_PREFIXES"]):
            return False
        return not any(path.startswith(p) for p in conf["EXCLUDE_PREFIXES"])

    def __call__(self, request):
        request_id = uuid.uuid4()
        request.request_id = request_id
        if not self._tracked(request.path):
            response = self.get_response(request)
            response[REQUEST_ID_HEADER] = str(request_id)
            return response

        started = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - started) * 1000
        response[REQUEST_ID_HEADER] = str(request_id)

        try:
            user = getattr(request, "user", None)
            user_id = user.pk if getattr(user, "is_authenticated", False) else None
            writer.submit(
                RequestLog(
                    created_at=timezone.now(),
                    method=request.method[:8],
                    path=safe_path(request.path),
                    route=route_template(getattr(request, "resolver_match", None)),
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                    request_id=request_id,
                    user_id=user_id,
                    error_category=categorize(response.status_code),
                )
            )
        except Exception:  # noqa: BLE001 - monitoring must never fail a request
            logger.warning("request metrics capture failed", exc_info=True)
        return response
