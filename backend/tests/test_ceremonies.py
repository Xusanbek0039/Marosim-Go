import json

import pytest
from django.test import override_settings

from apps.accounts.models import Role
from apps.audit.models import AuditAction, AuditLog
from apps.ceremonies.models import AccessStatus, Ceremony, CeremonyParticipant, CeremonyStatus
from apps.studios.models import StudioMembership
from apps.studios.services import sync_owner_membership

CEREMONIES = "/api/v1/ceremonies/"
STUDIO_ME = "/api/v1/studios/me/"
STUDIO_ME_CEREMONIES = "/api/v1/studios/me/ceremonies/"
MY_CEREMONIES = "/api/v1/me/ceremonies/"
INVITATIONS = "/api/v1/me/invitations/"


def detail(c):
    return f"{CEREMONIES}{c.pk}/"


def participants_url(c):
    return f"{CEREMONIES}{c.pk}/participants/"


@pytest.fixture
def studio_world(make_user, make_studio):
    """Two studios with their owners, plus an UPLOADER in studio A."""
    owner_a, owner_b = make_user(Role.STUDIO), make_user(Role.STUDIO)
    studio_a, studio_b = make_studio(owner_a, name="Nur Studio"), make_studio(owner_b, name="Lola Studio")
    sync_owner_membership(studio_a)
    sync_owner_membership(studio_b)
    uploader = make_user(Role.STUDIO)
    StudioMembership.objects.create(studio=studio_a, user=uploader, role=StudioMembership.Role.UPLOADER)
    return {"owner_a": owner_a, "owner_b": owner_b, "studio_a": studio_a, "studio_b": studio_b, "uploader": uploader}


def make_ceremony(studio, **extra):
    return Ceremony.objects.create(
        studio=studio, title=extra.pop("title", "To'y"), event_date=extra.pop("event_date", "2026-09-12"), **extra
    )


def invite(client, ceremony, phone, kind="BRIDE"):
    return client.post(participants_url(ceremony), {"phone_number": phone, "participant_type": kind}, format="json")


# ---------------------------------------------------------------- studios/me
@pytest.mark.django_db
def test_studio_me_lists_own_memberships_only(studio_world, client_for):
    res = client_for(studio_world["owner_a"]).get(STUDIO_ME)
    assert res.status_code == 200
    assert [m["studio"]["name"] for m in res.data] == ["Nur Studio"]
    assert res.data[0]["role"] == "OWNER" and res.data[0]["can_manage"] is True
    body = json.dumps(res.data, default=str)
    assert "pinfl" not in body and "responsible_user" not in body


@pytest.mark.django_db
def test_studio_without_membership_sees_nothing(make_user, client_for, studio_world):
    loner = make_user(Role.STUDIO)
    client = client_for(loner)
    assert client.get(STUDIO_ME).data == []
    make_ceremony(studio_world["studio_a"])
    assert client.get(STUDIO_ME_CEREMONIES).data["count"] == 0
    assert client.post(CEREMONIES, {"title": "X", "event_date": "2026-10-01"}, format="json").status_code == 400


@pytest.mark.django_db
def test_owner_change_moves_membership(super_admin, client_for, studio_world, make_user):
    new_owner = make_user(Role.STUDIO)
    studio = studio_world["studio_a"]
    res = client_for(super_admin).patch(f"/api/v1/studios/{studio.pk}/", {"responsible_user_id": str(new_owner.pk)})
    assert res.status_code == 200, res.data
    assert StudioMembership.objects.get(studio=studio, user=new_owner).role == "OWNER"
    old = StudioMembership.objects.get(studio=studio, user=studio_world["owner_a"])
    assert old.is_active is False
    assert client_for(studio_world["owner_a"]).get(STUDIO_ME).data == []


# --------------------------------------------------------------- ceremonies
@pytest.mark.django_db
def test_studio_creates_ceremony_in_its_studio(studio_world, client_for):
    res = client_for(studio_world["owner_a"]).post(
        CEREMONIES, {"title": "  Dilnoza  &  Jasur ", "event_date": "2026-09-12"}, format="json"
    )
    assert res.status_code == 201, res.data
    assert res.data["title"] == "Dilnoza & Jasur" and res.data["status"] == "DRAFT"
    assert res.data["studio"]["id"] == str(studio_world["studio_a"].pk)
    assert "drive_folder_id" not in res.data
    c = Ceremony.objects.get(pk=res.data["id"])
    assert c.created_by == studio_world["owner_a"]
    assert AuditLog.objects.filter(action=AuditAction.CREATE, target_id=str(c.pk)).exists()


@pytest.mark.django_db
def test_studio_cannot_create_in_foreign_studio(studio_world, client_for):
    res = client_for(studio_world["owner_a"]).post(
        CEREMONIES,
        {"title": "X", "event_date": "2026-09-12", "studio_id": str(studio_world["studio_b"].pk)},
        format="json",
    )
    assert res.status_code == 400 and "studio_id" in res.data["error"]["details"]
    assert not Ceremony.objects.exists()


@pytest.mark.django_db
def test_super_admin_must_pick_studio(super_admin, client_for, studio_world):
    client = client_for(super_admin)
    assert client.post(CEREMONIES, {"title": "X", "event_date": "2026-09-12"}, format="json").status_code == 400
    res = client.post(
        CEREMONIES,
        {"title": "X", "event_date": "2026-09-12", "studio_id": str(studio_world["studio_b"].pk)},
        format="json",
    )
    assert res.status_code == 201


@pytest.mark.django_db
def test_ceremony_scope_is_own_studio(studio_world, client_for, super_admin):
    """Ownership: a studio sees and edits only its own ceremonies; others are 404."""
    mine, theirs = make_ceremony(studio_world["studio_a"]), make_ceremony(studio_world["studio_b"])
    client = client_for(studio_world["owner_a"])
    ids = {c["id"] for c in client.get(CEREMONIES).data["results"]}
    assert ids == {str(mine.pk)}
    assert {c["id"] for c in client.get(STUDIO_ME_CEREMONIES).data["results"]} == {str(mine.pk)}
    assert client.get(detail(theirs)).status_code == 404
    assert client.patch(detail(theirs), {"title": "hijack"}, format="json").status_code == 404
    assert client.get(participants_url(theirs)).status_code == 404
    assert invite(client, theirs, "+998901112233").status_code == 404
    assert client.get(detail(mine)).status_code == 200
    # super admin sees both
    assert client_for(super_admin).get(CEREMONIES).data["count"] == 2


@pytest.mark.django_db
def test_uploader_can_view_but_not_manage(studio_world, client_for):
    c = make_ceremony(studio_world["studio_a"])
    client = client_for(studio_world["uploader"])
    assert client.get(detail(c)).status_code == 200
    assert client.get(detail(c)).data["can_manage"] is False
    assert client.patch(detail(c), {"title": "new"}, format="json").status_code == 403
    assert invite(client, c, "+998901112233").status_code == 403
    assert client.post(CEREMONIES, {"title": "X", "event_date": "2026-09-12"}, format="json").status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.ADMIN, Role.USER])
def test_admin_and_user_cannot_use_studio_endpoints(role, make_user, client_for):
    client = client_for(make_user(role, admin_permissions=["dashboard.view", "studios.view"]) if role == Role.ADMIN else make_user(role))
    for url in (CEREMONIES, STUDIO_ME, STUDIO_ME_CEREMONIES):
        assert client.get(url).status_code == 403


@pytest.mark.django_db
def test_status_transitions(studio_world, client_for, super_admin):
    c = make_ceremony(studio_world["studio_a"])
    client = client_for(studio_world["owner_a"])
    assert client.patch(detail(c), {"status": "READY"}, format="json").data["status"] == "READY"
    bad = client.patch(detail(c), {"status": "PROCESSING"}, format="json")
    assert bad.status_code == 400 and "status" in bad.data["error"]["details"]
    assert client.patch(detail(c), {"status": "ARCHIVED"}, format="json").status_code == 200
    # the media pipeline statuses are system-only for studios, but super admin may fix them
    assert client_for(super_admin).patch(detail(c), {"status": "PROCESSING"}, format="json").status_code == 200


@pytest.mark.django_db
def test_studio_cannot_move_ceremony_or_write_drive_fields(studio_world, client_for):
    c = make_ceremony(studio_world["studio_a"])
    res = client_for(studio_world["owner_a"]).patch(
        detail(c), {"studio_id": str(studio_world["studio_b"].pk), "drive_folder_id": "evil"}, format="json"
    )
    assert res.status_code == 200
    c.refresh_from_db()
    assert c.studio == studio_world["studio_a"] and c.drive_folder_id == ""


# -------------------------------------------------------------- participants
@pytest.mark.django_db
def test_invite_response_does_not_reveal_account_existence(studio_world, client_for, make_user):
    make_user(Role.USER, phone_number="+998901112233", first_name="Dilnoza")
    c = make_ceremony(studio_world["studio_a"])
    client = client_for(studio_world["owner_a"])
    known = invite(client, c, "90 111 22 33", "BRIDE")
    unknown = invite(client, c, "+998907776655", "GROOM")
    assert known.status_code == unknown.status_code == 201
    strip = lambda d: {k: v for k, v in d.items() if k not in ("id", "phone_number", "participant_type", "invited_at")}  # noqa: E731
    assert strip(known.data) == strip(unknown.data)
    assert known.data["display_name"] is None and known.data["access_status"] == "INVITED"
    assert known.data["phone_number"] == "+998901112233"
    assert "Dilnoza" not in json.dumps(client.get(participants_url(c)).data)


@pytest.mark.django_db
def test_duplicate_invite_and_second_bride_rejected(studio_world, client_for):
    c = make_ceremony(studio_world["studio_a"])
    client = client_for(studio_world["owner_a"])
    assert invite(client, c, "+998901112233", "BRIDE").status_code == 201
    dup = invite(client, c, "901112233", "OTHER")
    assert dup.status_code == 400 and "phone_number" in dup.data["error"]["details"]
    second = invite(client, c, "+998907776655", "BRIDE")
    assert second.status_code == 400 and "participant_type" in second.data["error"]["details"]
    assert invite(client, c, "+998907776655", "GROOM").status_code == 201
    assert invite(client, c, "+998935554433", "OTHER").status_code == 201


@pytest.mark.django_db
def test_invalid_phone_rejected(studio_world, client_for):
    c = make_ceremony(studio_world["studio_a"])
    res = invite(client_for(studio_world["owner_a"]), c, "12345")
    assert res.status_code == 400 and "phone_number" in res.data["error"]["details"]


# -------------------------------------------------------------- couple side
@pytest.fixture
def couple(studio_world, make_user, client_for):
    bride = make_user(Role.USER, phone_number="+998901112233", first_name="Dilnoza")
    groom = make_user(Role.USER, phone_number="+998907776655", first_name="Jasur")
    c = make_ceremony(studio_world["studio_a"], title="Dilnoza & Jasur", status=CeremonyStatus.READY)
    studio = client_for(studio_world["owner_a"])
    invite(studio, c, bride.phone_number, "BRIDE")
    invite(studio, c, groom.phone_number, "GROOM")
    return {"bride": bride, "groom": groom, "ceremony": c, "studio": studio}


@pytest.mark.django_db
def test_invitation_flow_bride_and_groom(couple, client_for):
    bride = client_for(couple["bride"])
    assert bride.get(MY_CEREMONIES).data["count"] == 0  # not visible before accepting
    invitations = bride.get(INVITATIONS).data
    assert len(invitations) == 1 and invitations[0]["participant_type"] == "BRIDE"
    assert invitations[0]["ceremony_title"] == "Dilnoza & Jasur" and "phone_number" not in invitations[0]

    res = bride.post(f"{INVITATIONS}{invitations[0]['id']}/accept/")
    assert res.status_code == 200, res.data
    assert res.data["my_role"] == "BRIDE"
    mine = bride.get(MY_CEREMONIES).data
    assert mine["count"] == 1 and mine["results"][0]["id"] == str(couple["ceremony"].pk)

    groom = client_for(couple["groom"])
    groom.post(f"{INVITATIONS}{groom.get(INVITATIONS).data[0]['id']}/accept/")
    detail_res = groom.get(f"{MY_CEREMONIES}{couple['ceremony'].pk}/")
    assert {p["participant_type"] for p in detail_res.data["participants"]} == {"BRIDE", "GROOM"}
    body = json.dumps(detail_res.data, default=str)
    assert "+99890" not in body and "drive_folder_id" not in body

    names = {p["display_name"] for p in couple["studio"].get(participants_url(couple["ceremony"])).data}
    assert {"Dilnoza Familiya1", "Jasur Familiya2"} <= names or {"Dilnoza", "Jasur"} <= {
        (n or "").split()[0] for n in names
    }
    assert AuditLog.objects.filter(action=AuditAction.PARTICIPANT_ACCEPT).count() == 2


@pytest.mark.django_db
def test_user_ceremony_scope_is_own_participation(couple, client_for, make_user, studio_world):
    """Ownership: a user sees only ceremonies where they are an ACTIVE participant."""
    bride = client_for(couple["bride"])
    bride.post(f"{INVITATIONS}{bride.get(INVITATIONS).data[0]['id']}/accept/")
    other = make_ceremony(studio_world["studio_b"], status=CeremonyStatus.READY)
    stranger = client_for(make_user(Role.USER))
    assert stranger.get(MY_CEREMONIES).data["count"] == 0
    assert stranger.get(f"{MY_CEREMONIES}{couple['ceremony'].pk}/").status_code == 404
    assert stranger.get(INVITATIONS).data == []
    assert bride.get(f"{MY_CEREMONIES}{other.pk}/").status_code == 404


@pytest.mark.django_db
def test_invitation_scope_is_own_phone(couple, client_for, make_user):
    """Ownership: invitations are matched by the caller's phone; others cannot accept them."""
    invitation_id = client_for(couple["bride"]).get(INVITATIONS).data[0]["id"]
    thief = client_for(make_user(Role.USER))
    assert thief.post(f"{INVITATIONS}{invitation_id}/accept/").status_code == 404
    assert thief.post(f"{INVITATIONS}{invitation_id}/decline/").status_code == 404
    assert CeremonyParticipant.objects.get(pk=invitation_id).access_status == AccessStatus.INVITED


@pytest.mark.django_db
def test_draft_ceremony_hidden_from_couple(couple, client_for):
    bride = client_for(couple["bride"])
    bride.post(f"{INVITATIONS}{bride.get(INVITATIONS).data[0]['id']}/accept/")
    Ceremony.objects.filter(pk=couple["ceremony"].pk).update(status=CeremonyStatus.DRAFT)
    assert bride.get(MY_CEREMONIES).data["count"] == 0


@pytest.mark.django_db
def test_decline_and_revoke(couple, client_for):
    groom = client_for(couple["groom"])
    groom_inv = groom.get(INVITATIONS).data[0]["id"]
    assert groom.post(f"{INVITATIONS}{groom_inv}/decline/").status_code == 204
    assert groom.get(INVITATIONS).data == []

    bride = client_for(couple["bride"])
    bride.post(f"{INVITATIONS}{bride.get(INVITATIONS).data[0]['id']}/accept/")
    bride_row = CeremonyParticipant.objects.get(participant_type="BRIDE")
    res = couple["studio"].delete(f"{participants_url(couple['ceremony'])}{bride_row.pk}/")
    assert res.status_code == 204
    assert bride.get(MY_CEREMONIES).data["count"] == 0  # access gone immediately
    # a revoked bride slot can be re-invited
    assert invite(couple["studio"], couple["ceremony"], "+998935554433", "BRIDE").status_code == 201


@pytest.mark.django_db
def test_studio_account_cannot_accept_invitations(studio_world, client_for):
    c = make_ceremony(studio_world["studio_a"], status=CeremonyStatus.READY)
    owner = studio_world["owner_a"]
    invite(client_for(owner), c, owner.phone_number, "OTHER")
    assert client_for(owner).get(INVITATIONS).status_code == 403


@pytest.mark.django_db
def test_verified_phone_required_when_configured(couple, client_for):
    bride = client_for(couple["bride"])
    inv = bride.get(INVITATIONS).data[0]["id"]
    with override_settings(CEREMONY_INVITE_REQUIRE_VERIFIED_PHONE=True):
        res = bride.post(f"{INVITATIONS}{inv}/accept/")
        assert res.status_code == 403
        type(couple["bride"]).objects.filter(pk=couple["bride"].pk).update(is_phone_verified=True)
        assert bride.post(f"{INVITATIONS}{inv}/accept/").status_code == 200


@pytest.mark.django_db
def test_one_user_many_ceremonies(studio_world, make_user, client_for):
    guest = make_user(Role.USER, phone_number="+998935554433")
    studios = [client_for(studio_world["owner_a"]), client_for(studio_world["owner_b"])]
    for studio, s in zip(studios, (studio_world["studio_a"], studio_world["studio_b"]), strict=True):
        invite(studio, make_ceremony(s, status=CeremonyStatus.READY), guest.phone_number, "OTHER")
    client = client_for(guest)
    for inv in client.get(INVITATIONS).data:
        client.post(f"{INVITATIONS}{inv['id']}/accept/")
    assert client.get(MY_CEREMONIES).data["count"] == 2


@pytest.mark.django_db
def test_schema_has_ceremony_endpoints():
    from apps.monitoring import catalog

    catalog.reset_cache()
    paths = catalog.get_schema()["paths"]
    for p in (
        "/api/v1/studios/me/",
        "/api/v1/studios/me/ceremonies/",
        "/api/v1/ceremonies/",
        "/api/v1/ceremonies/{id}/",
        "/api/v1/ceremonies/{id}/participants/",
        "/api/v1/ceremonies/{id}/participants/{participant_id}/",
        "/api/v1/me/ceremonies/",
        "/api/v1/me/invitations/{id}/accept/",
    ):
        assert p in paths, p
