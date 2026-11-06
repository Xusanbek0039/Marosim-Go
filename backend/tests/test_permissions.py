"""Server-side RBAC matrix: every management endpoint against every role."""

import pytest

from apps.accounts.models import Role
from apps.accounts.permissions_catalog import ALL_CODES

LIST_ENDPOINTS = {
    "/api/v1/users/": "users.view",
    "/api/v1/studios/": "studios.view",
    "/api/v1/dashboard/overview/": "dashboard.view",
}


@pytest.mark.parametrize("url", [*LIST_ENDPOINTS, "/api/v1/admins/", "/api/v1/admins/permissions/"])
def test_anonymous_gets_401(anon, url, db):
    assert anon.get(url).status_code == 401


@pytest.mark.parametrize("role", [Role.USER, Role.STUDIO])
@pytest.mark.parametrize("url", [*LIST_ENDPOINTS, "/api/v1/admins/"])
def test_client_roles_get_403(make_user, client_for, role, url):
    res = client_for(make_user(role)).get(url)
    assert res.status_code == 403
    assert res.data["error"]["code"] == "permission_denied"


@pytest.mark.parametrize("url", [*LIST_ENDPOINTS, "/api/v1/admins/"])
def test_super_admin_has_access(super_admin, client_for, url):
    assert client_for(super_admin).get(url).status_code == 200


@pytest.mark.parametrize("url,code", list(LIST_ENDPOINTS.items()))
def test_admin_needs_the_matching_permission(make_user, client_for, url, code):
    without = make_user(Role.ADMIN, admin_permissions=[c for c in ALL_CODES if c != code])
    with_it = make_user(Role.ADMIN, admin_permissions=[code])
    assert client_for(without).get(url).status_code == 403
    assert client_for(with_it).get(url).status_code == 200


def test_admin_can_never_manage_admins(make_user, client_for):
    admin = make_user(Role.ADMIN, admin_permissions=list(ALL_CODES))
    client = client_for(admin)
    assert client.get("/api/v1/admins/").status_code == 403
    assert client.get("/api/v1/admins/permissions/").status_code == 403
    assert client.patch(f"/api/v1/admins/{admin.pk}/", {"permissions": []}, format="json").status_code == 403


def test_admin_action_level_permissions(make_user, client_for, plain_user):
    viewer = client_for(make_user(Role.ADMIN, admin_permissions=["users.view"]))
    url = f"/api/v1/users/{plain_user.pk}/"
    assert viewer.get(url).status_code == 200
    assert viewer.patch(url, {"address": "x"}, format="json").status_code == 403
    assert viewer.delete(url).status_code == 403
    assert viewer.get(f"{url}pinfl/").status_code == 403

    editor = client_for(make_user(Role.ADMIN, admin_permissions=["users.view", "users.update"]))
    assert editor.patch(url, {"address": "x"}, format="json").status_code == 200


def test_inactive_admin_loses_access(make_user, client_for):
    admin = make_user(Role.ADMIN, admin_permissions=list(ALL_CODES))
    client = client_for(admin)
    admin.is_active = False
    admin.save()
    assert client.get("/api/v1/users/").status_code == 401


def test_permission_change_applies_immediately(super_admin, make_user, client_for):
    admin = make_user(Role.ADMIN, admin_permissions=["users.view"])
    admin_client = client_for(admin)
    assert admin_client.get("/api/v1/studios/").status_code == 403

    res = client_for(super_admin).patch(
        f"/api/v1/admins/{admin.pk}/", {"permissions": ["users.view", "studios.view"]}, format="json"
    )
    assert res.status_code == 200
    assert admin_client.get("/api/v1/studios/").status_code == 200
