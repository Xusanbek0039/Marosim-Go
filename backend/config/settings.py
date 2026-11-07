"""MarosimGo backend settings.

Every secret and environment-specific value comes from environment variables
(or a local ``backend/.env`` file in development). See ``.env.example``.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

# --------------------------------------------------------------------------- core
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # local
    "apps.core",
    "apps.audit",
    "apps.accounts",
    "apps.studios",
    "apps.dashboard",
    "apps.monitoring",
]

MIDDLEWARE = [
    # Outermost, so request timing covers the whole stack.
    "apps.monitoring.middleware.RequestMetricsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.ApiSecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    }
]

# ----------------------------------------------------------------------- database
# SQLite by default; switch to PostgreSQL by setting e.g.
# DATABASE_URL=postgres://marosimgo:password@localhost:5432/marosimgo
DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
# No ATOMIC_REQUESTS: audit/security records must survive a failed request.
# Write paths use explicit transaction.atomic blocks instead.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://marosimgo")}

# --------------------------------------------------------------------------- auth
AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("phone_number", "first_name", "last_name", "email")},
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Number of reverse proxies in front of Django (Next.js rewrite proxy = 1).
# Used for client IP detection (throttling, audit). Never trust X-Forwarded-For otherwise.
NUM_PROXIES = env.int("NUM_PROXIES", default=0)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.accounts.authentication.CookieJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env.str("THROTTLE_ANON", default="60/min"),
        "user": env.str("THROTTLE_USER", default="600/min"),
        "login": env.str("THROTTLE_LOGIN", default="5/min"),
        "register": env.str("THROTTLE_REGISTER", default="10/hour"),
        "token_refresh": env.str("THROTTLE_REFRESH", default="30/min"),
        "pinfl_reveal": env.str("THROTTLE_PINFL_REVEAL", default="20/hour"),
    },
    "NUM_PROXIES": NUM_PROXIES or None,
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "apps.core.schema.MarosimAutoSchema",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append("rest_framework.renderers.BrowsableAPIRenderer")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=10)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("JWT_SIGNING_KEY"),
    "ISSUER": "marosimgo",
    "AUDIENCE": "marosimgo-api",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "LEEWAY": 5,
}

# HttpOnly auth cookies for the web panel (mobile clients use the Authorization header).
AUTH_COOKIES = {
    "ACCESS": "mg_access",
    "REFRESH": "mg_refresh",
    # Non-secret marker ("1") so the Next.js proxy can tell a session probably exists.
    "SESSION_HINT": "mg_session",
    "REFRESH_PATH": "/api/v1/auth/",
    "SECURE": env.bool("AUTH_COOKIE_SECURE", default=not DEBUG),
    "DOMAIN": env.str("AUTH_COOKIE_DOMAIN", default=None),
}

# Login identifier: E.164 phone numbers from these regions (ISO 3166-1 alpha-2, first = default).
PHONE_ALLOWED_REGIONS = tuple(env.list("PHONE_ALLOWED_REGIONS", default=["UZ"]))

# Optional challenge verifier for public sign-up: dotted path to ``guard(request) -> bool``.
BOT_PROTECTION = {"GUARD": env.str("BOT_PROTECTION_GUARD", default="") or None}

# Brute-force protection (per phone number), on top of IP-based throttling.
LOGIN_LOCKOUT = {
    "MAX_FAILURES": env.int("LOGIN_MAX_FAILURES", default=5),
    "WINDOW_SECONDS": env.int("LOGIN_FAILURE_WINDOW", default=15 * 60),
    "LOCK_SECONDS": env.int("LOGIN_LOCK_SECONDS", default=15 * 60),
}

# --------------------------------------------------------------- PINFL protection
# Comma separated Fernet keys; the first one encrypts, all of them decrypt (rotation).
PINFL_ENCRYPTION_KEYS = env.list("PINFL_ENCRYPTION_KEYS")
# Separate secret for the deterministic HMAC used for uniqueness / exact search.
PINFL_HASH_KEY = env("PINFL_HASH_KEY")

# ------------------------------------------------------------------- CORS & CSRF
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ["accept", "authorization", "content-type", "x-csrftoken", "x-client"]
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:3000"])
CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_HTTPONLY = False  # the SPA must read it to send X-CSRFToken (double submit)
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = AUTH_COOKIES["SECURE"]
SESSION_COOKIE_SECURE = AUTH_COOKIES["SECURE"]

# ------------------------------------------------------------- security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
# Behind the Next.js proxy: build absolute URLs (pagination, media) with the panel's host.
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=False)
if env.bool("USE_X_FORWARDED_PROTO", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ------------------------------------------------------------------ uploads/media
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env.str("MEDIA_ROOT", default=str(BASE_DIR / "media")))
# Let Django serve uploads (development / small deployments). In production prefer nginx.
SERVE_MEDIA = env.bool("SERVE_MEDIA", default=DEBUG)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200
IMAGE_UPLOAD = {
    "MAX_BYTES": 5 * 1024 * 1024,
    "MAX_PIXELS": 25_000_000,
    "MAX_SIDE": 1024,
    "ALLOWED_FORMATS": ("JPEG", "PNG", "WEBP"),
}

# ------------------------------------------------------------------- i18n / time
LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

# ----------------------------------------------------------------------- OpenAPI
SPECTACULAR_SETTINGS = {
    "TITLE": "MarosimGo API",
    "DESCRIPTION": (
        "MarosimGo REST API (v1). Login identifikatori — telefon raqam (E.164).\n\n"
        "* **Mobil:** `X-Client: mobile` + `Authorization: Bearer <access>`.\n"
        "* **Web panel:** httpOnly cookie + `X-CSRFToken`.\n\n"
        "Har bir operatsiyada `x-access` (rol/ruxsat) va standart xato javoblari avtomatik hujjatlashtiriladi."
    ),
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "RoleEnum": "apps.accounts.models.Role",
        "ClientRoleEnum": ["USER", "STUDIO"],
        "AdminRoleEnum": ["ADMIN"],
    },
    "SERVE_PERMISSIONS": (
        ["rest_framework.permissions.AllowAny"] if DEBUG else ["apps.accounts.permissions.IsSuperAdmin"]
    ),
}

# -------------------------------------------------------------------- monitoring
MONITORING = {
    "ENABLED": env.bool("MONITORING_ENABLED", default=True),
    # Write request metrics from a background thread (False = inline, used by tests).
    "ASYNC": env.bool("MONITORING_ASYNC", default=True),
    "BATCH_SIZE": 200,
    "FLUSH_INTERVAL_SECONDS": 2.0,
    "QUEUE_MAX": 10_000,
    "RETENTION_DAYS": env.int("MONITORING_RETENTION_DAYS", default=14),
    "MAX_ROWS": env.int("MONITORING_MAX_ROWS", default=2_000_000),
    "PRUNE_INTERVAL_SECONDS": 3600,
    "CATALOG_TTL_SECONDS": 300,
    "INCLUDE_PREFIXES": ["/api/"],
    # Probes, the monitoring UI itself and the docs would only add noise.
    "EXCLUDE_PREFIXES": ["/api/v1/health/", "/api/v1/monitoring/", "/api/v1/schema/", "/api/v1/docs/"],
}
# Base URL shown in the API command examples of the monitoring catalog (documentation only).
PUBLIC_API_BASE_URL = env.str("PUBLIC_API_BASE_URL", default="http://localhost:8000").rstrip("/")

# ----------------------------------------------------------------------- logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact": {"()": "apps.core.logging.SensitiveDataFilter"}},
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain", "filters": ["redact"]},
    },
    "root": {"handlers": ["console"], "level": env.str("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
