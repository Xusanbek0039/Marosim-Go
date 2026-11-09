"""Studio / venue partner applications from the landing page, reviewed on the staff "Yordam" page."""

import hashlib
import itertools

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.support import challenge
from apps.support.models import ApplicationStatus, PartnerApplication

PUBLIC = "/api/v1/public/partner-applications/"
STAFF = "/api/v1/admin/support/applications/"
FORM = {
    "kind": "STUDIO",
    "full_name": "Sardor Karimov",
    "phone_number": "90 123 45 67",
    "business_name": "Nur Studio",
    "region": "SAMARKAND",
    "message": "Oyiga 20 ta to'y yozamiz",
}


@pytest.fixture(autouse=True)
def _cheap_challenge(settings):
    """Real rules, smaller numbers: 8 bits of work, no minimum fill time (tested separately)."""
    settings.PARTNER_APPLY = {"POW_BITS": 8, "MIN_SECONDS": 0, "MAX_AGE_SECONDS": 7200}


def solve(token: str, bits: int) -> str:
    for n in itertools.count():
        if challenge.leading_zero_bits(hashlib.sha256(f"{token}:{n}".encode()).digest()) >= bits:
            return str(n)
    raise AssertionError  # pragma: no cover


def apply(client=None, **overrides):
    client = client or APIClient()
    ch = client.get(f"{PUBLIC}challenge/").data
    body = {**FORM, "challenge": ch["token"], "proof": solve(ch["token"], ch["difficulty"]), **overrides}
    return client.post(PUBLIC, body, format="json")


@pytest.mark.django_db
def test_anyone_can_apply_and_the_answer_reveals_nothing():
    ch = APIClient().get(f"{PUBLIC}challenge/")
    assert ch.status_code == 200 and ch.data["difficulty"] == 8 and ch["Cache-Control"] == "no-store"
    res = apply()
    assert res.status_code == 201 and res.data == {"received": True}
    row = PartnerApplication.objects.get()
    assert row.phone_number == "+998901234567" and row.status == ApplicationStatus.NEW
    assert row.business_name == "Nur Studio" and row.region == "SAMARKAND"


@pytest.mark.django_db
def test_invalid_input_is_rejected_and_honeypot_drops_bots():
    assert apply(phone_number="123").status_code == 400
    assert apply(kind="SHOP").status_code == 400
    assert apply(business_name="").status_code == 400
    assert apply(website="http://spam").status_code == 201
    assert PartnerApplication.objects.count() == 0


@pytest.mark.django_db
def test_bots_without_work_or_with_a_reused_or_forged_token_are_refused():
    client = APIClient()
    token = client.get(f"{PUBLIC}challenge/").data["token"]
    assert client.post(PUBLIC, FORM, format="json").status_code == 400  # no challenge at all
    wrong = next(str(n) for n in itertools.count() if solve(token, 8) != str(n))
    res = client.post(PUBLIC, {**FORM, "challenge": token, "proof": wrong}, format="json")
    assert res.status_code == 403 and res.data["error"]["code"] == "bot_check_failed"
    forged = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    assert client.post(PUBLIC, {**FORM, "challenge": forged, "proof": "1"}, format="json").status_code == 403

    proof = solve(token, 8)
    assert client.post(PUBLIC, {**FORM, "challenge": token, "proof": proof}, format="json").status_code == 201
    again = client.post(PUBLIC, {**FORM, "challenge": token, "proof": proof}, format="json")
    assert again.status_code == 403  # one token, one application
    assert PartnerApplication.objects.count() == 1


@pytest.mark.django_db
def test_instant_submission_is_refused(settings):
    settings.PARTNER_APPLY = {"POW_BITS": 4, "MIN_SECONDS": 60, "MAX_AGE_SECONDS": 7200}
    res = apply()
    assert res.status_code == 403 and "tez" in res.data["error"]["message"]


@pytest.mark.django_db
def test_one_phone_number_is_limited_per_day():
    for _ in range(3):
        assert apply().status_code == 201
    res = apply()
    assert res.status_code == 400 and "phone_number" in res.data["error"]["details"]
    assert apply(phone_number="+998907654321").status_code == 201


def test_leading_zero_bits():
    assert challenge.leading_zero_bits(b"\x00\x00\xff") == 16
    assert challenge.leading_zero_bits(b"\x00\x10") == 11
    assert challenge.leading_zero_bits(b"\x80") == 0


@pytest.mark.django_db
def test_staff_with_support_view_review_applications(make_user, client_for):
    apply()
    apply(kind="VENUE", business_name="Navro'z", phone_number="+998907654321")
    staff = client_for(make_user(Role.ADMIN, admin_permissions=["support.view"], first_name="Ko'rib"))
    assert client_for(make_user(Role.ADMIN, admin_permissions=[])).get(STAFF).status_code == 403
    assert client_for(make_user(Role.USER)).get(STAFF).status_code == 403

    listing = staff.get(STAFF).data
    assert listing["count"] == 2 and listing["results"][0]["region_label"] == "Samarqand viloyati"
    assert staff.get(STAFF, {"kind": "VENUE"}).data["count"] == 1
    assert staff.get(STAFF, {"search": "Nur"}).data["count"] == 1
    assert staff.get(f"{STAFF}summary/").data == {"new": 2, "in_review": 0}

    rid = staff.get(STAFF, {"kind": "STUDIO"}).data["results"][0]["id"]
    res = staff.patch(f"{STAFF}{rid}/", {"status": "IN_REVIEW", "staff_note": "Ertaga qo'ng'iroq"}, format="json")
    assert res.status_code == 200 and res.data["status"] == "IN_REVIEW"
    assert res.data["handled_by_name"].startswith("Ko'rib") and res.data["staff_note"] == "Ertaga qo'ng'iroq"
    assert staff.get(f"{STAFF}summary/").data == {"new": 1, "in_review": 1}
    assert client_for(make_user(Role.SUPER_ADMIN)).get(STAFF).data["count"] == 2
