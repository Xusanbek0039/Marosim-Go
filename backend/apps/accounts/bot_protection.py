"""Pluggable anti-bot check for public, unauthenticated write endpoints (register, later OTP send).

IP throttling (``register`` scope) is always on. On top of it a deployment can plug in a
challenge verifier (reCAPTCHA, Cloudflare Turnstile, hCaptcha, device attestation…) by pointing
``BOT_PROTECTION["GUARD"]`` at a callable ``guard(request) -> bool``. The mobile app then sends the
challenge token in the ``X-Bot-Token`` header. No guard configured = only throttling applies.
"""

from functools import lru_cache

from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.exceptions import PermissionDenied

BOT_TOKEN_HEADER = "X-Bot-Token"


class BotCheckFailed(PermissionDenied):
    default_detail = "Bot tekshiruvidan o'tilmadi. Qayta urinib ko'ring."
    default_code = "bot_check_failed"


@lru_cache(maxsize=1)
def _guard():
    path = (getattr(settings, "BOT_PROTECTION", {}) or {}).get("GUARD")
    return import_string(path) if path else None


def verify(request) -> None:
    guard = _guard()
    if guard is not None and not guard(request):
        raise BotCheckFailed()


def reset_cache() -> None:
    """For tests that swap the configured guard."""
    _guard.cache_clear()
