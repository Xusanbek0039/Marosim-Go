import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.audit.models import AuditAction, AuditLog

from .conftest import PASSWORD

LOGIN = "/api/v1/auth/login/"
REFRESH = "/api/v1/auth/refresh/"
LOGOUT = "/api/v1/auth/logout/"
ME = "/api/v1/auth/me/"
CSRF = "/api/v1/auth/csrf/"
ACCESS = settings.AUTH_COOKIES["ACCESS"]
REFRESH_COOKIE = settings.AUTH_COOKIES["REFRESH"]


def web_client() -> APIClient:
    client = APIClient(enforce_csrf_checks=True)
    client.get(CSRF)
    return client


def csrf_headers(client) -> dict:
    return {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value}


def web_login(client, user):
    return client.post(LOGIN, {"email": user.email, "password": PASSWORD}, format="json", **csrf_headers(client))


# ----------------------------------------------------------------- web flow
def test_web_login_sets_httponly_cookies_and_hides_tokens(super_admin):
    client = web_client()
    res = web_login(client, super_admin)
    assert res.status_code == 200
    assert "access" not in res.data and "refresh" not in res.data
    assert res.data["user"]["role"] == Role.SUPER_ADMIN
    access, refresh = res.cookies[ACCESS], res.cookies[REFRESH_COOKIE]
    assert access["httponly"] and refresh["httponly"]
    assert refresh["path"] == "/api/v1/auth/"
    assert refresh["samesite"] == "Strict"
    assert res.cookies[settings.AUTH_COOKIES["SESSION_HINT"]].value == "1"


def test_web_login_requires_csrf(super_admin):
    client = APIClient(enforce_csrf_checks=True)
    res = client.post(LOGIN, {"email": super_admin.email, "password": PASSWORD}, format="json")
    assert res.status_code == 403


def test_cookie_auth_requires_csrf_for_unsafe_methods(super_admin, plain_user):
    client = web_client()
    web_login(client, super_admin)
    assert client.get(ME).status_code == 200
    url = f"/api/v1/users/{plain_user.pk}/"
    assert client.patch(url, {"address": "x"}, format="json").status_code == 403
    assert client.patch(url, {"address": "x"}, format="json", **csrf_headers(client)).status_code == 200


def test_web_refresh_rotates_and_old_refresh_is_rejected(super_admin):
    client = web_client()
    web_login(client, super_admin)
    old_refresh = client.cookies[REFRESH_COOKIE].value
    res = client.post(REFRESH, **csrf_headers(client))
    assert res.status_code == 200
    assert client.cookies[REFRESH_COOKIE].value != old_refresh


def test_web_logout_clears_cookies_and_blacklists(super_admin):
    client = web_client()
    web_login(client, super_admin)
    refresh = client.cookies[REFRESH_COOKIE].value
    res = client.post(LOGOUT, **csrf_headers(client))
    assert res.status_code == 204
    assert res.cookies[ACCESS].value == ""
    assert res.cookies[settings.AUTH_COOKIES["SESSION_HINT"]].value == ""
    mobile = APIClient(HTTP_X_CLIENT="mobile")
    assert mobile.post(REFRESH, {"refresh": refresh}, format="json").status_code == 401


# -------------------------------------------------------------- mobile flow
def mobile_login(user):
    client = APIClient(HTTP_X_CLIENT="mobile")
    return client, client.post(LOGIN, {"email": user.email, "password": PASSWORD}, format="json")


def test_mobile_login_returns_tokens(plain_user):
    _, res = mobile_login(plain_user)
    assert res.status_code == 200
    assert {"access", "refresh", "user"} <= set(res.data)
    assert ACCESS not in res.cookies


def test_refresh_token_reuse_revokes_all_sessions(plain_user):
    client, res = mobile_login(plain_user)
    first_refresh = res.data["refresh"]
    rotated = client.post(REFRESH, {"refresh": first_refresh}, format="json")
    assert rotated.status_code == 200
    new_access = rotated.data["access"]

    # attacker replays the stolen (already used) refresh token
    assert client.post(REFRESH, {"refresh": first_refresh}, format="json").status_code == 401
    # ...which kills the legitimate session too
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
    assert client.get(ME).status_code == 401
    assert client.post(REFRESH, {"refresh": rotated.data["refresh"]}, format="json").status_code == 401
    assert AuditLog.objects.filter(action=AuditAction.TOKEN_REUSE, target_id=str(plain_user.pk)).exists()


def test_wrong_password_is_generic_and_audited(plain_user):
    client = APIClient(HTTP_X_CLIENT="mobile")
    res = client.post(LOGIN, {"email": plain_user.email, "password": "wrong-password"}, format="json")
    unknown = client.post(LOGIN, {"email": "nobody@example.uz", "password": "wrong-password"}, format="json")
    assert res.status_code == unknown.status_code == 401
    assert res.data["error"]["message"] == unknown.data["error"]["message"]
    assert AuditLog.objects.filter(action=AuditAction.LOGIN_FAILED).count() == 2


def test_account_lockout_after_repeated_failures(plain_user):
    client = APIClient(HTTP_X_CLIENT="mobile")
    for _ in range(settings.LOGIN_LOCKOUT["MAX_FAILURES"]):
        client.post(LOGIN, {"email": plain_user.email, "password": "wrong-password"}, format="json")
    res = client.post(LOGIN, {"email": plain_user.email, "password": PASSWORD}, format="json")
    assert res.status_code == 429
    assert res.data["error"]["code"] == "account_locked"


def test_inactive_user_cannot_login(make_user):
    user = make_user(Role.USER, is_active=False)
    _, res = mobile_login(user)
    assert res.status_code == 401


@pytest.mark.parametrize("field,value", [("is_active", False), ("password", "Boshqa-Yangi-Parol-77")])
def test_deactivation_or_password_change_revokes_existing_tokens(client_for, super_admin, plain_user, field, value):
    victim_client, res = mobile_login(plain_user)
    victim_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    assert victim_client.get(ME).status_code == 200

    admin = client_for(super_admin)
    assert admin.patch(f"/api/v1/users/{plain_user.pk}/", {field: value}, format="json").status_code == 200
    assert victim_client.get(ME).status_code == 401
    assert victim_client.post(REFRESH, {"refresh": res.data["refresh"]}, format="json").status_code == 401


def test_me_requires_auth(anon):
    res = anon.get(ME)
    assert res.status_code == 401
    assert res.data["error"]["code"] == "not_authenticated"


def test_api_responses_are_not_cacheable(client_for, super_admin):
    res = client_for(super_admin).get(ME)
    assert res["Cache-Control"] == "no-store"
    assert res.data["permissions"]  # super admin has every permission
