"""Panel management of venues (``/api/v1/admin/venues/``) and venue gallery images (owner + panel).

User decisions 2026-11-07: Super Admin grants / revokes venue rights to admins; venues sit next to
Users / Admins / Studios in the panel; up to 20 gallery images of 5 MB each.
"""

import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import Role
from apps.audit.models import AuditAction, AuditLog
from apps.venues.models import MembershipRole, PublicationStatus, Venue, VenueImage, VenueMembership

from .conftest import image_file
from .test_venues import BASE as OWNER_BASE
from .test_venues import VENUE_DATA, make_venue, venue_owner  # noqa: F401 - fixtures

ADMIN = "/api/v1/admin/venues/"


def admin_with(make_user, *codes):
    return make_user(Role.ADMIN, admin_permissions=list(codes))


def gallery_upload(client, url, **kw):
    return client.post(url, {"image": image_file(**kw)}, format="multipart")


# ------------------------------------------------------------- permissions
@pytest.mark.django_db
def test_admin_venue_rights_come_only_from_granted_codes(make_user, client_for, super_admin, venue_owner, make_venue):
    venue = make_venue(venue_owner)
    nobody = client_for(admin_with(make_user))
    assert nobody.get(ADMIN).status_code == 403

    viewer = client_for(admin_with(make_user, "venues.view"))
    assert viewer.get(ADMIN).data["count"] == 1
    assert viewer.get(f"{ADMIN}{venue.pk}/").status_code == 200
    assert viewer.patch(f"{ADMIN}{venue.pk}/", {"name": "X"}, format="json").status_code == 403
    assert viewer.post(ADMIN, {**VENUE_DATA, "owner_id": str(venue_owner.pk)}, format="json").status_code == 403
    assert viewer.delete(f"{ADMIN}{venue.pk}/").status_code == 403

    assert client_for(super_admin).get(ADMIN).status_code == 200


@pytest.mark.django_db
def test_revoked_permission_stops_working_on_the_next_request(make_user, client_for, venue_owner, make_venue):
    make_venue(venue_owner)
    admin = admin_with(make_user, "venues.view")
    client = client_for(admin)
    assert client.get(ADMIN).status_code == 200
    admin.admin_permissions = []
    admin.save(update_fields=["admin_permissions"])
    assert client.get(ADMIN).status_code == 403


@pytest.mark.django_db
def test_super_admin_grants_venue_codes_and_catalog_lists_them(make_user, client_for, super_admin):
    catalog = {p["code"] for p in client_for(super_admin).get("/api/v1/admins/permissions/").data}
    assert {"venues.view", "venues.create", "venues.update", "venues.delete", "venues.publish"} <= catalog
    admin = admin_with(make_user)
    res = client_for(super_admin).patch(
        f"/api/v1/admins/{admin.pk}/", {"permissions": ["venues.view", "venues.update"]}, format="json"
    )
    assert res.status_code == 200, res.data
    admin.refresh_from_db()
    assert client_for(admin).get(ADMIN).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.USER, Role.STUDIO, Role.VENUE_OWNER])
def test_non_panel_roles_cannot_use_admin_venue_api(make_user, client_for, role):
    assert client_for(make_user(role)).get(ADMIN).status_code == 403


# ----------------------------------------------------------------- CRUD
@pytest.mark.django_db
def test_admin_creates_venue_for_a_venue_owner(make_user, client_for, venue_owner):
    client = client_for(admin_with(make_user, "venues.create", "venues.view"))
    res = client.post(ADMIN, {**VENUE_DATA, "owner_id": str(venue_owner.pk)}, format="json")
    assert res.status_code == 201, res.data
    venue = Venue.objects.get(pk=res.data["id"])
    assert venue.publication_status == PublicationStatus.PRIVATE
    assert VenueMembership.objects.get(venue=venue).user == venue_owner
    assert [m["role"] for m in res.data["members"]] == [MembershipRole.OWNER]
    assert [h["name"] for h in res.data["halls"]] == ["Asosiy zal"]

    # owner_id must be an active VENUE_OWNER account
    for bad in (make_user(Role.USER), make_user(Role.STUDIO)):
        res = client.post(ADMIN, {**VENUE_DATA, "owner_id": str(bad.pk)}, format="json")
        assert res.status_code == 400 and "owner_id" in res.data["error"]["details"]
    assert client.post(ADMIN, VENUE_DATA, format="json").status_code == 400


@pytest.mark.django_db
def test_publication_status_needs_publish_right(make_user, client_for, venue_owner, make_venue):
    venue = make_venue(venue_owner)
    editor = client_for(admin_with(make_user, "venues.view", "venues.update"))
    assert editor.patch(f"{ADMIN}{venue.pk}/", {"publication_status": "APPROVED"}, format="json").status_code == 403
    assert editor.patch(f"{ADMIN}{venue.pk}/", {"is_active": False}, format="json").status_code == 200
    venue.refresh_from_db()
    assert venue.is_active is False and venue.publication_status == PublicationStatus.PRIVATE
    assert AuditLog.objects.filter(action=AuditAction.DEACTIVATE, target_id=str(venue.pk)).exists()

    publisher = client_for(admin_with(make_user, "venues.view", "venues.update", "venues.publish"))
    res = publisher.patch(f"{ADMIN}{venue.pk}/", {"publication_status": "APPROVED"}, format="json")
    assert res.status_code == 200 and res.data["publication_status"] == "APPROVED"


@pytest.mark.django_db
def test_admin_manages_halls_and_soft_deletes(make_user, client_for, venue_owner, make_venue):
    venue = make_venue(venue_owner)
    client = client_for(admin_with(make_user, "venues.view", "venues.update", "venues.delete"))
    res = client.post(f"{ADMIN}{venue.pk}/halls/", {"name": "Oq zal", "capacity": 200}, format="json")
    assert res.status_code == 201
    hall_id = res.data["id"]
    assert (
        client.patch(f"{ADMIN}{venue.pk}/halls/{hall_id}/", {"is_active": False}, format="json").data["is_active"]
        is False
    )
    assert client.delete(f"{ADMIN}{venue.pk}/").status_code == 204
    assert client.get(f"{ADMIN}{venue.pk}/").status_code == 404
    assert client_for(venue_owner).get(OWNER_BASE).data["count"] == 0


# --------------------------------------------------------------- gallery
@pytest.mark.django_db
def test_owner_uploads_gallery_images_reencoded_and_limited_to_20(
    venue_owner, make_venue, client_for, django_capture_on_commit_callbacks
):
    venue = make_venue(venue_owner)
    url = f"{OWNER_BASE}{venue.pk}/images/"
    client = client_for(venue_owner)
    res = gallery_upload(client, url, size=(2600, 1300))
    assert res.status_code == 201, res.data
    image = VenueImage.objects.get(pk=res.data["id"])
    assert image.image.name.endswith(".webp")
    from PIL import Image

    with Image.open(image.image.path) as im:
        assert max(im.size) == 1920  # gallery keeps more detail than avatars (1024)

    for _ in range(19):
        assert gallery_upload(client, url).status_code == 201
    res = gallery_upload(client, url)
    assert res.status_code == 400 and "20" in str(res.data["error"]["details"]["image"])
    detail = client.get(f"{OWNER_BASE}{venue.pk}/").data
    assert len(detail["images"]) == 20 and [i["position"] for i in detail["images"]] == list(range(20))

    first = detail["images"][0]["id"]
    path = VenueImage.objects.get(pk=first).image.path
    with django_capture_on_commit_callbacks(execute=True):  # the file is removed after commit
        assert client.delete(f"{url}{first}/").status_code == 204
    assert not VenueImage.objects.filter(pk=first).exists()
    assert gallery_upload(client, url).status_code == 201
    assert not os.path.exists(path)


@pytest.mark.django_db
def test_gallery_rejects_big_and_non_image_files(venue_owner, make_venue, client_for):
    venue = make_venue(venue_owner)
    url = f"{OWNER_BASE}{venue.pk}/images/"
    client = client_for(venue_owner)
    big = SimpleUploadedFile("big.jpg", b"\xff\xd8" + b"0" * (5 * 1024 * 1024 + 10), content_type="image/jpeg")
    assert client.post(url, {"image": big}, format="multipart").status_code == 400
    fake = SimpleUploadedFile("x.png", b"<script>alert(1)</script>", content_type="image/png")
    assert client.post(url, {"image": fake}, format="multipart").status_code == 400
    assert VenueImage.objects.count() == 0


@pytest.mark.django_db
def test_gallery_rights_follow_membership(make_user, make_venue, venue_owner, client_for):
    venue = make_venue(venue_owner)
    url = f"{OWNER_BASE}{venue.pk}/images/"
    manager, viewer, stranger = (make_user(Role.VENUE_OWNER) for _ in range(3))
    VenueMembership.objects.create(venue=venue, user=manager, role=MembershipRole.MANAGER)
    VenueMembership.objects.create(venue=venue, user=viewer, role=MembershipRole.VIEWER)
    assert gallery_upload(client_for(manager), url).status_code == 201
    assert gallery_upload(client_for(viewer), url).status_code == 403
    assert client_for(viewer).get(url).status_code == 200
    assert gallery_upload(client_for(stranger), url).status_code == 404
    image = VenueImage.objects.get()
    assert client_for(viewer).delete(f"{url}{image.pk}/").status_code == 403
    assert client_for(stranger).delete(f"{url}{image.pk}/").status_code == 404
    # a venue cannot be deleted through the owner API even though DELETE is allowed for images
    assert client_for(venue_owner).delete(f"{OWNER_BASE}{venue.pk}/").status_code == 405


@pytest.mark.django_db
def test_admin_gallery_needs_update_right(make_user, client_for, venue_owner, make_venue):
    venue = make_venue(venue_owner)
    url = f"{ADMIN}{venue.pk}/images/"
    assert gallery_upload(client_for(admin_with(make_user, "venues.view")), url).status_code == 403
    editor = client_for(admin_with(make_user, "venues.view", "venues.update"))
    res = gallery_upload(editor, url)
    assert res.status_code == 201
    assert editor.delete(f"{url}{res.data['id']}/").status_code == 204
