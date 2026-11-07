"""Per-account brute-force protection (complements IP throttling).

Keyed by the normalized login identifier (E.164 phone). Only a SHA-256 digest reaches the cache.
"""

import hashlib

from django.conf import settings
from django.core.cache import cache


def _key(kind: str, identifier: str) -> str:
    digest = hashlib.sha256(identifier.strip().lower().encode()).hexdigest()
    return f"login:{kind}:{digest}"


def is_locked(identifier: str) -> bool:
    return bool(cache.get(_key("lock", identifier)))


def register_failure(identifier: str) -> bool:
    """Returns True when this failure locked the account."""
    cfg = settings.LOGIN_LOCKOUT
    key = _key("fail", identifier)
    cache.add(key, 0, timeout=cfg["WINDOW_SECONDS"])
    try:
        failures = cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.set(key, 1, timeout=cfg["WINDOW_SECONDS"])
        failures = 1
    if failures >= cfg["MAX_FAILURES"]:
        cache.set(_key("lock", identifier), True, timeout=cfg["LOCK_SECONDS"])
        cache.delete(key)
        return True
    return False


def reset(identifier: str) -> None:
    cache.delete_many([_key("fail", identifier), _key("lock", identifier)])
