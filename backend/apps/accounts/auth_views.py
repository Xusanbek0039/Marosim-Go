"""Authentication endpoints.

Web panel (default): tokens are set as httpOnly cookies and never returned in the body;
every state-changing request must carry the ``X-CSRFToken`` header (double submit).

Mobile apps: send ``X-Client: mobile``; tokens are returned in the body and the refresh
token is sent back in the body. The custom header forces a CORS preflight, so a hostile
web page cannot use this mode from a browser.
"""

from django.conf import settings
from django.contrib.auth import authenticate
from django.middleware.csrf import get_token, rotate_token
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.services import AuditAction, record
from apps.core.exceptions import AccountLocked

from . import lockout
from .authentication import enforce_csrf
from .models import User
from .serializers import LoginSerializer, MeSerializer, RefreshSerializer
from .tokens import (
    blacklist_quietly,
    clear_auth_cookies,
    issue_tokens,
    rotate_refresh,
    set_auth_cookies,
)

INVALID_CREDENTIALS = "Email yoki parol noto'g'ri."
LOCKED = "Juda ko'p muvaffaqiyatsiz urinish. Hisob vaqtincha bloklandi, keyinroq qayta urinib ko'ring."


def is_mobile(request) -> bool:
    return request.headers.get("X-Client", "").lower() == "mobile"


def token_response(request, user: User, tokens: dict, status_code=status.HTTP_200_OK) -> Response:
    payload = {"user": MeSerializer(user, context={"request": request}).data}
    if is_mobile(request):
        return Response({**payload, **tokens}, status=status_code)
    response = Response(payload, status=status_code)
    set_auth_cookies(response, tokens)
    return response


class CsrfView(APIView):
    """Sets the ``csrftoken`` cookie the web panel echoes back in ``X-CSRFToken``."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiResponse(description="CSRF cookie o'rnatildi")})
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        get_token(request)
        return Response({"detail": "ok"})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: MeSerializer})
    def post(self, request):
        if not is_mobile(request):
            enforce_csrf(request)

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        if lockout.is_locked(email):
            raise AccountLocked(LOCKED)

        user = authenticate(request, username=email, password=password)
        if user is None or user.is_deleted:
            locked_now = lockout.register_failure(email)
            target = User.objects.filter(email__iexact=email).first()
            record(request, AuditAction.LOGIN_FAILED, target, target_label=email)
            if locked_now:
                record(request, AuditAction.LOGIN_LOCKED, target, target_label=email)
            raise AuthenticationFailed(INVALID_CREDENTIALS, code="invalid_credentials")

        lockout.reset(email)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        record(request, AuditAction.LOGIN, user, actor=user)
        if not is_mobile(request):
            rotate_token(request)  # new CSRF secret per session
        return token_response(request, user, issue_tokens(user))


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_refresh"

    @extend_schema(request=RefreshSerializer, responses={200: MeSerializer})
    def post(self, request):
        if is_mobile(request):
            serializer = RefreshSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            raw = serializer.validated_data.get("refresh")
        else:
            enforce_csrf(request)
            raw = request.COOKIES.get(settings.AUTH_COOKIES["REFRESH"])
        if not raw:
            raise AuthenticationFailed("Refresh token topilmadi.", code="session_invalid")
        try:
            user, tokens = rotate_refresh(raw, request)
        except AuthenticationFailed:
            if not is_mobile(request):
                # Make sure a rejected browser session is fully cleared.
                response = Response(
                    {"error": {"code": "session_invalid", "message": "Sessiya tugagan. Qayta kiring.", "details": None}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
                clear_auth_cookies(response)
                return response
            raise
        return token_response(request, user, tokens)


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=RefreshSerializer, responses={204: None})
    def post(self, request):
        if is_mobile(request):
            raw = (request.data or {}).get("refresh")
        else:
            enforce_csrf(request)
            raw = request.COOKIES.get(settings.AUTH_COOKIES["REFRESH"])
        user = blacklist_quietly(raw)
        if user is not None:
            record(request, AuditAction.LOGOUT, user, actor=user)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user, context={"request": request}).data)
