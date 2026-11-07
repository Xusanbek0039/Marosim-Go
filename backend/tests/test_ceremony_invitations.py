"""Phase C — invitation, acceptance, owner approval and revocation through the HTTP API."""

import json
from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.models import AuditAction, AuditLog
from apps.ceremonies import invitations as flows
from apps.ceremonies import ownership
from apps.ceremonies.models import (
    Ceremony,
    CeremonyInvitation,
    CeremonyOwnership,
    CeremonyStatus,
    CeremonyViewerAccess,
    InvitationStatus,
    OwnershipStatus,
    ViewerStatus,
)
from apps.studios.services import sync_owner_membership

from .conftest import next_pinfl

INV = "/api/v1/me/invitations/"
MY = "/api/v1/me/ceremonies/"


def studio_invite(client, ceremony, identifier, owner_type="BRIDE", identifier_type="PHONE"):
    return client.post(
        f"/api/v1/ceremonies/{ceremony.pk}/owners/invite/",
        {"identifier_type": identifier_type, "identifier": identifier, "owner_type": owner_type},
        format="json",
    )


def owner_invite(client, ceremony, identifier, role="VIEWER", owner_type="", identifier_type="PHONE", duration="1W"):
    body = {"identifier_type": identifier_type, "identifier": identifier, "requested_role": role}
    if owner_type:
        body["owner_type"] = owner_type
    if role == "VIEWER" and duration:
        body["access_duration"] = duration
    return client.post(f"{MY}{ceremony.pk}/invitations/", body, format="json")


def answer(client, verb="accept", index=0):
    pending = client.get(INV).data
    return client.post(f"{INV}{pending[index]['id']}/{verb}/")


@pytest.fixture
def world(make_user, make_studio, client_for):
    studio_owner, rival_owner = make_user(Role.STUDIO), make_user(Role.STUDIO)
    studio, rival = make_studio(studio_owner), make_studio(rival_owner)
    sync_owner_membership(studio)
    sync_owner_membership(rival)
    ceremony = Ceremony.objects.create(studio=studio, title="Dilnoza & Jasur", event_date="2026-09-12")
    ceremony.status = CeremonyStatus.READY
    ceremony.save()
    other = Ceremony.objects.create(
        studio=rival, title="Boshqa to'y", event_date="2026-10-01", status=CeremonyStatus.READY
    )
    users = {name: make_user(Role.USER, is_phone_verified=True, first_name=name.title()) for name in (
        "bride", "groom", "mother", "guest", "stranger"
    )}  # fmt: skip
    return {
        "ceremony": ceremony,
        "other": other,
        "studio": client_for(studio_owner),
        "rival": client_for(rival_owner),
        "users": users,
        "c": {name: client_for(u) for name, u in users.items()},
    }


@pytest.fixture
def wedding(world):
    """The bride is the ceremony's first (and only) owner."""
    assert studio_invite(world["studio"], world["ceremony"], world["users"]["bride"].phone_number).status_code == 201
    assert answer(world["c"]["bride"]).data["status"] == "ACCEPTED"
    return world


# --------------------------------------------------------------- first owner
@pytest.mark.django_db
def test_studio_invites_first_owner_who_accepts(world):
    c, bride = world["ceremony"], world["c"]["bride"]
    res = studio_invite(world["studio"], c, world["users"]["bride"].phone_number)
    assert res.status_code == 201 and res.data["status"] == "PENDING" and res.data["display_name"] is None
    assert bride.get(f"{MY}{c.pk}/").status_code == 404  # an invitation alone grants nothing

    pending = bride.get(INV).data
    assert len(pending) == 1 and pending[0]["requested_role"] == "OWNER" and pending[0]["owner_type"] == "BRIDE"
    assert pending[0]["ceremony_title"] == "Dilnoza & Jasur" and pending[0]["requires_owner_approval"] is False
    assert bride.get(f"{INV}{pending[0]['id']}/").status_code == 200

    res = bride.post(f"{INV}{pending[0]['id']}/accept/")
    assert res.status_code == 200 and res.data["status"] == "ACCEPTED" and res.data["access_role"] == "OWNER"
    assert res.data["ceremony"]["access_role"] == "OWNER" and res.data["ceremony"]["my_role"] == "BRIDE"
    owners = world["studio"].get(f"/api/v1/ceremonies/{c.pk}/owners/").data
    assert owners[0]["ownership_status"] == "ACCEPTED" and owners[0]["display_name"].startswith("Bride")
    assert AuditLog.objects.filter(action=AuditAction.OWNER_INVITE).exists()
    assert AuditLog.objects.filter(action=AuditAction.OWNER_ACCEPT, actor=world["users"]["bride"]).exists()


@pytest.mark.django_db
def test_owner_invitation_rejection(world):
    studio_invite(world["studio"], world["ceremony"], world["users"]["bride"].phone_number)
    assert answer(world["c"]["bride"], "decline").status_code == 204
    assert world["c"]["bride"].get(INV).data == []
    assert CeremonyInvitation.objects.get().status == InvitationStatus.DECLINED
    assert not CeremonyOwnership.objects.exists()
    assert AuditLog.objects.filter(action=AuditAction.INVITATION_DECLINE).exists()


# ------------------------------------------------------------ more owners
@pytest.mark.django_db
def test_multiple_owners_need_existing_owner_approval(wedding):
    w = wedding
    c, bride, groom = w["ceremony"], w["c"]["bride"], w["c"]["groom"]
    studio_invite(w["studio"], c, w["users"]["groom"].phone_number, "GROOM")
    assert groom.get(INV).data[0]["requires_owner_approval"] is True
    res = answer(groom)
    assert res.data["status"] == "PENDING_APPROVAL" and res.data["ceremony"] is None
    assert groom.get(f"{MY}{c.pk}/").status_code == 404  # pending ownership grants nothing

    requests_ = bride.get(f"{MY}{c.pk}/owner-requests/").data
    assert len(requests_) == 1 and requests_[0]["candidate_name"].startswith("Groom")
    assert requests_[0]["recipient_hint"].count("*") == 3 and requests_[0]["can_decide"] is True
    res = bride.post(f"{MY}{c.pk}/owner-requests/{requests_[0]['id']}/approve/")
    assert res.status_code == 200 and res.data["status"] == "ACCEPTED"
    assert groom.get(f"{MY}{c.pk}/").data["my_role"] == "GROOM"

    # A third owner, invited by the bride: her invitation is her approval, the groom still decides.
    assert owner_invite(bride, c, w["users"]["mother"].phone_number, "OWNER", "FAMILY_OWNER").status_code == 201
    assert answer(w["c"]["mother"]).data["status"] == "PENDING_APPROVAL"
    req = groom.get(f"{MY}{c.pk}/owner-requests/").data[0]
    assert {a["decision"] for a in req["approvals"]} == {"APPROVED", "PENDING"}
    assert bride.post(f"{MY}{c.pk}/owner-requests/{req['id']}/approve/").status_code == 403  # already voted
    groom.post(f"{MY}{c.pk}/owner-requests/{req['id']}/approve/")
    members = bride.get(f"{MY}{c.pk}/members/").data
    assert {o["owner_type"] for o in members["owners"]} == {"BRIDE", "GROOM", "FAMILY_OWNER"}
    assert json.dumps(members).count("+998") == 0


@pytest.mark.django_db
def test_owner_request_rejected_by_one_owner(wedding):
    w = wedding
    c, bride = w["ceremony"], w["c"]["bride"]
    studio_invite(w["studio"], c, w["users"]["stranger"].phone_number, "GROOM")
    answer(w["c"]["stranger"])
    req = bride.get(f"{MY}{c.pk}/owner-requests/").data[0]
    res = bride.post(f"{MY}{c.pk}/owner-requests/{req['id']}/reject/")
    assert res.status_code == 200 and res.data["status"] == "REJECTED"
    assert w["c"]["stranger"].get(f"{MY}{c.pk}/").status_code == 404
    assert AuditLog.objects.filter(action=AuditAction.OWNER_REJECT).exists()
    # the GROOM slot is free again
    assert studio_invite(w["studio"], c, w["users"]["groom"].phone_number, "GROOM").status_code == 201


# ------------------------------------------------------------------ viewers
@pytest.mark.django_db
def test_viewer_invitation_acceptance_and_rejection(wedding):
    w = wedding
    c, bride = w["ceremony"], w["c"]["bride"]
    assert owner_invite(bride, c, w["users"]["guest"].phone_number).status_code == 201
    res = answer(w["c"]["guest"])
    assert res.data == {**res.data, "status": "ACCEPTED", "access_role": "VIEWER"}
    assert res.data["ceremony"]["access_role"] == "VIEWER" and res.data["ceremony"]["my_role"] is None
    assert w["c"]["guest"].get(MY).data["count"] == 1

    owner_invite(bride, c, w["users"]["mother"].phone_number)
    assert answer(w["c"]["mother"], "decline").status_code == 204
    assert w["c"]["mother"].get(f"{MY}{c.pk}/").status_code == 404
    assert AuditLog.objects.filter(action=AuditAction.VIEWER_ACCEPT).count() == 1


@pytest.mark.django_db
def test_viewer_cannot_invite_promote_or_manage(wedding):
    w = wedding
    c, bride, guest = w["ceremony"], w["c"]["bride"], w["c"]["guest"]
    owner_invite(bride, c, w["users"]["guest"].phone_number)
    answer(guest)
    assert owner_invite(guest, c, w["users"]["stranger"].phone_number).status_code == 403
    assert owner_invite(guest, c, w["users"]["stranger"].phone_number, "OWNER", "OTHER_OWNER").status_code == 403
    for path in ("members/", "invitations/", "owner-requests/"):
        assert guest.get(f"{MY}{c.pk}/{path}").status_code == 403
    assert not CeremonyInvitation.objects.filter(invited_by=w["users"]["guest"]).exists()


# ------------------------------------------------------- wrong / cross access
@pytest.mark.django_db
def test_wrong_user_cannot_see_or_accept_invitation(world):
    studio_invite(world["studio"], world["ceremony"], world["users"]["bride"].phone_number)
    invitation_id = world["c"]["bride"].get(INV).data[0]["id"]
    thief = world["c"]["stranger"]
    assert thief.get(INV).data == []
    assert thief.get(f"{INV}{invitation_id}/").status_code == 404
    assert thief.post(f"{INV}{invitation_id}/accept/").status_code == 404
    assert thief.post(f"{INV}{invitation_id}/decline/").status_code == 404
    assert CeremonyInvitation.objects.get().status == InvitationStatus.PENDING


@pytest.mark.django_db
def test_cross_ceremony_and_cross_studio_denied(wedding):
    w = wedding
    c, other, bride = w["ceremony"], w["other"], w["c"]["bride"]
    assert bride.get(f"{MY}{other.pk}/").status_code == 404
    assert owner_invite(bride, other, w["users"]["guest"].phone_number).status_code == 404
    assert bride.get(f"{MY}{other.pk}/members/").status_code == 404
    # another studio can neither see nor invite owners to this ceremony
    assert w["rival"].get(f"/api/v1/ceremonies/{c.pk}/owners/").status_code == 404
    assert studio_invite(w["rival"], c, w["users"]["groom"].phone_number, "GROOM").status_code == 404
    # studios cannot use the owner endpoints, owners cannot use studio endpoints
    assert w["studio"].get(f"{MY}{c.pk}/").status_code == 403
    assert bride.get(f"/api/v1/ceremonies/{c.pk}/owners/").status_code == 403


@pytest.mark.django_db
def test_other_ceremony_ids_do_not_leak_through_nested_routes(wedding, make_user, client_for):
    w = wedding
    c, bride = w["ceremony"], w["c"]["bride"]
    # an invitation of another ceremony, addressed through this ceremony's URL
    foreign = CeremonyInvitation.objects.create(
        ceremony=w["other"],
        requested_role="OWNER",
        owner_type="BRIDE",
        inviter_kind="STUDIO",
        expires_at=ownership.default_expiry(),
        **ownership.seal_identifier("PHONE", "+998901119999"),
    )
    assert bride.post(f"{MY}{c.pk}/invitations/{foreign.pk}/revoke/").status_code == 404
    assert bride.post(f"{MY}{c.pk}/invitations/{foreign.pk}/resend/").status_code == 404


# ---------------------------------------------------------------- revocation
@pytest.mark.django_db
def test_owner_cannot_revoke_unrelated_access(wedding):
    w = wedding
    c, bride, groom = w["ceremony"], w["c"]["bride"], w["c"]["groom"]
    studio_invite(w["studio"], c, w["users"]["groom"].phone_number, "GROOM")
    answer(groom)
    bride.post(f"{MY}{c.pk}/owner-requests/{bride.get(f'{MY}{c.pk}/owner-requests/').data[0]['id']}/approve/")

    owner_invite(bride, c, w["users"]["guest"].phone_number)
    answer(w["c"]["guest"])
    owner_invite(bride, c, w["users"]["mother"].phone_number)  # still pending
    access = CeremonyViewerAccess.objects.get()
    pending = CeremonyInvitation.objects.get(status=InvitationStatus.PENDING)

    assert groom.post(f"{MY}{c.pk}/viewers/{access.pk}/revoke/").status_code == 403
    assert groom.post(f"{MY}{c.pk}/invitations/{pending.pk}/revoke/").status_code == 403
    viewers = groom.get(f"{MY}{c.pk}/members/").data["viewers"]
    assert viewers[0]["can_revoke"] is False and viewers[0]["granted_by_me"] is False
    # no endpoint lets an owner remove another owner
    assert CeremonyOwnership.objects.filter(status=OwnershipStatus.ACCEPTED).count() == 2

    assert bride.post(f"{MY}{c.pk}/invitations/{pending.pk}/revoke/").status_code == 204
    assert bride.post(f"{MY}{c.pk}/viewers/{access.pk}/revoke/").status_code == 204
    assert AuditLog.objects.filter(action=AuditAction.ACCESS_REVOKE).count() == 1


@pytest.mark.django_db
def test_revoked_viewer_loses_access_immediately(wedding):
    w = wedding
    c, bride, guest = w["ceremony"], w["c"]["bride"], w["c"]["guest"]
    owner_invite(bride, c, w["users"]["guest"].phone_number)
    answer(guest)
    assert guest.get(f"{MY}{c.pk}/").status_code == 200
    bride.post(f"{MY}{c.pk}/viewers/{CeremonyViewerAccess.objects.get().pk}/revoke/")
    assert guest.get(f"{MY}{c.pk}/").status_code == 404
    assert guest.get(MY).data["count"] == 0


@pytest.mark.django_db
def test_leaving_owner_takes_their_pending_invitations_and_votes_along(wedding):
    w = wedding
    c, bride, groom = w["ceremony"], w["c"]["bride"], w["c"]["groom"]
    studio_invite(w["studio"], c, w["users"]["groom"].phone_number, "GROOM")
    answer(groom)
    bride.post(f"{MY}{c.pk}/owner-requests/{bride.get(f'{MY}{c.pk}/owner-requests/').data[0]['id']}/approve/")

    owner_invite(groom, c, w["users"]["guest"].phone_number)  # pending, from the groom
    studio_invite(w["studio"], c, w["users"]["mother"].phone_number, "FAMILY_OWNER")
    answer(w["c"]["mother"])  # needs bride + groom
    bride.post(f"{MY}{c.pk}/owner-requests/{bride.get(f'{MY}{c.pk}/owner-requests/').data[0]['id']}/approve/")
    assert w["c"]["mother"].get(f"{MY}{c.pk}/").status_code == 404

    assert groom.post(f"{MY}{c.pk}/leave/").status_code == 204
    assert groom.get(f"{MY}{c.pk}/").status_code == 404
    assert w["c"]["guest"].get(INV).data == []  # the groom's invitation lapsed with him
    assert w["c"]["mother"].get(f"{MY}{c.pk}/").status_code == 200  # his vote no longer blocks


@pytest.mark.django_db
def test_studio_cannot_remove_accepted_owner(wedding, super_admin, client_for):
    w = wedding
    c = w["ceremony"]
    row = w["studio"].get(f"/api/v1/ceremonies/{c.pk}/participants/").data[0]
    assert row["access_status"] == "ACTIVE"
    assert w["studio"].delete(f"/api/v1/ceremonies/{c.pk}/participants/{row['id']}/").status_code == 403
    assert w["c"]["bride"].get(f"{MY}{c.pk}/").status_code == 200
    assert client_for(super_admin).delete(f"/api/v1/ceremonies/{c.pk}/participants/{row['id']}/").status_code == 204
    assert w["c"]["bride"].get(f"{MY}{c.pk}/").status_code == 404


# --------------------------------------------------------------- privacy
@pytest.mark.django_db
def test_invite_response_does_not_reveal_account_existence(wedding):
    w = wedding
    c, bride = w["ceremony"], w["c"]["bride"]
    known = owner_invite(bride, c, w["users"]["guest"].phone_number)
    unknown = owner_invite(bride, c, "+998939990000")
    assert known.status_code == unknown.status_code == 201
    volatile = {"id", "recipient_hint", "invited_at", "expires_at"}
    assert {k: v for k, v in known.data.items() if k not in volatile} == {
        k: v for k, v in unknown.data.items() if k not in volatile
    }
    assert "+99890" not in json.dumps(known.data) and known.data["recipient_hint"].count("*") == 3

    studio_known = studio_invite(w["studio"], c, w["users"]["groom"].phone_number, "GROOM")
    studio_unknown = studio_invite(w["studio"], c, "+998939990001", "FAMILY_OWNER")
    assert studio_known.status_code == studio_unknown.status_code == 201
    assert studio_known.data["display_name"] is None and studio_unknown.data["display_name"] is None


@pytest.mark.django_db
def test_jshshir_invitations_stay_private(wedding, make_user, client_for):
    w = wedding
    c, bride = w["ceremony"], w["c"]["bride"]
    pinfl = next_pinfl()
    cousin = make_user(Role.USER, pinfl=pinfl, is_phone_verified=True)
    res = owner_invite(bride, c, pinfl, identifier_type="PINFL")
    assert res.status_code == 201 and pinfl not in json.dumps(res.data)
    assert res.data["recipient_hint"] == f"{'*' * 10}{pinfl[-4:]}"
    history = json.dumps(bride.get(f"{MY}{c.pk}/invitations/").data)
    assert pinfl not in history
    assert all(pinfl not in json.dumps(a.changes) for a in AuditLog.objects.all())

    assert client_for(cousin).get(INV).data[0]["requested_role"] == "VIEWER"
    assert w["c"]["stranger"].get(INV).data == []
    bad = owner_invite(bride, c, "1234", identifier_type="PINFL")
    assert bad.status_code == 400 and "identifier" in bad.data["error"]["details"]


@pytest.mark.django_db
def test_jshshir_cannot_found_ownership(world, make_user, client_for):
    pinfl = next_pinfl()
    make_user(Role.USER, pinfl=pinfl, is_phone_verified=True)
    res = studio_invite(world["studio"], world["ceremony"], pinfl, identifier_type="PINFL")
    assert res.status_code == 400 and "identifier_type" in res.data["error"]["details"]


@pytest.mark.django_db
@override_settings(CEREMONY_OWNER_REQUIRE_VERIFIED_PHONE=True, CEREMONY_INVITE_REQUIRE_VERIFIED_PHONE=False)
def test_unverified_phone_cannot_claim_ownership(world, make_user, client_for):
    squatter = make_user(Role.USER, phone_number="+998977001122")  # registered, never verified
    studio_invite(world["studio"], world["ceremony"], squatter.phone_number)
    client = client_for(squatter)
    listed = client.get(INV).data[0]
    assert listed["phone_verification_required"] is True
    assert listed["ceremony_title"] is None and listed["studio_name"] is None and listed["inviter_display"] is None
    res = client.post(f"{INV}{listed['id']}/accept/")
    assert res.status_code == 403 and res.data["error"]["code"] == "phone_not_verified"
    assert not CeremonyOwnership.objects.exists()
    assert client.post(f"{INV}{listed['id']}/decline/").status_code == 204  # declining needs no proof


# ---------------------------------------------------- expiry / duplicates
@pytest.mark.django_db
def test_expired_invitation_rejected_and_resend_revives_it(wedding):
    w = wedding
    c, bride, guest = w["ceremony"], w["c"]["bride"], w["c"]["guest"]
    created = owner_invite(bride, c, w["users"]["guest"].phone_number).data
    invitation_id = guest.get(INV).data[0]["id"]
    CeremonyInvitation.objects.filter(pk=created["id"]).update(expires_at=timezone.now() - timedelta(minutes=1))

    assert guest.get(INV).data == []
    res = guest.post(f"{INV}{invitation_id}/accept/")
    assert res.status_code == 410 and res.data["error"]["code"] == "invitation_expired"
    assert CeremonyInvitation.objects.get(pk=created["id"]).status == InvitationStatus.EXPIRED  # persisted
    assert bride.get(f"{MY}{c.pk}/invitations/").data[0]["status"] == "EXPIRED"

    res = bride.post(f"{MY}{c.pk}/invitations/{created['id']}/resend/")
    assert res.status_code == 200 and res.data["status"] == "PENDING" and res.data["send_count"] == 2
    assert answer(guest).data["status"] == "ACCEPTED"


@pytest.mark.django_db
@override_settings(CEREMONY_MAX_INVITATION_SENDS=2)
def test_resend_is_limited(wedding):
    w = wedding
    c, bride = w["ceremony"], w["c"]["bride"]
    created = owner_invite(bride, c, w["users"]["guest"].phone_number).data
    url = f"{MY}{c.pk}/invitations/{created['id']}/resend/"
    assert bride.post(url).status_code == 200
    assert bride.post(url).status_code == 400


@pytest.mark.django_db
def test_expire_command(wedding):
    from django.core.management import call_command

    w = wedding
    owner_invite(w["c"]["bride"], w["ceremony"], w["users"]["guest"].phone_number)
    CeremonyInvitation.objects.filter(status="PENDING").update(expires_at=timezone.now() - timedelta(seconds=1))
    call_command("expire_ceremony_invitations")
    assert not CeremonyInvitation.objects.filter(status="PENDING").exists()


@pytest.mark.django_db
def test_duplicate_invitation_handling(wedding):
    w = wedding
    c, bride = w["ceremony"], w["c"]["bride"]
    phone = w["users"]["guest"].phone_number
    first = owner_invite(bride, c, phone)
    dup = owner_invite(bride, c, phone.replace("+998", ""))  # same number, other format
    assert dup.status_code == 400 and "identifier" in dup.data["error"]["details"]
    assert owner_invite(bride, c, w["users"]["bride"].phone_number).status_code == 400  # self
    bride.post(f"{MY}{c.pk}/invitations/{first.data['id']}/revoke/")
    assert owner_invite(bride, c, phone).status_code == 201
    # a second bride slot is refused
    second = studio_invite(w["studio"], c, w["users"]["mother"].phone_number, "BRIDE")
    assert second.status_code == 400 and "owner_type" in second.data["error"]["details"]


@pytest.mark.django_db
def test_already_member_cannot_accept_again(wedding):
    w = wedding
    c, bride = w["ceremony"], w["c"]["bride"]
    owner_invite(bride, c, w["users"]["guest"].phone_number)
    answer(w["c"]["guest"])
    CeremonyInvitation.objects.create(
        ceremony=c,
        requested_role="VIEWER",
        inviter_kind="OWNER",
        invited_by=w["users"]["bride"],
        expires_at=ownership.default_expiry(),
        **ownership.seal_identifier("PHONE", w["users"]["guest"].phone_number),
    )
    assert answer(w["c"]["guest"]).status_code == 409


# ------------------------------------------------------------ concurrency
@pytest.mark.django_db
def test_concurrent_acceptance_has_one_winner(wedding, monkeypatch):
    """Both requests pass the checks before either writes: the conditional UPDATE lets one win."""
    from rest_framework.exceptions import NotFound
    from rest_framework.test import APIRequestFactory

    w = wedding
    owner_invite(w["c"]["bride"], w["ceremony"], w["users"]["guest"].phone_number)
    stale = CeremonyInvitation.objects.get(status=InvitationStatus.PENDING)
    assert answer(w["c"]["guest"]).status_code == 200

    monkeypatch.setattr(ownership, "response_refusal", lambda *a, **k: None)
    request = APIRequestFactory().post("/")
    request.user = w["users"]["guest"]
    with pytest.raises(NotFound):
        flows.accept(request, stale)
    assert CeremonyViewerAccess.objects.filter(status=ViewerStatus.ACCEPTED).count() == 1


@pytest.mark.django_db
def test_concurrent_approval_counts_once(wedding):
    w = wedding
    c, bride = w["ceremony"], w["c"]["bride"]
    studio_invite(w["studio"], c, w["users"]["groom"].phone_number, "GROOM")
    answer(w["c"]["groom"])
    req = bride.get(f"{MY}{c.pk}/owner-requests/").data[0]["id"]
    assert bride.post(f"{MY}{c.pk}/owner-requests/{req}/approve/").status_code == 200
    assert bride.post(f"{MY}{c.pk}/owner-requests/{req}/reject/").status_code == 404  # no longer pending
    assert CeremonyOwnership.objects.get(user=w["users"]["groom"]).status == OwnershipStatus.ACCEPTED


# ------------------------------------------------------- API documentation
@pytest.mark.django_db
def test_owner_endpoints_document_ceremony_conditions():
    from apps.monitoring import catalog

    catalog.reset_cache()
    by_id = {e["id"]: e for e in catalog.build()}
    for op in ("me_ceremonies_invitations_create", "me_ceremonies_members_retrieve", "me_ceremonies_leave_create"):
        e = by_id[op]
        assert e["allowed_roles"] == ["USER"] and "CEREMONY_OWNER" in e["ownership_scope"]
    assert any("CEREMONY_OWNER" in c for c in by_id["me_ceremonies_invitations_create"]["conditions"])
