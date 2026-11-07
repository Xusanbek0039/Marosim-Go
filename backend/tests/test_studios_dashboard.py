from apps.accounts.models import Role
from apps.studios.models import Studio

from .conftest import image_file

STUDIOS = "/api/v1/studios/"


def test_create_studio_with_logo(super_admin, client_for, studio_user):
    res = client_for(super_admin).post(
        STUDIOS,
        {
            "name": "Nur Studio",
            "address": "Toshkent",
            "responsible_user_id": str(studio_user.pk),
            "profile_picture": image_file("logo.jpg", "JPEG"),
        },
        format="multipart",
    )
    assert res.status_code == 201, res.data
    assert res.data["responsible_user"]["id"] == str(studio_user.pk)
    assert res.data["responsible_user"]["pinfl_masked"].startswith("*")
    assert res.data["profile_picture"].endswith(".webp")


def test_responsible_user_must_be_active_studio_role(super_admin, client_for, plain_user, make_user):
    client = client_for(super_admin)
    inactive_studio = make_user(Role.STUDIO, is_active=False)
    for candidate in (plain_user, inactive_studio):
        res = client.post(
            STUDIOS, {"name": "X", "address": "Y", "responsible_user_id": str(candidate.pk)}, format="json"
        )
        assert res.status_code == 400
        assert "responsible_user_id" in res.data["error"]["details"]


def test_duplicate_studio_name_rejected(super_admin, client_for, studio_user, make_studio):
    make_studio(studio_user, name="Nur Studio")
    res = client_for(super_admin).post(
        STUDIOS, {"name": "  nur   studio ", "address": "Y", "responsible_user_id": str(studio_user.pk)}, format="json"
    )
    assert res.status_code == 400


def test_studio_soft_delete_and_filters(super_admin, client_for, studio_user, make_studio):
    a = make_studio(studio_user, name="Alfa")
    make_studio(studio_user, name="Beta", is_active=False)
    client = client_for(super_admin)
    assert client.get(STUDIOS, {"is_active": "true"}).data["count"] == 1
    assert client.get(STUDIOS, {"search": "bet"}).data["count"] == 1
    assert client.delete(f"{STUDIOS}{a.pk}/").status_code == 204
    assert client.get(STUDIOS).data["count"] == 1
    assert Studio.objects.filter(pk=a.pk).exists()


def test_dashboard_overview_counts(super_admin, client_for, make_user, make_studio):
    owner = make_user(Role.STUDIO)
    make_user(Role.USER)
    make_user(Role.USER, is_active=False)
    make_user(Role.ADMIN)
    make_studio(owner)

    data = client_for(super_admin).get("/api/v1/dashboard/overview/").data
    totals = data["totals"]
    assert totals["users"] == 3 and totals["active_users"] == 2 and totals["inactive_users"] == 1
    assert totals["admins"] == 1 and totals["studios"] == 1
    assert len(data["recent_profiles"]) == 4
    assert all("pinfl" not in p for p in data["recent_profiles"])


def test_dashboard_hides_profiles_without_users_view(make_user, client_for):
    make_user(Role.USER)
    admin = make_user(Role.ADMIN, admin_permissions=["dashboard.view"])
    data = client_for(admin).get("/api/v1/dashboard/overview/").data
    assert data["recent_profiles"] == []
    assert data["totals"]["users"] == 1
