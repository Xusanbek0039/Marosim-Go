"""Studio / venue partner applications from the landing page, reviewed on the staff "Yordam" page."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role
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


@pytest.mark.django_db
def test_anyone_can_apply_and_the_answer_reveals_nothing():
    res = APIClient().post(PUBLIC, FORM, format="json")
    assert res.status_code == 201 and res.data == {"received": True}
    row = PartnerApplication.objects.get()
    assert row.phone_number == "+998901234567" and row.status == ApplicationStatus.NEW
    assert row.business_name == "Nur Studio" and row.region == "SAMARKAND"


@pytest.mark.django_db
def test_invalid_input_is_rejected_and_honeypot_drops_bots():
    client = APIClient()
    assert client.post(PUBLIC, {**FORM, "phone_number": "123"}, format="json").status_code == 400
    assert client.post(PUBLIC, {**FORM, "kind": "SHOP"}, format="json").status_code == 400
    assert client.post(PUBLIC, {**FORM, "business_name": ""}, format="json").status_code == 400
    assert client.post(PUBLIC, {**FORM, "website": "http://spam"}, format="json").status_code == 201
    assert PartnerApplication.objects.count() == 0


@pytest.mark.django_db
def test_staff_with_support_view_review_applications(make_user, client_for):
    APIClient().post(PUBLIC, FORM, format="json")
    APIClient().post(PUBLIC, {**FORM, "kind": "VENUE", "business_name": "Navro'z"}, format="json")
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
