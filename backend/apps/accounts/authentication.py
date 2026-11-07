"""JWT authentication for both clients of the API.

* Mobile / server clients: ``Authorization: Bearer <access>`` (no cookies, no CSRF).
* Web panel: the access token lives in an httpOnly cookie. Because browsers attach cookies
  automatically, cookie-authenticated unsafe requests must also pass Django's CSRF check.
"""

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication

from .tokens import ensure_user_can_use_token


class _CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason


def enforce_csrf(request) -> None:
    check = _CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied(f"CSRF tekshiruvi muvaffaqiyatsiz: {reason}")


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            raw = self.get_raw_token(header)
            if raw is None:
                return None
            return self._authenticate_raw(raw)

        raw = request.COOKIES.get(settings.AUTH_COOKIES["ACCESS"])
        if not raw:
            return None
        user, token = self._authenticate_raw(raw.encode())
        enforce_csrf(request)
        return user, token

    def _authenticate_raw(self, raw):
        validated = self.get_validated_token(raw)
        user = self.get_user(validated)
        ensure_user_can_use_token(user, validated)
        return user, validated
