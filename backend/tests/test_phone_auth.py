import json

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts import bot_protection
from apps.accounts import phone as phone_utils
from apps.accounts.models import Role, User
from apps.audit.models import AuditAction, AuditLog

from .conftest import PASSWORD, image_file

REGISTER = "/api/v1/auth/register/"
LOGIN = "/api/v1/auth/login/"
REFRESH = "/api/v1/auth/refresh/"
LOGOUT = "/api/v1/auth/logout/"
ME = "/api/v1/auth/me/"
STRONG = "SecurePassword123!"


def mobile() -> APIClient:
    return APIClient(HTTP_X_CLIENT="mobile")


def register(client=None, **body):
    data = {"phone_number": "+998901234567", "password": STRONG, "password_confirm": STRONG, **body}
    return (client or mobile()).post(REGISTER, data, format="json")


# ------------------------------------------------------------ normalization
@pytest.mark.parametrize(
    "raw",
    ["+998901234567", "998901234567", "901234567", "+998 90 123-45-67", "(90) 123 45 67", "00998901234567"],
)
def test_phone_normalization_to_e164(raw):
    assert phone_utils.normalize(raw) == "+998901234567"


@pytest.mark.parametrize("raw", ["", "12345", "+998001234567", "+9989012345678", "+14155552671", "abc", "9" * 40])
def test_invalid_phone_numbers_rejected(raw):
    with pytest.raises(ValidationError):
        phone_utils.normalize(raw)


def test_phone_mask():
    assert phone_utils.mask("+998901234567") == "+99890***4567"


# ----------------------------------------------------------------- register
@pytest.mark.django_db
def test_register_success_creates_unverified_user_with_hashed_password():
    res = register()
    assert res.status_code == 201, res.data
    assert {"user", "access", "refresh"} <= set(res.data)
    assert res.data["user"]["phone_number"] == "+998901234567"
    assert res.data["user"]["role"] == Role.USER
    assert res.data["user"]["is_phone_verified"] is False
    assert "password" not in res.data["user"]

    user = User.objects.get(phone_number="+998901234567")
    assert user.password != STRONG and user.check_password(STRONG)
    assert user.pinfl_hash is None and user.is_phone_verified is False
    assert AuditLog.objects.filter(action=AuditAction.REGISTER, target_id=str(user.pk)).exists()

    # the issued access token works against the mobile API
    client = mobile()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    assert client.get(ME).data["phone_number"] == "+998901234567"


@pytest.mark.django_db
def test_register_normalizes_phone():
    res = register(phone_number="90 123 45 67")
    assert res.status_code == 201
    assert res.data["user"]["phone_number"] == "+998901234567"


@pytest.mark.django_db
def test_register_web_client_gets_no_session():
    res = register(client=APIClient())
    assert res.status_code == 201
    assert "access" not in res.data and "refresh" not in res.data
    assert not res.cookies


@pytest.mark.django_db
@pytest.mark.parametrize("spelling", ["+998901234567", "998901234567", "901234567"])
def test_register_duplicate_phone_rejected_in_any_spelling(spelling):
    assert register().status_code == 201
    res = register(phone_number=spelling)
    assert res.status_code == 400
    assert "phone_number" in res.data["error"]["details"]
    assert User.objects.filter(phone_number="+998901234567").count() == 1


@pytest.mark.django_db
def test_register_duplicate_of_soft_deleted_account_rejected(make_user):
    make_user(phone_number="+998901234567").soft_delete()
    assert register().status_code == 400


@pytest.mark.django_db
def test_register_invalid_phone():
    res = register(phone_number="12345")
    assert res.status_code == 400
    assert "phone_number" in res.data["error"]["details"]


@pytest.mark.django_db
@pytest.mark.parametrize("weak", ["short1!", "1234567890123", "password1234", "+998901234567"])
def test_register_weak_password(weak):
    res = register(password=weak, password_confirm=weak)
    assert res.status_code == 400
    assert "password" in res.data["error"]["details"]
    assert not User.objects.exists()


@pytest.mark.django_db
def test_register_password_mismatch():
    res = register(password_confirm="SecurePassword123?")
    assert res.status_code == 400
    assert "password_confirm" in res.data["error"]["details"]


@pytest.mark.django_db
def test_register_cannot_escalate_role_or_flags():
    res = register(role=Role.SUPER_ADMIN, is_staff=True, is_phone_verified=True, admin_permissions=["users.view"])
    assert res.status_code == 201
    user = User.objects.get(phone_number="+998901234567")
    assert user.role == Role.USER and not user.is_staff and not user.is_phone_verified
    assert user.effective_permissions() == []


@pytest.mark.django_db
def test_register_is_rate_limited(monkeypatch):
    from rest_framework.throttling import ScopedRateThrottle

    monkeypatch.setattr(
        ScopedRateThrottle, "THROTTLE_RATES", {**ScopedRateThrottle.THROTTLE_RATES, "register": "2/hour"}
    )
    codes = [register(phone_number=f"+99890123450{i}").status_code for i in range(3)]
    assert codes == [201, 201, 429]


def deny_all(request):
    return request.headers.get(bot_protection.BOT_TOKEN_HEADER) == "valid-challenge"


@pytest.mark.django_db
def test_register_bot_guard_hook():
    with override_settings(BOT_PROTECTION={"GUARD": "tests.test_phone_auth.deny_all"}):
        bot_protection.reset_cache()
        try:
            blocked = register()
            allowed = mobile().post(
                REGISTER,
                {"phone_number": "+998901234567", "password": STRONG, "password_confirm": STRONG},
                format="json",
                HTTP_X_BOT_TOKEN="valid-challenge",
            )
        finally:
            bot_protection.reset_cache()
    assert blocked.status_code == 403 and blocked.data["error"]["code"] == "bot_check_failed"
    assert allowed.status_code == 201


# -------------------------------------------------------------------- login
@pytest.mark.django_db
@pytest.mark.parametrize("spelling", ["+998901234567", "998901234567", "901234567"])
def test_login_success_with_any_phone_spelling(make_user, spelling):
    make_user(phone_number="+998901234567")
    res = mobile().post(LOGIN, {"phone_number": spelling, "password": PASSWORD}, format="json")
    assert res.status_code == 200, res.data
    assert {"access", "refresh"} <= set(res.data)
    assert res.data["user"]["phone_number"] == "+998901234567"


@pytest.mark.django_db
def test_login_errors_do_not_reveal_account_existence(make_user):
    make_user(phone_number="+998901234567")
    client = mobile()
    wrong_password = client.post(LOGIN, {"phone_number": "+998901234567", "password": "nope-nope-1"}, format="json")
    unknown_phone = client.post(LOGIN, {"phone_number": "+998907654321", "password": "nope-nope-1"}, format="json")
    garbage_phone = client.post(LOGIN, {"phone_number": "not-a-phone", "password": "nope-nope-1"}, format="json")
    bodies = {json.dumps(r.data, sort_keys=True) for r in (wrong_password, unknown_phone, garbage_phone)}
    assert {r.status_code for r in (wrong_password, unknown_phone, garbage_phone)} == {401}
    assert len(bodies) == 1
    assert wrong_password.data["error"]["code"] == "invalid_credentials"


@pytest.mark.django_db
def test_inactive_user_gets_same_generic_error(make_user):
    make_user(phone_number="+998901234567", is_active=False)
    res = mobile().post(LOGIN, {"phone_number": "+998901234567", "password": PASSWORD}, format="json")
    assert res.status_code == 401
    assert res.data["error"]["code"] == "invalid_credentials"


@pytest.mark.django_db
def test_legacy_account_without_phone_cannot_login_by_email(make_user):
    user = make_user()
    User.objects.filter(pk=user.pk).update(phone_number=None)
    res = mobile().post(LOGIN, {"email": user.email, "password": PASSWORD}, format="json")
    assert res.status_code == 400  # phone_number is required


@pytest.mark.django_db
def test_jwt_refresh_rotation_and_logout(plain_user):
    client = mobile()
    tokens = client.post(LOGIN, {"phone_number": plain_user.phone_number, "password": PASSWORD}, format="json").data
    rotated = client.post(REFRESH, {"refresh": tokens["refresh"]}, format="json")
    assert rotated.status_code == 200 and rotated.data["refresh"] != tokens["refresh"]

    assert client.post(LOGOUT, {"refresh": rotated.data["refresh"]}, format="json").status_code == 204
    assert client.post(REFRESH, {"refresh": rotated.data["refresh"]}, format="json").status_code == 401
    assert AuditLog.objects.filter(action=AuditAction.LOGOUT, target_id=str(plain_user.pk)).exists()


@pytest.mark.django_db
def test_tampered_or_garbage_bearer_rejected(plain_user, client_for):
    client = mobile()
    client.credentials(HTTP_AUTHORIZATION="Bearer not.a.jwt")
    assert client.get(ME).status_code == 401


# ----------------------------------------------------------------- profile
@pytest.mark.django_db
def test_unauthorized_profile_access(anon):
    assert anon.get(ME).status_code == 401
    assert anon.patch(ME, {"first_name": "X"}, format="json").status_code == 401


@pytest.mark.django_db
def test_profile_update_allowed_fields(plain_user, client_for):
    client = client_for(plain_user)
    res = client.patch(ME, {"first_name": "  Malika ", "last_name": "Yusupova", "address": "Samarqand"}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["first_name"] == "Malika" and res.data["address"] == "Samarqand"
    assert AuditLog.objects.filter(action=AuditAction.UPDATE, target_id=str(plain_user.pk)).exists()


@pytest.mark.django_db
def test_profile_picture_upload(plain_user, client_for):
    res = client_for(plain_user).patch(ME, {"profile_picture": image_file()}, format="multipart")
    assert res.status_code == 200, res.data
    assert res.data["profile_picture"].endswith(".webp")


@pytest.mark.django_db
def test_profile_update_cannot_escalate(plain_user, client_for):
    original_phone = plain_user.phone_number
    res = client_for(plain_user).patch(
        ME,
        {
            "role": Role.SUPER_ADMIN,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
            "is_phone_verified": True,
            "phone_number": "+998909999999",
            "admin_permissions": ["users.view"],
            "pinfl": "31201990123456",
        },
        format="json",
    )
    assert res.status_code == 200
    plain_user.refresh_from_db()
    assert plain_user.role == Role.USER and not plain_user.is_staff
    assert not plain_user.is_phone_verified and plain_user.phone_number == original_phone
    assert plain_user.admin_permissions == [] and plain_user.pinfl_last4 != "3456"


@pytest.mark.django_db
def test_user_cannot_reach_other_accounts(plain_user, make_user, client_for):
    other = make_user(Role.USER)
    client = client_for(plain_user)
    assert client.get(f"/api/v1/users/{other.pk}/").status_code == 403
    assert client.patch(f"/api/v1/users/{other.pk}/", {"address": "x"}, format="json").status_code == 403
    assert client.get("/api/v1/users/").status_code == 403
    assert client.get(f"/api/v1/users/{other.pk}/pinfl/").status_code == 403


@pytest.mark.django_db
def test_pinfl_privacy_in_profile_and_register(make_user, client_for):
    user = make_user(pinfl="31201990123456")
    res = client_for(user).get(ME)
    body = json.dumps(res.data)
    assert "31201990123456" not in body
    assert res.data["pinfl_masked"] == "**********3456"
    assert "pinfl" not in res.data

    created = register(phone_number="+998901112233", pinfl="31201990654321")
    assert created.status_code == 201
    assert User.objects.get(phone_number="+998901112233").pinfl_hash is None  # ignored, not stored


# ------------------------------------------------------- panel phone admin
@pytest.mark.django_db
def test_panel_phone_change_revokes_sessions_and_resets_verification(super_admin, plain_user, client_for):
    victim = mobile()
    tokens = victim.post(LOGIN, {"phone_number": plain_user.phone_number, "password": PASSWORD}, format="json").data
    User.objects.filter(pk=plain_user.pk).update(is_phone_verified=True)

    res = client_for(super_admin).patch(
        f"/api/v1/users/{plain_user.pk}/", {"phone_number": "93 555 44 33"}, format="json"
    )
    assert res.status_code == 200, res.data
    assert res.data["phone_number"] == "+998935554433" and res.data["is_phone_verified"] is False

    victim.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert victim.get(ME).status_code == 401


@pytest.mark.django_db
def test_panel_duplicate_phone_rejected(super_admin, plain_user, make_user, client_for):
    other = make_user()
    res = client_for(super_admin).patch(
        f"/api/v1/users/{other.pk}/", {"phone_number": plain_user.phone_number}, format="json"
    )
    assert res.status_code == 400 and "phone_number" in res.data["error"]["details"]


@pytest.mark.django_db
def test_database_enforces_phone_uniqueness(make_user):
    from django.db import IntegrityError, transaction

    make_user(phone_number="+998901234567")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create(phone_number="+998901234567")


@pytest.mark.django_db
def test_set_phone_command(make_user):
    from django.core.management import call_command

    user = make_user()
    User.objects.filter(pk=user.pk).update(phone_number=None)
    call_command("set_phone", user.email, "90 765 43 21")
    user.refresh_from_db()
    assert user.phone_number == "+998907654321"
    res = mobile().post(LOGIN, {"phone_number": "+998907654321", "password": PASSWORD}, format="json")
    assert res.status_code == 200
