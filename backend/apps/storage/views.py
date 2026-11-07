"""Super Admin Google Drive connection API.

``connect``, ``status``, ``test`` and ``disconnect`` require a SUPER_ADMIN JWT (cookie or Bearer).
``callback`` is reached by Google's *browser redirect*, so it cannot carry our JWT: it is public
at the HTTP level and is authorized by the single-use state + browser-binding cookie instead
(see ``services.complete_callback``). It always answers with a redirect to the panel and an error
*code* — never tokens or Google's raw error text.
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import IsSuperAdmin

from . import client_config, services
from .models import StorageConnection

logger = logging.getLogger("apps.storage")
TAG = ["storage"]


class StorageConnectionSerializer(serializers.ModelSerializer):
    """Public facts only — the model holding the refresh token is a different table."""

    connected_by = serializers.SerializerMethodField()

    class Meta:
        model = StorageConnection
        fields = [
            "provider",
            "status",
            "account_email",
            "root_folder_id",
            "root_folder_name",
            "scopes",
            "connected_by",
            "connected_at",
            "last_checked_at",
            "last_success_at",
            "last_error_code",
        ]
        read_only_fields = fields

    def get_connected_by(self, obj) -> str | None:
        return obj.connected_by.full_name or obj.connected_by.identifier if obj.connected_by else None


StatusSerializer = inline_serializer(
    "GoogleDriveStatus",
    fields={
        "connection": StorageConnectionSerializer(),
        "has_credential": serializers.BooleanField(),
        "configuration": serializers.DictField(),
        "picker": serializers.DictField(),
    },
)
ConnectSerializer = inline_serializer(
    "GoogleDriveConnect",
    fields={"authorization_url": serializers.URLField(), "expires_at": serializers.DateTimeField()},
)
TestSerializer = inline_serializer(
    "GoogleDriveTest",
    fields={
        "ok": serializers.BooleanField(),
        "account_email": serializers.EmailField(),
        "quota_limit": serializers.IntegerField(allow_null=True),
        "quota_usage": serializers.IntegerField(allow_null=True),
        "connection": StorageConnectionSerializer(),
    },
)


def error_response(exc: services.StorageError, http_status=status.HTTP_409_CONFLICT) -> Response:
    messages = {
        "not_connected": "Google Drive ulanmagan.",
        "reconnect_required": "Google ruxsati bekor qilingan yoki muddati tugagan. Qayta ulang.",
        "encryption_key_missing": "Serverda GOOGLE_TOKEN_ENCRYPTION_KEY sozlanmagan.",
        "client_file_missing": "OAuth client JSON fayli serverda topilmadi.",
        "redirect_uri_mismatch": "Redirect URI Google Cloud sozlamasiga mos emas.",
    }
    return Response(
        {"error": {"code": exc.code, "message": messages.get(exc.code, "Google Drive bilan ishlashda xatolik."), "details": None}},
        status=http_status,
    )


class StatusView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(summary="Google Drive ulanish holati", tags=TAG, responses=StatusSerializer)
    def get(self, request):
        conn = services.connection()
        try:
            project_number = client_config.load().project_number
        except client_config.ClientConfigError:
            project_number = ""
        return Response(
            {
                "connection": StorageConnectionSerializer(conn).data,
                "has_credential": conn.has_credential,
                "configuration": client_config.diagnose(),
                # Phase B: Google Picker needs the Cloud project number as appId (not a secret).
                "picker": {"app_id": project_number, "ready": False},
            }
        )


class ConnectView(APIView):
    permission_classes = [IsSuperAdmin]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "storage_connect"

    @extend_schema(
        summary="Google Drive'ni ulashni boshlash",
        description=(
            "Google rozilik sahifasi URL'ini qaytaradi; panel brauzerni shu URL'ga yo'naltiradi. "
            "Bir martalik `state` (10 daqiqa), PKCE va brauzerga bog'lovchi httpOnly cookie yaratiladi."
        ),
        tags=TAG,
        responses={200: ConnectSerializer},
    )
    def get(self, request):
        try:
            start = services.start_connect(request.user)
        except services.StorageError as exc:
            return error_response(exc, status.HTTP_503_SERVICE_UNAVAILABLE)
        response = Response({"authorization_url": start.authorization_url, "expires_at": start.expires_at})
        response.set_cookie(
            services.BINDING_COOKIE,
            start.binding,
            max_age=settings.GOOGLE_OAUTH_STATE_TTL_SECONDS,
            path=services.BINDING_COOKIE_PATH,
            httponly=True,
            secure=settings.AUTH_COOKIES["SECURE"],
            samesite="Lax",  # sent on Google's top-level redirect back to the callback
            domain=settings.AUTH_COOKIES["DOMAIN"],
        )
        return response


class CallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "storage_callback"

    @extend_schema(
        summary="Google OAuth callback (brauzer redirect)",
        description=(
            "Google shu manzilga brauzerni yo'naltiradi. JWT talab qilinmaydi — so'rov bir martalik `state` "
            "va bog'lovchi cookie orqali aynan ulashni boshlagan Super Admin'ga bog'lanadi. "
            "Javob har doim panelga 302 redirect: `?google=connected` yoki `?google=error&reason=<kod>`."
        ),
        tags=TAG,
        parameters=[
            OpenApiParameter("state", str, required=False),
            OpenApiParameter("code", str, required=False),
            OpenApiParameter("error", str, required=False),
        ],
        responses={302: OpenApiResponse(description="Panelga qaytish")},
    )
    def get(self, request):
        params = request.query_params
        try:
            services.complete_callback(
                request,
                state=params.get("state", ""),
                code=params.get("code", ""),
                error=params.get("error", ""),
                binding=request.COOKIES.get(services.BINDING_COOKIE),
            )
            query = {"google": "connected"}
        except services.StorageError as exc:
            logger.warning("google oauth callback rejected: %s", exc.code)
            query = {"google": "error", "reason": exc.code}
        response = HttpResponseRedirect(f"{settings.PANEL_URL}/storage?{urlencode(query)}")
        response.delete_cookie(services.BINDING_COOKIE, path=services.BINDING_COOKIE_PATH, domain=settings.AUTH_COOKIES["DOMAIN"])
        response["Referrer-Policy"] = "no-referrer"  # the URL held ?code=
        return response


class TestConnectionView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Ulanishni tekshirish",
        description="Refresh token orqali yangi access token oladi va Drive `about.get` ni chaqiradi.",
        tags=TAG,
        request=None,
        responses={200: TestSerializer},
    )
    def post(self, request):
        try:
            info = services.test_connection(request)
        except services.StorageError as exc:
            return error_response(exc)
        return Response(
            {
                "ok": True,
                "account_email": info.email,
                "quota_limit": info.quota_limit,
                "quota_usage": info.quota_usage,
                "connection": StorageConnectionSerializer(services.connection()).data,
            }
        )


class DisconnectView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        summary="Google Drive'ni uzish",
        description="Refresh token Google'da revoke qilinadi (best effort) va serverdan o'chiriladi.",
        tags=TAG,
        request=None,
        responses={200: StorageConnectionSerializer},
    )
    def post(self, request):
        conn = services.disconnect(request, request.user)
        return Response(StorageConnectionSerializer(conn).data)
