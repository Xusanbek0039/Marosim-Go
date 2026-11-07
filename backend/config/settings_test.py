"""Settings used by the test-suite: deterministic throwaway secrets, in-memory DB."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-not-for-production-0123456789")
os.environ.setdefault("JWT_SIGNING_KEY", "test-jwt-signing-key-not-for-production-0123456789")
os.environ.setdefault("PINFL_ENCRYPTION_KEYS", "bW9ja19rZXlfZm9yX3Rlc3RzX29ubHlfMDEyMzQ1Njc=")
os.environ.setdefault("PINFL_HASH_KEY", "test-pinfl-hash-key")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")

from .settings import *  # noqa: E402,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # speed only
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "10000/min",
    "user": "10000/min",
    "login": "10000/min",
    "register": "10000/min",
    "storage_connect": "10000/min",
    "storage_callback": "10000/min",
    "token_refresh": "10000/min",
    "pinfl_reveal": "10000/min",
}
MEDIA_ROOT = BASE_DIR / ".test-media"  # noqa: F405
MONITORING = {**MONITORING, "ASYNC": False}  # noqa: F405 - deterministic, inline writes
GOOGLE_TOKEN_ENCRYPTION_KEYS = ["dGVzdF9nb29nbGVfdG9rZW5fa2V5X29ubHlfMDEyMzQ="]  # base64 of 32 test bytes
GOOGLE_OAUTH_CLIENT_FILE = BASE_DIR / ".test-missing-google-client.json"  # noqa: F405 - tests inject config
GOOGLE_OAUTH_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET = "test-client-secret"
