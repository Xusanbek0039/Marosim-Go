"""Authentication endpoints.

Login identifier: the phone number (normalized to E.164).

Web panel (default): tokens are set as httpOnly cookies and never returned in the body;
every state-changing request must carry the ``X-CSRFToken`` header (double submit).

Mobile apps: send ``X-Client: mobile``; tokens are returned in the body and the refresh
token is sent back in the body. The custom header forces a CORS preflight, so a hostile
web page cannot use this mode from a browser.
"""

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.middleware.csrf import get_token, rotate_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.services import AuditAction, diff, record, snapshot
from apps.core.exceptions import AccountLocked

from . import bot_protection, lockout
from . import phone as phone_utils
from .access import AccessNote
from .authentication import enforce_csrf
from .models import User
from .serializers import (
    LoginSerializer,
    MeSerializer,
    MeUpdateSerializer,
    RefreshSerializer,
    RegisterSerializer,
    TokenPairSerializer,
)
from .tokens import (
    blacklist_quietly,
    clear_auth_cookies,
    issue_tokens,
    rotate_refresh,
    set_auth_cookies,
)

INVALID_CREDENTIALS = "Telefon raqam yoki parol noto'g'ri."
LOCKED = "Juda ko'p muvaffaqiyatsiz urinish. Hisob vaqtincha bloklandi, keyinroq qayta urinib ko'ring."
PROFILE_FIELDS = ["first_name", "last_name", "profile_picture", "address"]

X_CLIENT = OpenApiParameter(
    "X-Client",
    str,
    OpenApiParameter.HEADER,
    required=False,
    enum=["mobile"],
    description="`mobile` — tokenlar javob tanasida qaytadi. Yuborilmasa: web panel (httpOnly cookie + CSRF).",
)


def is_mobile(request) -> bool:
    return request.headers.get("X-Client", "").lower() == "mobile"


def token_response(request, user: User, tokens: dict, status_code=status.HTTP_200_OK) -> Response:
    payload = {"user": MeSerializer(user, context={"request": request}).data}
    if is_mobile(request):
        return Response({**payload, **tokens}, status=status_code)
    response = Response(payload, status=status_code)
    set_auth_cookies(response, tokens)
    return response


class PublicAuthView(APIView):
    """Unauthenticated auth endpoints still answer 401 (not 403) with a WWW-Authenticate header."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        return 'Bearer realm="api"'


class CsrfView(APIView):
    """Sets the ``csrftoken`` cookie the web panel echoes back in ``X-CSRFToken``."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="CSRF cookie olish (web panel)",
        responses={200: OpenApiResponse(description="CSRF cookie o'rnatildi")},
    )
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        get_token(request)
        return Response({"detail": "ok"})


class RegisterView(PublicAuthView):
    """Public sign-up for the mobile app (there is no web sign-up page).

    The account always gets the USER role and ``is_phone_verified = false`` until an OTP flow
    exists. Web clients get no session: tokens are only issued to ``X-Client: mobile``.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"
    access_notes = {
        "*": AccessNote(
            conditions=(
                "Yaratilgan hisob roli har doim USER",
                "Tokenlar faqat `X-Client: mobile` uchun qaytariladi",
                "Bot himoyasi yoqilgan bo'lsa bot-token sarlavhasi talab qilinadi",
            )
        )
    }

    @extend_schema(
        summary="Ro'yxatdan o'tish (telefon + parol)",
        description=(
            "Rol har doim `USER`. Telefon raqam E.164 ga keltiriladi (`901234567` → `+998901234567`). "
            "Telefon egaligi hali tasdiqlanmagan (`is_phone_verified=false`). "
            f"Bot himoyasi yoqilgan bo'lsa, `{bot_protection.BOT_TOKEN_HEADER}` sarlavhasi talab qilinadi."
        ),
        parameters=[X_CLIENT],
        request=RegisterSerializer,
        responses={201: TokenPairSerializer},
    )
    def post(self, request):
        bot_protection.verify(request)
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
            record(request, AuditAction.REGISTER, user, actor=user)
        payload = {"user": MeSerializer(user, context={"request": request}).data}
        if is_mobile(request):
            payload.update(issue_tokens(user))
        return Response(payload, status=status.HTTP_201_CREATED)


class LoginView(PublicAuthView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"
    access_notes = {
        "*": AccessNote(
            conditions=(
                "Web (cookie) rejimida X-CSRFToken talab qilinadi",
                "Ketma-ket xatolardan so'ng hisob vaqtincha bloklanadi (429 account_locked)",
            )
        )
    }

    @extend_schema(
        summary="Tizimga kirish (telefon + parol)",
        description=(
            "Noto'g'ri telefon, noto'g'ri parol va nofaol hisob uchun bir xil `401 invalid_credentials` qaytadi. "
            "Ketma-ket muvaffaqiyatsiz urinishlardan so'ng hisob vaqtincha bloklanadi (`429 account_locked`)."
        ),
        parameters=[X_CLIENT],
        request=LoginSerializer,
        responses={200: TokenPairSerializer},
    )
    def post(self, request):
        if not is_mobile(request):
            enforce_csrf(request)

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_phone = serializer.validated_data["phone_number"]
        password = serializer.validated_data["password"]
        phone = phone_utils.try_normalize(raw_phone)
        lock_key = phone or raw_phone.strip()

        if lockout.is_locked(lock_key):
            raise AccountLocked(LOCKED)

        if phone is None:
            User().set_password(password)  # spend the same hashing time as a real lookup
            user = None
        else:
            user = authenticate(request, phone_number=phone, password=password)

        if user is None or user.is_deleted:
            locked_now = lockout.register_failure(lock_key)
            target = User.objects.filter(phone_number=phone).first() if phone else None
            label = phone or "invalid-phone"
            record(request, AuditAction.LOGIN_FAILED, target, target_label=label)
            if locked_now:
                record(request, AuditAction.LOGIN_LOCKED, target, target_label=label)
            raise AuthenticationFailed(INVALID_CREDENTIALS, code="invalid_credentials")

        lockout.reset(lock_key)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        record(request, AuditAction.LOGIN, user, actor=user)
        if not is_mobile(request):
            rotate_token(request)  # new CSRF secret per session
        return token_response(request, user, issue_tokens(user))


class RefreshView(PublicAuthView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_refresh"
    access_notes = {
        "*": AccessNote(
            conditions=(
                "Access token kerak emas, lekin amaldagi refresh token talab qilinadi (mobil: body, web: cookie+CSRF)",
                "Ishlatilgan refresh tokenni qayta yuborish barcha sessiyalarni bekor qiladi",
            )
        )
    }

    @extend_schema(
        summary="Tokenni yangilash (rotation)",
        description=(
            "Refresh token bir martalik. Ishlatilgan refresh tokenni qayta yuborish barcha sessiyalarni bekor qiladi."
        ),
        parameters=[X_CLIENT],
        request=RefreshSerializer,
        responses={200: TokenPairSerializer},
    )
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
                    {
                        "error": {
                            "code": "session_invalid",
                            "message": "Sessiya tugagan. Qayta kiring.",
                            "details": None,
                        }
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
                clear_auth_cookies(response)
                return response
            raise
        return token_response(request, user, tokens)


class LogoutView(PublicAuthView):
    access_notes = {
        "*": AccessNote(conditions=("Refresh token bo'lsa blacklistga qo'shiladi; web rejimida CSRF talab qilinadi",))
    }

    @extend_schema(
        summary="Tizimdan chiqish",
        description="Refresh token blacklistga qo'shiladi; web panelda cookie'lar tozalanadi.",
        parameters=[X_CLIENT],
        request=RefreshSerializer,
        responses={204: None},
    )
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
    access_notes = {
        "*": AccessNote(ownership="Faqat chaqiruvchining o'z hisobi (request.user)."),
        "patch": AccessNote(conditions=("Faqat first_name, last_name, profile_picture, address o'zgaradi",)),
    }

    @extend_schema(summary="Mening profilim", responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user, context={"request": request}).data)

    @extend_schema(
        summary="Profilni tahrirlash",
        description=(
            "Faqat `first_name`, `last_name`, `profile_picture`, `address` o'zgaradi. "
            "Rol, holat, telefon va JSHSHIR bu yerda o'zgartirilmaydi (boshqa maydonlar e'tiborsiz qoldiriladi)."
        ),
        request=MeUpdateSerializer,
        responses=MeSerializer,
    )
    def patch(self, request):
        user = request.user
        serializer = MeUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            before = snapshot(user, PROFILE_FIELDS)
            serializer.save()
            changes = diff(before, snapshot(user, PROFILE_FIELDS))
            if changes:
                record(request, AuditAction.UPDATE, user, changes=changes, actor=user)
        return Response(MeSerializer(user, context={"request": request}).data)
