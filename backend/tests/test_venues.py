"""V5.0 Phase B: venues, halls, memberships and the venue-owner API."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.models import Role
from apps.audit.models import AuditLog
from apps.venues import services
from apps.venues.models import (
    CAPABILITIES,
    Capability,
    MembershipRole,
    PublicationStatus,
    Venue,
    VenueHall,
    VenueMembership,
)

from .conftest import PASSWORD, image_file, next_pinfl

BASE = "/api/v1/venue-owner/venues/"
VENUE_DATA = {
    "name": "Navro'z to'yxonasi",
    "address": "Toshkent, Chilonzor 9",
    "region": "TASHKENT_CITY",
    "district": "Chilonzor",
    "capacity_min": 100,
    "capacity_max": 600,
    "base_price": "45000000.00",
}


@pytest.fixture
def venue_owner(make_user):
    return make_user(Role.VENUE_OWNER)


@pytest.fixture
def make_venue(db):
    def factory(owner, **extra) -> Venue:
        data = {**VENUE_DATA, "base_price": Decimal(VENUE_DATA["base_price"]), **extra}
        data.setdefault("name", f"Venue {owner.pk.hex[:6]}")
        return services.create_venue(None, owner, **data)

    return factory


def _member(venue, user, role):
    return VenueMembership.objects.create(venue=venue, user=user, role=role)


# ------------------------------------------------------------- creation
@pytest.mark.django_db
def test_venue_owner_creates_private_venue_with_owner_membership_and_default_hall(venue_owner, client_for):
    payload = {**VENUE_DATA, "phone_number": "90 123 45 67", "publication_status": "APPROVED", "is_active": False}
    payload["currency"] = "USD"
    res = client_for(venue_owner).post(BASE, payload, format="json")
    assert res.status_code == 201, res.data
    venue = Venue.objects.get(pk=res.data["id"])
    # client cannot self-approve, unblock or change currency
    assert venue.publication_status == PublicationStatus.PRIVATE and venue.is_active and venue.currency == "UZS"
    assert venue.phone_number == "+998901234567"
    assert res.data["membership_role"] == "OWNER"
    assert set(res.data["membership_capabilities"]) == set(Capability.values)
    membership = VenueMembership.objects.get(venue=venue)
    assert membership.user == venue_owner and membership.role == MembershipRole.OWNER
    [hall] = res.data["halls"]
    assert hall["name"] == services.DEFAULT_HALL_NAME and hall["capacity"] == 600
    assert hall["base_price"] is None and hall["effective_base_price"] == "45000000.00"
    assert AuditLog.objects.filter(target_id=str(venue.pk), action="CREATE").exists()


@pytest.mark.django_db
def test_cover_image_is_reencoded(venue_owner, client_for):
    res = client_for(venue_owner).post(BASE, {**VENUE_DATA, "cover_image": image_file()}, format="multipart")
    assert res.status_code == 201, res.data
    assert Venue.objects.get(pk=res.data["id"]).cover_image.name.endswith(".webp")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "patch, field",
    [
        ({"capacity_min": 700}, "capacity_min"),
        ({"capacity_max": 0}, "capacity_max"),
        ({"base_price": "-1"}, "base_price"),
        ({"region": "MARS"}, "region"),
        ({"latitude": "41.3"}, "latitude"),
        ({"latitude": "91", "longitude": "69.2"}, "latitude"),
        ({"phone_number": "12345"}, "phone_number"),
        ({"name": "   "}, "name"),
    ],
)
def test_venue_validation(venue_owner, client_for, patch, field):
    res = client_for(venue_owner).post(BASE, {**VENUE_DATA, **patch}, format="json")
    assert res.status_code == 400 and field in res.data["error"]["details"], res.data


@pytest.mark.django_db
def test_create_venue_service_requires_venue_owner_account(make_user, make_venue):
    for role in (Role.USER, Role.STUDIO, Role.ADMIN):
        with pytest.raises(ValidationError):
            make_venue(make_user(role))
    with pytest.raises(ValidationError):
        make_venue(make_user(Role.VENUE_OWNER, is_active=False))


@pytest.mark.django_db
def test_super_admin_manages_venue_owner_accounts(super_admin, client_for):
    client = client_for(super_admin)
    res = client.post(
        "/api/v1/users/",
        {
            "phone_number": "+998935550011",
            "first_name": "To'yxona",
            "last_name": "Egasi",
            "role": "VENUE_OWNER",
            "password": PASSWORD,
            "password_confirm": PASSWORD,
            "pinfl": next_pinfl(),
        },
        format="json",
    )
    assert res.status_code == 201, res.data
    assert res.data["role"] == "VENUE_OWNER"
    listed = client.get("/api/v1/users/", {"role": "VENUE_OWNER"}).data["results"]
    assert [row["id"] for row in listed] == [res.data["id"]]


# ------------------------------------------------- ownership & isolation
@pytest.mark.django_db
def test_venue_scope_is_own_membership(make_user, make_venue, client_for):
    owner_a, owner_b = make_user(Role.VENUE_OWNER), make_user(Role.VENUE_OWNER)
    venue_a, venue_b = make_venue(owner_a, name="A"), make_venue(owner_b, name="B")
    hall_b = venue_b.halls.get()
    client = client_for(owner_a)

    listed = {row["id"] for row in client.get(BASE).data["results"]}
    assert listed == {str(venue_a.pk)}
    foreign = f"{BASE}{venue_b.pk}/"
    assert client.get(foreign).status_code == 404
    assert client.patch(foreign, {"name": "Hijack"}, format="json").status_code == 404
    assert client.get(f"{foreign}halls/").status_code == 404
    assert client.post(f"{foreign}halls/", {"name": "X", "capacity": 10}, format="json").status_code == 404
    assert client.patch(f"{foreign}halls/{hall_b.pk}/", {"capacity": 1}, format="json").status_code == 404
    # a foreign hall through one's own venue URL is a 404 as well (hall isolation)
    own_url_foreign_hall = f"{BASE}{venue_a.pk}/halls/{hall_b.pk}/"
    assert client.patch(own_url_foreign_hall, {"capacity": 1}, format="json").status_code == 404
    venue_b.refresh_from_db()
    hall_b.refresh_from_db()
    assert venue_b.name == "B" and hall_b.capacity == 600

    # inactive membership and deleted venue disappear
    VenueMembership.objects.filter(venue=venue_a, user=owner_a).update(is_active=False)
    assert client.get(f"{BASE}{venue_a.pk}/").status_code == 404
    venue_b.soft_delete()
    assert client_for(owner_b).get(f"{BASE}{venue_b.pk}/").status_code == 404
    assert client_for(owner_b).get(BASE).data["results"] == []


@pytest.mark.django_db
def test_one_account_member_of_several_venues_with_different_roles(make_user, make_venue, client_for):
    staff = make_user(Role.VENUE_OWNER)
    venue_a = make_venue(make_user(Role.VENUE_OWNER), name="A")
    venue_b = make_venue(make_user(Role.VENUE_OWNER), name="B")
    services.add_member(None, venue_a, staff, MembershipRole.MANAGER)
    services.add_member(None, venue_b, staff, MembershipRole.VIEWER)
    client = client_for(staff)
    rows = {row["name"]: row for row in client.get(BASE).data["results"]}
    assert rows["A"]["membership_role"] == "MANAGER" and rows["B"]["membership_role"] == "VIEWER"
    assert client.patch(f"{BASE}{venue_a.pk}/", {"district": "Yunusobod"}, format="json").status_code == 200
    assert client.patch(f"{BASE}{venue_b.pk}/", {"district": "Yunusobod"}, format="json").status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role, can_edit, can_halls",
    [
        (MembershipRole.OWNER, True, True),
        (MembershipRole.MANAGER, True, True),
        (MembershipRole.SCHEDULER, False, False),
        (MembershipRole.VIEWER, False, False),
    ],
)
def test_membership_capabilities(make_user, make_venue, client_for, role, can_edit, can_halls):
    venue = make_venue(make_user(Role.VENUE_OWNER))
    member = make_user(Role.VENUE_OWNER)
    _member(venue, member, role)
    client = client_for(member)
    url = f"{BASE}{venue.pk}/"
    hall = venue.halls.get()

    assert client.get(url).status_code == 200 and client.get(f"{url}halls/").status_code == 200
    assert client.patch(url, {"description": "Yangi"}, format="json").status_code == (200 if can_edit else 403)
    created = client.post(f"{url}halls/", {"name": "Kichik zal", "capacity": 80}, format="json")
    assert created.status_code == (201 if can_halls else 403)
    edited = client.patch(f"{url}halls/{hall.pk}/", {"base_price": "30000000"}, format="json")
    assert edited.status_code == (200 if can_halls else 403)
    assert set(client.get(url).data["membership_capabilities"]) == set(CAPABILITIES[role])


@pytest.mark.django_db
def test_blocked_venue_is_read_only_for_members(venue_owner, make_venue, client_for):
    venue = make_venue(venue_owner)
    Venue.objects.filter(pk=venue.pk).update(is_active=False)
    client = client_for(venue_owner)
    url = f"{BASE}{venue.pk}/"
    res = client.get(url)
    assert res.status_code == 200 and res.data["is_active"] is False and res.data["membership_capabilities"] == ["VIEW"]
    assert client.patch(url, {"name": "X"}, format="json").status_code == 403
    assert client.post(f"{url}halls/", {"name": "X", "capacity": 5}, format="json").status_code == 403


@pytest.mark.django_db
def test_owner_cannot_change_admin_controlled_fields(venue_owner, make_venue, client_for):
    venue = make_venue(venue_owner)
    res = client_for(venue_owner).patch(
        f"{BASE}{venue.pk}/", {"publication_status": "APPROVED", "is_active": False, "currency": "USD"}, format="json"
    )
    assert res.status_code == 200
    venue.refresh_from_db()
    assert venue.publication_status == PublicationStatus.PRIVATE and venue.is_active and venue.currency == "UZS"


@pytest.mark.parametrize("role", [Role.USER, Role.STUDIO, Role.ADMIN, Role.SUPER_ADMIN])
@pytest.mark.django_db
def test_other_roles_cannot_use_venue_owner_api(make_user, venue_owner, make_venue, client_for, role):
    venue = make_venue(venue_owner)
    client = client_for(make_user(role))
    assert client.get(BASE).status_code == 403
    assert client.post(BASE, VENUE_DATA, format="json").status_code == 403
    assert client.get(f"{BASE}{venue.pk}/").status_code == 403


@pytest.mark.django_db
def test_owner_response_has_no_member_personal_data(venue_owner, make_venue, client_for):
    venue = make_venue(venue_owner)
    body = str(client_for(venue_owner).get(f"{BASE}{venue.pk}/").data)
    assert venue_owner.phone_number not in body and venue_owner.last_name not in body
    assert str(venue_owner.pk) not in body


# ----------------------------------------------------------------- halls
@pytest.mark.django_db
def test_halls_are_independent_rooms_of_one_venue(venue_owner, make_venue, client_for):
    venue = make_venue(venue_owner)
    client = client_for(venue_owner)
    url = f"{BASE}{venue.pk}/halls/"
    res = client.post(url, {"name": "Kichik zal", "capacity": 120, "base_price": "20000000"}, format="json")
    assert res.status_code == 201 and res.data["effective_base_price"] == "20000000.00"
    assert client.post(url, {"name": "kichik  ZAL", "capacity": 50}, format="json").status_code == 400
    assert client.post(url, {"name": "Yana", "capacity": 0}, format="json").status_code == 400
    assert client.post(url, {"name": "Yana", "capacity": 5, "base_price": "-5"}, format="json").status_code == 400
    assert len(client.get(url).data) == 2

    hall = VenueHall.objects.get(pk=res.data["id"])
    res = client.patch(f"{url}{hall.pk}/", {"is_active": False}, format="json")
    assert res.status_code == 200 and res.data["is_active"] is False
    other = venue.halls.exclude(pk=hall.pk).get()
    assert other.is_active  # deactivating one hall never touches another
    hall.soft_delete()
    assert client.patch(f"{url}{hall.pk}/", {"capacity": 9}, format="json").status_code == 404
    assert [h["id"] for h in client.get(url).data] == [str(other.pk)]


# ------------------------------------------------------ db constraints
@pytest.mark.django_db
@pytest.mark.parametrize(
    "fields",
    [
        {"capacity_min": 10, "capacity_max": 5},
        {"capacity_max": 0, "capacity_min": 0},
        {"base_price": Decimal("-1")},
        {"currency": "USD"},
        {"latitude": Decimal("95")},
        {"phone_number": "998901234567"},
        {"publication_status": "PUBLISHED"},
    ],
)
def test_venue_db_constraints(fields):
    data = {"name": "V", "address": "A", "region": "TASHKENT", "capacity_max": 100, "base_price": Decimal("1")}
    with pytest.raises(IntegrityError), transaction.atomic():
        Venue.objects.create(**{**data, **fields})


@pytest.mark.django_db
def test_hall_and_membership_db_constraints(venue_owner, make_venue, make_user):
    venue = make_venue(venue_owner)
    with pytest.raises(IntegrityError), transaction.atomic():
        VenueHall.objects.create(venue=venue, name=services.DEFAULT_HALL_NAME, capacity=5)
    with pytest.raises(IntegrityError), transaction.atomic():
        VenueHall.objects.create(venue=venue, name="Z", capacity=0)
    with pytest.raises(IntegrityError), transaction.atomic():
        VenueMembership.objects.create(venue=venue, user=venue_owner, role=MembershipRole.VIEWER)
    with pytest.raises(IntegrityError), transaction.atomic():
        VenueMembership.objects.create(venue=venue, user=make_user(Role.VENUE_OWNER), role="GOD")
    # a soft-deleted hall frees its name
    venue.halls.get().soft_delete()
    VenueHall.objects.create(venue=venue, name=services.DEFAULT_HALL_NAME, capacity=5)


# ------------------------------------------------------- memberships
@pytest.mark.django_db
def test_membership_services(venue_owner, make_venue, make_user):
    venue = make_venue(venue_owner)
    owner_membership = VenueMembership.objects.get(venue=venue, user=venue_owner)
    with pytest.raises(ValidationError):  # the last active OWNER cannot step down or be deactivated
        services.update_member(None, owner_membership, role=MembershipRole.MANAGER)
    with pytest.raises(ValidationError):
        services.update_member(None, owner_membership, is_active=False)
    for role in (Role.USER, Role.STUDIO, Role.ADMIN, Role.SUPER_ADMIN):
        with pytest.raises(ValidationError):
            services.add_member(None, venue, make_user(role), MembershipRole.VIEWER)

    partner = make_user(Role.VENUE_OWNER)
    services.add_member(None, venue, partner, MembershipRole.OWNER)
    services.update_member(None, owner_membership, role=MembershipRole.MANAGER)  # now allowed
    owner_membership.refresh_from_db()
    assert owner_membership.role == MembershipRole.MANAGER
    assert AuditLog.objects.filter(target_id=str(owner_membership.pk), action="UPDATE").exists()

    # re-adding a deactivated member re-activates the same row (unique venue+user)
    services.update_member(None, owner_membership, is_active=False)
    again = services.add_member(None, venue, venue_owner, MembershipRole.SCHEDULER)
    assert again.pk == owner_membership.pk and again.is_active and again.role == MembershipRole.SCHEDULER


@pytest.mark.django_db
def test_deactivated_account_loses_venue_access(venue_owner, make_venue):
    venue = make_venue(venue_owner)
    assert services.has_capability(venue_owner, venue, Capability.MANAGE_BOOKINGS)
    venue_owner.is_active = False
    venue_owner.save(update_fields=["is_active"])
    assert services.capabilities_for(venue_owner, venue) == frozenset()
    assert not services.venues_for(venue_owner).exists()


# ------------------------------------------------------- members API
@pytest.mark.django_db
def test_owner_manages_members_by_phone(venue_owner, make_venue, make_user, client_for):
    venue = make_venue(venue_owner)
    client = client_for(venue_owner)
    url = f"{BASE}{venue.pk}/members/"
    staff = make_user(Role.VENUE_OWNER)

    res = client.post(url, {"phone_number": staff.phone_number, "role": "SCHEDULER"}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["role"] == "SCHEDULER" and res.data["user"]["id"] == str(staff.pk)
    assert set(res.data["user"]) == {"id", "full_name", "phone_number"}  # no JSHSHIR / email / address
    again = client.post(url, {"phone_number": staff.phone_number, "role": "VIEWER"}, format="json")
    assert again.status_code == 400

    # unknown number, a non-venue account and an inactive account all get the same answer
    plain, inactive = make_user(Role.USER), make_user(Role.VENUE_OWNER, is_active=False)
    errors = {
        str(client.post(url, {"phone_number": phone, "role": "VIEWER"}, format="json").data["error"]["details"])
        for phone in ("+998939999999", plain.phone_number, inactive.phone_number)
    }
    assert len(errors) == 1 and services.MEMBER_NOT_FOUND in errors.pop()

    rows = client.get(url).data
    assert {r["user"]["id"] for r in rows} == {str(venue_owner.pk), str(staff.pk)}
    membership_id = res.data["id"]
    res = client.patch(f"{url}{membership_id}/", {"role": "MANAGER"}, format="json")
    assert res.status_code == 200 and res.data["role"] == "MANAGER"
    assert client_for(staff).patch(f"{BASE}{venue.pk}/", {"district": "X"}, format="json").status_code == 200
    res = client.patch(f"{url}{membership_id}/", {"is_active": False}, format="json")
    assert res.status_code == 200 and res.data["is_active"] is False
    assert client_for(staff).get(f"{BASE}{venue.pk}/").status_code == 404

    own = VenueMembership.objects.get(venue=venue, user=venue_owner)
    assert client.patch(f"{url}{own.pk}/", {"role": "VIEWER"}, format="json").status_code == 400  # last OWNER


@pytest.mark.django_db
@pytest.mark.parametrize("role", [MembershipRole.MANAGER, MembershipRole.SCHEDULER, MembershipRole.VIEWER])
def test_only_owners_manage_members(make_user, make_venue, client_for, role):
    venue = make_venue(make_user(Role.VENUE_OWNER))
    member = make_user(Role.VENUE_OWNER)
    target = _member(venue, make_user(Role.VENUE_OWNER), MembershipRole.VIEWER)
    _member(venue, member, role)
    client = client_for(member)
    url = f"{BASE}{venue.pk}/members/"
    assert client.get(url).status_code == 403
    newcomer = make_user(Role.VENUE_OWNER)
    assert client.post(url, {"phone_number": newcomer.phone_number, "role": "OWNER"}, format="json").status_code == 403
    assert client.patch(f"{url}{target.pk}/", {"role": "OWNER"}, format="json").status_code == 403
    target.refresh_from_db()
    assert target.role == MembershipRole.VIEWER


@pytest.mark.django_db
def test_member_of_another_venue_is_not_reachable(make_user, make_venue, client_for):
    owner_a, owner_b = make_user(Role.VENUE_OWNER), make_user(Role.VENUE_OWNER)
    venue_a, venue_b = make_venue(owner_a, name="A"), make_venue(owner_b, name="B")
    foreign = VenueMembership.objects.get(venue=venue_b)
    client = client_for(owner_a)
    assert (
        client.patch(f"{BASE}{venue_a.pk}/members/{foreign.pk}/", {"role": "VIEWER"}, format="json").status_code == 404
    )
    assert client.get(f"{BASE}{venue_b.pk}/members/").status_code == 404
