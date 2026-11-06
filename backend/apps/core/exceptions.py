"""One error shape for the whole API:

{"error": {"code": "...", "message": "...", "details": {...}}}
"""

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps.api")

MESSAGES = {
    "validation_error": "Yuborilgan ma'lumotlar noto'g'ri.",
    "not_authenticated": "Tizimga kirish talab qilinadi.",
    "authentication_failed": "Autentifikatsiya muvaffaqiyatsiz.",
    "permission_denied": "Bu amal uchun ruxsatingiz yo'q.",
    "not_found": "Ma'lumot topilmadi.",
    "method_not_allowed": "Bu metod qo'llab-quvvatlanmaydi.",
    "throttled": "So'rovlar juda ko'p. Birozdan so'ng qayta urinib ko'ring.",
    "unsupported_media_type": "Qo'llab-quvvatlanmaydigan format.",
    "parse_error": "So'rov tanasi noto'g'ri.",
    "conflict": "Amalni bajarib bo'lmaydi: bog'liq ma'lumotlar mavjud.",
    "server_error": "Serverda kutilmagan xatolik yuz berdi.",
}


class Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = MESSAGES["conflict"]
    default_code = "conflict"


class AccountLocked(exceptions.APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Juda ko'p muvaffaqiyatsiz urinish. Keyinroq qayta urinib ko'ring."
    default_code = "account_locked"


def _code_for(exc: exceptions.APIException) -> str:
    if isinstance(exc, exceptions.ValidationError):
        return "validation_error"
    codes = exc.get_codes()
    return codes if isinstance(codes, str) else exc.default_code


def api_exception_handler(exc, context):
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(getattr(exc, "message_dict", None) or exc.messages)
    elif isinstance(exc, ProtectedError):
        exc = Conflict()

    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        return Response(
            {"error": {"code": "server_error", "message": MESSAGES["server_error"], "details": None}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = _code_for(exc)
    details = None
    if isinstance(exc, exceptions.ValidationError):
        details = response.data if isinstance(response.data, dict) else {"non_field_errors": response.data}
        message = MESSAGES["validation_error"]
    else:
        detail = exc.detail
        message = str(detail) if isinstance(detail, str) else MESSAGES.get(code, str(detail))
        if isinstance(exc, exceptions.Throttled):
            message = MESSAGES["throttled"]
            details = {"retry_after": exc.wait}

    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response
