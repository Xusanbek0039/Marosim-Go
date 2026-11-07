"""Request metrics — deliberately separate from the audit log.

* ``AuditLog`` (apps.audit) answers *who did what* to which record; it is append-only and kept.
* ``RequestLog`` answers *how the API behaves* (traffic, status codes, latency). It holds no
  request/response bodies, headers, cookies, tokens, query strings or personal data — only the
  fields below — and is pruned after ``MONITORING["RETENTION_DAYS"]``.
"""

from django.db import models


class ErrorCategory(models.TextChoices):
    NONE = "", "—"
    VALIDATION = "validation", "Validatsiya"
    AUTHENTICATION = "authentication", "Autentifikatsiya"
    PERMISSION = "permission", "Ruxsat"
    NOT_FOUND = "not_found", "Topilmadi"
    METHOD = "method_not_allowed", "Metod"
    CONFLICT = "conflict", "Konflikt"
    PAYLOAD = "payload", "So'rov hajmi/format"
    THROTTLED = "throttled", "Throttling"
    CLIENT = "client_error", "Mijoz xatosi"
    SERVER = "server_error", "Server xatosi"


_BY_STATUS = {
    400: ErrorCategory.VALIDATION,
    401: ErrorCategory.AUTHENTICATION,
    403: ErrorCategory.PERMISSION,
    404: ErrorCategory.NOT_FOUND,
    405: ErrorCategory.METHOD,
    409: ErrorCategory.CONFLICT,
    413: ErrorCategory.PAYLOAD,
    415: ErrorCategory.PAYLOAD,
    429: ErrorCategory.THROTTLED,
}


def categorize(status_code: int) -> str:
    if status_code < 400:
        return ErrorCategory.NONE
    if status_code >= 500:
        return ErrorCategory.SERVER
    return _BY_STATUS.get(status_code, ErrorCategory.CLIENT)


class RequestLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(db_index=True)
    method = models.CharField(max_length=8)
    #: Concrete path without the query string, with long digit runs masked.
    path = models.CharField(max_length=255)
    #: URL pattern, OpenAPI style (``/api/v1/users/{id}/``) — the grouping key for statistics.
    route = models.CharField(max_length=255, blank=True)
    status_code = models.PositiveSmallIntegerField()
    duration_ms = models.FloatField()
    request_id = models.UUIDField(db_index=True)
    # Plain id, not a FK: metrics writes must stay cheap and survive user deletion.
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    error_category = models.CharField(max_length=24, choices=ErrorCategory.choices, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["route", "created_at"]),
            models.Index(fields=["status_code", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.method} {self.path} {self.status_code}"
