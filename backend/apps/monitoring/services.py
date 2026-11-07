"""Aggregations over real ``RequestLog`` rows. No synthetic numbers: an empty window yields zeros."""

import math
from datetime import timedelta

from django.db.models import Avg, Count, Max, Q, QuerySet
from django.db.models.functions import TruncHour, TruncMinute
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog

from .models import RequestLog

WINDOWS = {
    "15m": (timedelta(minutes=15), "minute"),
    "1h": (timedelta(hours=1), "minute"),
    "24h": (timedelta(hours=24), "hour"),
    "7d": (timedelta(days=7), "hour"),
}
DEFAULT_WINDOW = "1h"

SUCCESS = Q(status_code__lt=400)
CLIENT_ERROR = Q(status_code__gte=400, status_code__lt=500)
SERVER_ERROR = Q(status_code__gte=500)


def window_bounds(window: str):
    span, bucket = WINDOWS.get(window, WINDOWS[DEFAULT_WINDOW])
    now = timezone.now()
    return now - span, now, span, bucket


def percentile(qs: QuerySet, fraction: float, total: int | None = None) -> float | None:
    """Exact nearest-rank percentile of ``duration_ms`` with a single indexed row fetch."""
    total = qs.count() if total is None else total
    if not total:
        return None
    index = max(0, math.ceil(fraction * total) - 1)
    value = qs.order_by("duration_ms").values_list("duration_ms", flat=True)[index : index + 1]
    return round(next(iter(value), 0.0), 2)


def _round(value) -> float | None:
    return None if value is None else round(value, 2)


def endpoint_status(count: int, server_errors: int, avg_ms: float | None) -> str:
    if not count:
        return "idle"
    rate = server_errors / count
    if rate >= 0.25:
        return "failing"
    if rate >= 0.05 or (avg_ms or 0) > 1500:
        return "degraded"
    return "healthy"


def _series(qs: QuerySet, start, end, bucket: str) -> list[dict]:
    trunc = TruncMinute if bucket == "minute" else TruncHour
    step = timedelta(minutes=1) if bucket == "minute" else timedelta(hours=1)
    rows = (
        qs.annotate(bucket=trunc("created_at"))
        .values("bucket")
        .annotate(
            total=Count("id"),
            client_errors=Count("id", filter=CLIENT_ERROR),
            server_errors=Count("id", filter=SERVER_ERROR),
            avg_ms=Avg("duration_ms"),
        )
        .order_by("bucket")
    )
    by_bucket = {row["bucket"]: row for row in rows}

    tz = timezone.get_current_timezone()
    cursor = timezone.localtime(start, tz).replace(second=0, microsecond=0)
    if bucket == "hour":
        cursor = cursor.replace(minute=0)
    series = []
    while cursor <= end:
        row = by_bucket.get(cursor) or {}
        series.append(
            {
                "t": cursor.isoformat(),
                "total": row.get("total", 0),
                "client_errors": row.get("client_errors", 0),
                "server_errors": row.get("server_errors", 0),
                "avg_ms": _round(row.get("avg_ms")),
            }
        )
        cursor += step
    return series


def overview(window: str = DEFAULT_WINDOW, catalog_size: int = 0) -> dict:
    start, end, span, bucket = window_bounds(window)
    qs = RequestLog.objects.filter(created_at__gte=start, created_at__lte=end)
    totals = qs.aggregate(
        total=Count("id"),
        success=Count("id", filter=SUCCESS),
        client_errors=Count("id", filter=CLIENT_ERROR),
        server_errors=Count("id", filter=SERVER_ERROR),
        throttled=Count("id", filter=Q(status_code=429)),
        avg_ms=Avg("duration_ms"),
    )
    total = totals["total"]
    minutes = span.total_seconds() / 60
    last_minute = RequestLog.objects.filter(created_at__gte=end - timedelta(minutes=1)).count()

    top = (
        qs.exclude(route="")
        .values("method", "route")
        .annotate(
            count=Count("id"),
            client_errors=Count("id", filter=CLIENT_ERROR),
            server_errors=Count("id", filter=SERVER_ERROR),
            avg_ms=Avg("duration_ms"),
            max_ms=Max("duration_ms"),
        )
        .order_by("-count")[:8]
    )
    statuses = qs.values("status_code").annotate(count=Count("id")).order_by("-count")[:10]
    categories = (
        qs.exclude(error_category="").values("error_category").annotate(count=Count("id")).order_by("-count")
    )
    audit = AuditLog.objects.filter(created_at__gte=start, created_at__lte=end)
    security = audit.aggregate(
        logins=Count("id", filter=Q(action=AuditAction.LOGIN)),
        failed_logins=Count("id", filter=Q(action=AuditAction.LOGIN_FAILED)),
        lockouts=Count("id", filter=Q(action=AuditAction.LOGIN_LOCKED)),
        token_reuse=Count("id", filter=Q(action=AuditAction.TOKEN_REUSE)),
        registrations=Count("id", filter=Q(action=AuditAction.REGISTER)),
    )

    return {
        "window": window if window in WINDOWS else DEFAULT_WINDOW,
        "bucket": bucket,
        "from": start,
        "to": end,
        "totals": {
            "total": total,
            "success": totals["success"],
            "client_errors": totals["client_errors"],
            "server_errors": totals["server_errors"],
            "throttled": totals["throttled"],
            "avg_ms": _round(totals["avg_ms"]),
            "p95_ms": percentile(qs, 0.95, total),
            "rpm": round(total / minutes, 2) if minutes else 0,
            "rpm_last_minute": last_minute,
            "active_endpoints": qs.exclude(route="").values("method", "route").distinct().count(),
            "documented_endpoints": catalog_size,
            "success_rate": round(totals["success"] / total * 100, 2) if total else None,
        },
        "series": _series(qs, start, end, bucket),
        "top_endpoints": [
            {
                **row,
                "avg_ms": _round(row["avg_ms"]),
                "max_ms": _round(row["max_ms"]),
                "status": endpoint_status(row["count"], row["server_errors"], row["avg_ms"]),
            }
            for row in top
        ],
        "status_codes": list(statuses),
        "error_categories": list(categories),
        "security": security,
    }


def endpoint_stats(since_hours: int = 24) -> dict[tuple[str, str], dict]:
    since = timezone.now() - timedelta(hours=since_hours)
    rows = (
        RequestLog.objects.filter(created_at__gte=since)
        .exclude(route="")
        .values("method", "route")
        .annotate(
            count=Count("id"),
            client_errors=Count("id", filter=CLIENT_ERROR),
            server_errors=Count("id", filter=SERVER_ERROR),
            avg_ms=Avg("duration_ms"),
            last_seen=Max("created_at"),
        )
    )
    return {
        (row["method"], row["route"]): {
            "count": row["count"],
            "client_errors": row["client_errors"],
            "server_errors": row["server_errors"],
            "avg_ms": _round(row["avg_ms"]),
            "last_seen": row["last_seen"],
            "status": endpoint_status(row["count"], row["server_errors"], row["avg_ms"]),
        }
        for row in rows
    }
