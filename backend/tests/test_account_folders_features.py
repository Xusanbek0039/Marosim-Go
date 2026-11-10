"""User request 2026-11-10: "Mening marosimlarim" as renamable folders (own wedding + shared with me),
managed by admins too; per-account capability switches; 1 GB Drive portfolio space per studio."""

import pytest

from apps.accounts.models import Role
from apps.ceremonies.models import CeremonyFolder
from apps.studios import portfolio_storage
from apps.studios.models import PortfolioStorage, StudioImage
from apps.studios.services import sync_owner_membership
from apps.storage.google import MediaStream

from .conftest import image_file
from .test_ceremony_invitations import INV, MY, answer, owner_invite, wedding, world  # noqa: F401

USERS = "/api/v1/users/"


def admin_with(make_user, *codes):
    return make_user(Role.ADMIN, admin_permissions=list(codes))


@pytest.fixture
def shared(wedding):
    """The bride owns the wedding and shares it with the guest (viewer)."""
    guest = wedding["users"]["guest"]
    assert owner_invite(wedding["c"]["bride"], wedding["ceremony"], guest.phone_number).status_code == 201
    assert answer(wedding["c"]["guest"]).status_code == 200
    return wedding


# ------------------------------------------------------------------- folders
@pytest.mark.django_db
def test_user_folders_are_personal(shared):
    """Ownership: a folder name belongs to one account; others (and the studio) keep the title."""
    c, bride, guest = shared["ceremony"], shared["c"]["bride"], shared["c"]["guest"]

    mine = bride.get(MY).data["results"]
    assert [(r["folder_name"], r["access_role"]) for r in mine] == [("Dilnoza & Jasur", "OWNER")]
    assert guest.get(MY).data["results"][0]["access_role"] == "VIEWER"

    res = bride.patch(f"{MY}{c.pk}/folder/", {"name": "  Bizning   to'yimiz "}, format="json")
    assert res.status_code == 200 and res.data == {"folder_name": "Bizning to'yimiz", "is_custom": True}
    assert bride.get(f"{MY}{c.pk}/").data["folder_name"] == "Bizning to'yimiz"
    assert guest.get(MY).data["results"][0]["folder_name"] == "Dilnoza & Jasur"
    assert shared["studio"].get(f"/api/v1/ceremonies/{c.pk}/").data["title"] == "Dilnoza & Jasur"

    assert guest.patch(f"{MY}{c.pk}/folder/", {"name": "Do'stimning to'yi"}, format="json").status_code == 200
    assert shared["c"]["stranger"].patch(f"{MY}{c.pk}/folder/", {"name": "x"}, format="json").status_code == 404
    assert bride.patch(f"{MY}{shared['other'].pk}/folder/", {"name": "x"}, format="json").status_code == 404

    res = bride.patch(f"{MY}{c.pk}/folder/", {"name": ""}, format="json")
    assert res.data == {"folder_name": "Dilnoza & Jasur", "is_custom": False}
    assert list(CeremonyFolder.objects.values_list("name", flat=True)) == ["Do'stimning to'yi"]


@pytest.mark.django_db
def test_admin_manages_user_folders(make_user, client_for, shared):
    """Ownership: admins see / rename only ceremonies that account can open; rights come from codes."""
    bride = shared["users"]["bride"]
    c = shared["ceremony"]
    url = f"{USERS}{bride.pk}/folders/"

    assert client_for(admin_with(make_user, "dashboard.view")).get(url).status_code == 403
    viewer = client_for(admin_with(make_user, "users.view"))
    rows = viewer.get(url).data
    assert [(r["id"], r["access_role"], r["is_custom"]) for r in rows] == [(str(c.pk), "OWNER", False)]
    assert viewer.patch(f"{url}{c.pk}/", {"name": "x"}, format="json").status_code == 403

    editor = client_for(admin_with(make_user, "users.view", "users.update"))
    res = editor.patch(f"{url}{c.pk}/", {"name": "Admin nomladi"}, format="json")
    assert res.status_code == 200 and res.data["folder_name"] == "Admin nomladi"
    assert shared["c"]["bride"].get(MY).data["results"][0]["folder_name"] == "Admin nomladi"
    assert editor.patch(f"{url}{shared['other'].pk}/", {"name": "x"}, format="json").status_code == 404
    studio_owner = shared["ceremony"].studio.responsible_user
    assert editor.get(f"{USERS}{studio_owner.pk}/folders/").data == []


# ------------------------------------------------------- account features
@pytest.mark.django_db
def test_capabilities_per_account(make_user, client_for, shared):
    bride, guest = shared["users"]["bride"], shared["users"]["guest"]
    url = f"{USERS}{bride.pk}/features/"

    viewer = client_for(admin_with(make_user, "platform.view"))
    rows = viewer.get(url).data
    assert {r["code"] for r in rows} >= {"USER.ceremonies", "USER.sharing"} and all(r["enabled"] for r in rows)
    assert viewer.patch(url, {"disabled_features": ["USER.ceremonies"]}, format="json").status_code == 403

    manager = client_for(admin_with(make_user, "platform.view", "platform.manage"))
    assert manager.patch(url, {"disabled_features": ["STUDIO.portfolio"]}, format="json").status_code == 400
    res = manager.patch(url, {"disabled_features": ["USER.ceremonies"]}, format="json")
    assert res.status_code == 200
    assert {r["code"]: r["enabled"] for r in res.data}["USER.ceremonies"] is False

    assert shared["c"]["bride"].get(MY).status_code == 403  # only this account
    assert shared["c"]["guest"].get(MY).status_code == 200
    assert client_for(guest).get(f"{USERS}{bride.pk}/features/").status_code == 403

    manager.patch(url, {"disabled_features": []}, format="json")
    assert shared["c"]["bride"].get(MY).status_code == 200


# ------------------------------------------------------------ studio space
@pytest.fixture
def studio(make_user, make_studio):
    s = make_studio(make_user(Role.STUDIO))
    sync_owner_membership(s)
    return s


@pytest.mark.django_db
def test_portfolio_quota(make_user, client_for, studio, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    owner = client_for(studio.responsible_user)
    url = f"/api/v1/studios/me/{studio.pk}/"

    usage = owner.get(f"{url}storage/").data
    assert usage["quota_bytes"] == 1024 * 1024 * 1024 and usage["used_bytes"] == 0 and usage["storage"] == "LOCAL"
    res = owner.post(f"{url}images/", {"image": image_file()}, format="multipart")
    assert res.status_code == 201 and res.data["size_bytes"] > 0
    assert owner.get(f"{url}storage/").data["used_bytes"] == res.data["size_bytes"]

    studio.portfolio_quota_mb = 0
    studio.save()
    res = owner.post(f"{url}images/", {"image": image_file()}, format="multipart")
    assert res.status_code == 400 and "joyi yetmaydi" in str(res.data)

    other = make_user(Role.STUDIO)
    assert client_for(other).get(f"{url}storage/").status_code == 404
    editor = client_for(admin_with(make_user, "studios.view", "studios.update"))
    res = editor.patch(f"/api/v1/studios/{studio.pk}/", {"portfolio_quota_mb": 2048}, format="json")
    assert res.status_code == 200 and res.data["portfolio_quota_mb"] == 2048 and res.data["portfolio_used_bytes"] > 0


@pytest.mark.django_db
def test_portfolio_goes_to_drive(client_for, anon, studio, monkeypatch, settings, django_capture_on_commit_callbacks):
    settings.STUDIO_PORTFOLIO_STORAGE = "drive"
    blobs, trashed = {}, []

    def upload(st, files):
        ids = []
        for content, _mime in files:
            content.seek(0)
            fid = f"drive-{len(blobs)}"
            blobs[fid] = content.read()
            ids.append(fid)
        return ids

    monkeypatch.setattr(portfolio_storage, "upload_to_drive", upload)
    monkeypatch.setattr(portfolio_storage, "trash", lambda ids: trashed.extend(i for i in ids if i))
    monkeypatch.setattr(
        portfolio_storage,
        "open_stream",
        lambda fid, rng: MediaStream(200, {"Content-Length": str(len(blobs[fid]))}, iter([blobs[fid]]), lambda: None),
    )

    owner = client_for(studio.responsible_user)
    res = owner.post(f"/api/v1/studios/me/{studio.pk}/images/", {"image": image_file()}, format="multipart")
    assert res.status_code == 201
    item = StudioImage.objects.get()
    assert item.storage == PortfolioStorage.DRIVE and item.drive_file_id == "drive-0" and not item.image
    assert res.data["image"].endswith(f"/public/studios/{studio.pk}/portfolio/{item.pk}/file/main/")

    got = anon.get(res.data["image"])
    assert got.status_code == 200 and b"".join(got.streaming_content) == blobs["drive-0"]
    assert anon.get(res.data["image"].replace("/main/", "/poster/")).status_code == 404

    with django_capture_on_commit_callbacks(execute=True):
        assert owner.delete(f"/api/v1/studios/me/{studio.pk}/images/{item.pk}/").status_code == 204
    assert trashed == ["drive-0"]
