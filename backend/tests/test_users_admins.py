import json

from apps.accounts.models import Role, User
from apps.audit.models import AuditAction, AuditLog

from .conftest import image_file, next_phone, next_pinfl

USERS = "/api/v1/users/"
ADMINS = "/api/v1/admins/"


def payload(**extra):
    return {
        "phone_number": extra.pop("phone_number", next_phone()),
        "email": extra.pop("email", f"new{next_pinfl()}@example.uz"),
        "password": "Yangi-Xavfsiz-Parol-1",
        "first_name": "Dilnoza",
        "last_name": "Karimova",
        "pinfl": extra.pop("pinfl", next_pinfl()),
        "address": "Toshkent, Chilonzor",
        **extra,
    }


def test_create_user_masks_pinfl_and_audits(super_admin, client_for):
    data = payload(pinfl="31201990123456")
    res = client_for(super_admin).post(USERS, data, format="json")
    assert res.status_code == 201, res.data
    assert "pinfl" not in res.data and "password" not in res.data
    assert res.data["pinfl_masked"] == "**********3456"
    assert res.data["role"] == Role.USER

    log = AuditLog.objects.get(action=AuditAction.CREATE, target_id=res.data["id"])
    serialized = json.dumps(log.changes)
    assert "31201990123456" not in serialized and "Yangi-Xavfsiz" not in serialized


def test_create_user_validation_errors_have_consistent_shape(super_admin, client_for):
    res = client_for(super_admin).post(USERS, payload(pinfl="12345", password="123"), format="json")
    assert res.status_code == 400
    error = res.data["error"]
    assert error["code"] == "validation_error"
    assert {"pinfl", "password"} <= set(error["details"])


def test_users_endpoint_cannot_create_privileged_roles(super_admin, client_for):
    client = client_for(super_admin)
    for role in (Role.ADMIN, Role.SUPER_ADMIN):
        res = client.post(USERS, payload(role=role), format="json")
        assert res.status_code == 400
        assert "role" in res.data["error"]["details"]


def test_duplicate_email_and_pinfl_rejected(super_admin, client_for, plain_user):
    client = client_for(super_admin)
    res = client.post(USERS, payload(email=plain_user.email.upper()), format="json")
    assert "email" in res.data["error"]["details"]
    res = client.post(USERS, payload(pinfl=plain_user.get_pinfl()), format="json")
    assert "pinfl" in res.data["error"]["details"]


def test_list_search_filter_order_paginate(super_admin, client_for, make_user):
    make_user(Role.USER, first_name="Aziz", is_active=False)
    make_user(Role.STUDIO, first_name="Bobur")
    target = make_user(Role.USER, first_name="Zafar")
    make_user(Role.ADMIN)  # must not appear in /users/
    client = client_for(super_admin)

    res = client.get(USERS, {"page_size": 2})
    assert res.data["count"] == 3 and len(res.data["results"]) == 2 and res.data["total_pages"] == 2
    assert client.get(USERS, {"search": "zafar"}).data["count"] == 1
    assert client.get(USERS, {"is_active": "false"}).data["count"] == 1
    assert client.get(USERS, {"role": "STUDIO"}).data["count"] == 1
    names = [u["first_name"] for u in client.get(USERS, {"ordering": "first_name"}).data["results"]]
    assert names == sorted(names)
    found = client.get(USERS, {"pinfl": target.get_pinfl()}).data
    assert found["count"] == 1 and found["results"][0]["id"] == str(target.pk)


def test_soft_delete_hides_but_keeps_row(super_admin, client_for, plain_user):
    client = client_for(super_admin)
    assert client.delete(f"{USERS}{plain_user.pk}/").status_code == 204
    assert client.get(f"{USERS}{plain_user.pk}/").status_code == 404
    row = User.objects.get(pk=plain_user.pk)
    assert row.deleted_at is not None and row.is_active is False


def test_cannot_delete_or_deactivate_active_studio_owner(super_admin, client_for, studio_user, make_studio):
    make_studio(studio_user)
    client = client_for(super_admin)
    res = client.delete(f"{USERS}{studio_user.pk}/")
    assert res.status_code == 409 and res.data["error"]["code"] == "conflict"
    assert client.patch(f"{USERS}{studio_user.pk}/", {"is_active": False}, format="json").status_code == 409
    studio_user.refresh_from_db()
    assert studio_user.is_active and studio_user.deleted_at is None


def test_pinfl_reveal_is_audited(super_admin, client_for, plain_user):
    res = client_for(super_admin).get(f"{USERS}{plain_user.pk}/pinfl/")
    assert res.status_code == 200
    assert res.data["pinfl"] == plain_user.get_pinfl()
    assert AuditLog.objects.filter(action=AuditAction.PINFL_REVEAL, target_id=str(plain_user.pk)).exists()


def test_profile_picture_upload_is_reencoded(super_admin, client_for):
    data = payload()
    data["profile_picture"] = image_file("me.png")
    res = client_for(super_admin).post(USERS, data, format="multipart")
    assert res.status_code == 201, res.data
    assert res.data["profile_picture"].endswith(".webp")
    assert "me.png" not in res.data["profile_picture"]


def test_non_image_upload_rejected(super_admin, client_for):
    from django.core.files.uploadedfile import SimpleUploadedFile

    data = payload()
    data["profile_picture"] = SimpleUploadedFile("evil.png", b"<script>alert(1)</script>", content_type="image/png")
    res = client_for(super_admin).post(USERS, data, format="multipart")
    assert res.status_code == 400
    assert "profile_picture" in res.data["error"]["details"]


# -------------------------------------------------------------------- admins
def test_create_admin_with_permissions(super_admin, client_for):
    res = client_for(super_admin).post(
        ADMINS, payload(permissions=["users.view", "studios.view", "users.view"]), format="json"
    )
    assert res.status_code == 201, res.data
    assert res.data["role"] == Role.ADMIN
    assert res.data["permissions"] == ["users.view", "studios.view"]


def test_admin_default_permissions_and_invalid_code(super_admin, client_for):
    client = client_for(super_admin)
    res = client.post(ADMINS, payload(), format="json")
    assert res.data["permissions"] == ["dashboard.view"]
    bad = client.post(ADMINS, payload(permissions=["admins.delete"]), format="json")
    assert bad.status_code == 400


def test_admin_role_cannot_be_escalated(super_admin, client_for, admin_user):
    res = client_for(super_admin).patch(f"{ADMINS}{admin_user.pk}/", {"role": Role.SUPER_ADMIN}, format="json")
    assert res.status_code == 200
    admin_user.refresh_from_db()
    assert admin_user.role == Role.ADMIN


def test_permission_change_is_audited(super_admin, client_for, admin_user):
    client_for(super_admin).patch(f"{ADMINS}{admin_user.pk}/", {"permissions": ["users.view"]}, format="json")
    log = AuditLog.objects.get(action=AuditAction.PERMISSIONS_CHANGE)
    assert log.changes == {"from": [], "to": ["users.view"]}


def test_permission_catalog(super_admin, client_for):
    res = client_for(super_admin).get(f"{ADMINS}permissions/")
    assert res.status_code == 200
    assert {"code", "module", "module_label", "label"} <= set(res.data[0])


def test_super_admin_is_never_reachable_through_api(super_admin, client_for):
    client = client_for(super_admin)
    assert client.get(f"{USERS}{super_admin.pk}/").status_code == 404
    assert client.get(f"{ADMINS}{super_admin.pk}/").status_code == 404
    assert client.delete(f"{ADMINS}{super_admin.pk}/").status_code == 404
