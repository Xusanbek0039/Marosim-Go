"""JWT issuing, rotation, reuse detection and revocation.

* Every token carries ``ver`` (= ``User.auth_version``). Bumping the version invalidates all
  of the user's access *and* refresh tokens immediately — used on deactivate, soft delete,
  password change and refresh-token reuse.
* Refresh tokens are single use (rotation + blacklist). Presenting an already used refresh
  token is treated as theft: every session of that user is revoked.
"""

from django.conf import settings
from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken

from apps.audit.services import AuditAction, record

from .models import User

INVALID_SESSION = "Sessiya yaroqsiz yoki muddati tugagan. Qayta kiring."


def issue_tokens(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh["ver"] = user.auth_version
    refresh["role"] = user.role
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def ensure_user_can_use_token(user: User | None, token) -> User:
    if user is None or not user.is_active or user.is_deleted:
        raise AuthenticationFailed(INVALID_SESSION, code="session_invalid")
    if token.get("ver") != user.auth_version:
        raise AuthenticationFailed(INVALID_SESSION, code="session_revoked")
    return user


def _user_from_token(token) -> User | None:
    user_id = token.get(settings.SIMPLE_JWT["USER_ID_CLAIM"])
    return User.objects.filter(pk=user_id).first() if user_id else None


def revoke_all_sessions(user: User) -> None:
    User.objects.filter(pk=user.pk).update(auth_version=F("auth_version") + 1)
    user.refresh_from_db(fields=["auth_version"])
    outstanding = OutstandingToken.objects.filter(
        user=user, expires_at__gt=timezone.now(), blacklistedtoken__isnull=True
    )
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=t) for t in outstanding], ignore_conflicts=True
    )


def rotate_refresh(raw: str, request=None) -> tuple[User, dict]:
    try:
        refresh = RefreshToken(raw)  # verifies signature, expiry, type and blacklist
    except TokenError:
        _detect_reuse(raw, request)
        raise AuthenticationFailed(INVALID_SESSION, code="session_invalid") from None

    user = ensure_user_can_use_token(_user_from_token(refresh), refresh)
    refresh.blacklist()
    return user, issue_tokens(user)


def _detect_reuse(raw: str, request) -> None:
    """A correctly signed but blacklisted refresh token means it was already used: revoke everything."""
    try:
        token = UntypedToken(raw)
    except TokenError:
        return
    jti = token.get("jti")
    if token.get("token_type") != "refresh" or not jti:
        return
    if BlacklistedToken.objects.filter(token__jti=jti).exists():
        user = _user_from_token(token)
        # A token from an already revoked generation (stale ``ver``) is not a theft signal.
        if user is not None and token.get("ver") == user.auth_version:
            revoke_all_sessions(user)
            record(request, AuditAction.TOKEN_REUSE, user, actor=user)


def blacklist_quietly(raw: str | None) -> User | None:
    if not raw:
        return None
    try:
        refresh = RefreshToken(raw)
    except TokenError:
        return None
    refresh.blacklist()
    return _user_from_token(refresh)


# ------------------------------------------------------------------- cookies
def set_auth_cookies(response: HttpResponse, tokens: dict) -> None:
    cfg = settings.AUTH_COOKIES
    jwt = settings.SIMPLE_JWT
    common = {"httponly": True, "secure": cfg["SECURE"], "domain": cfg["DOMAIN"]}
    response.set_cookie(
        cfg["ACCESS"],
        tokens["access"],
        max_age=int(jwt["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        path="/",
        samesite="Lax",
        **common,
    )
    response.set_cookie(
        cfg["REFRESH"],
        tokens["refresh"],
        max_age=int(jwt["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=cfg["REFRESH_PATH"],
        samesite="Strict",
        **common,
    )


def clear_auth_cookies(response: HttpResponse) -> None:
    cfg = settings.AUTH_COOKIES
    response.delete_cookie(cfg["ACCESS"], path="/", domain=cfg["DOMAIN"], samesite="Lax")
    response.delete_cookie(cfg["REFRESH"], path=cfg["REFRESH_PATH"], domain=cfg["DOMAIN"], samesite="Strict")
