"""Hall sessions, public date search and bookings (user request → venue confirms)."""

import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import Role
from apps.venues import scheduling, services
from apps.venues.models import (
    BookingSource,
    BookingStatus,
    HallBooking,
    HallSession,
    MembershipRole,
    PublicationStatus,
    VenueMembership,
)

from .test_venues import VENUE_DATA

SEARCH = "/api/v1/venues/search/"
MINE = "/api/v1/me/venue-bookings/"
OWNER = "/api/v1/venue-owner/venues/"


def in_days(n: int) -> datetime.date:
    return scheduling.today() + datetime.timedelta(days=n)


@pytest.fixture
def venue_owner(make_user):
    return make_user(Role.VENUE_OWNER)


@pytest.fixture
def make_venue(db):
    def factory(owner, approved=True, **extra):
        data = {**VENUE_DATA, "base_price": Decimal(VENUE_DATA["base_price"]), **extra}
        data.setdefault("name", f"Venue {owner.pk.hex[:6]}")
        venue = services.create_venue(None, owner, **data)
        if approved:
            venue.publication_status = PublicationStatus.APPROVED
            venue.save(update_fields=["publication_status"])
        return venue

    return factory


def hall_of(venue):
    return venue.halls.get()


def session_named(venue, name="Kechki"):
    return HallSession.objects.get(hall__venue=venue, name=name)


# --------------------------------------------------------------- sessions
@pytest.mark.django_db
def test_new_halls_get_three_default_sessions(venue_owner, make_venue, client_for):
    venue = make_venue(venue_owner)
    names = list(HallSession.objects.filter(hall__venue=venue).values_list("name", flat=True))
    assert names == ["Nahor", "Kunduzgi", "Kechki"]
    res = client_for(venue_owner).post(f"{OWNER}{venue.pk}/halls/", {"name": "Kichik zal", "capacity": 80})
    assert res.status_code == 201
    assert HallSession.objects.filter(hall_id=res.data["id"]).count() == 3


@pytest.mark.django_db
def test_sessions_of_one_hall_cannot_overlap(venue_owner, make_venue, client_for):
    venue = make_venue(venue_owner)
    url = f"{OWNER}{venue.pk}/halls/{hall_of(venue).pk}/sessions/"
    client = client_for(venue_owner)
    clash = client.post(url, {"name": "Tushlik", "starts_at": "09:00", "ends_at": "11:00"})
    assert clash.status_code == 400
    ok = client.post(url, {"name": "Tushlik", "starts_at": "10:00", "ends_at": "12:00"})
    assert ok.status_code == 201
    bad = client.patch(f"{url}{ok.data['id']}/", {"ends_at": "09:00"})
    assert bad.status_code == 400


@pytest.mark.django_db
def test_scheduler_manages_sessions_viewer_cannot(venue_owner, make_venue, make_user, client_for):
    venue = make_venue(venue_owner)
    scheduler, viewer = make_user(Role.VENUE_OWNER), make_user(Role.VENUE_OWNER)
    VenueMembership.objects.create(venue=venue, user=scheduler, role=MembershipRole.SCHEDULER)
    VenueMembership.objects.create(venue=venue, user=viewer, role=MembershipRole.VIEWER)
    url = f"{OWNER}{venue.pk}/halls/{hall_of(venue).pk}/sessions/"
    body = {"name": "Tun", "starts_at": "23:00", "ends_at": "23:59"}
    assert client_for(viewer).post(url, body).status_code == 403
    assert client_for(scheduler).post(url, body).status_code == 201
    assert client_for(viewer).get(url).status_code == 200


# ----------------------------------------------------------------- search
@pytest.mark.django_db
def test_search_shows_only_approved_venues_with_a_free_slot(venue_owner, make_venue, anon):
    open_venue = make_venue(venue_owner, name="Ochiq")
    make_venue(venue_owner, name="Yopiq", approved=False)
    blocked = make_venue(venue_owner, name="Bloklangan")
    blocked.is_active = False
    blocked.save()
    full = make_venue(venue_owner, name="To'la")
    day = in_days(12)
    for session in HallSession.objects.filter(hall__venue=full):
        scheduling.venue_create_entry(None, session, day, status=BookingStatus.BLOCKED)

    res = anon.get(SEARCH, {"date": day.isoformat()})
    assert res.status_code == 200
    assert [row["venue"]["name"] for row in res.data] == ["Ochiq"]
    assert res.data[0]["free_slots"] == 3
    assert open_venue.name == "Ochiq"


@pytest.mark.django_db
def test_search_marks_taken_session_and_never_leaks_customer(venue_owner, make_venue, make_user, anon):
    venue = make_venue(venue_owner)
    day = in_days(5)
    scheduling.venue_create_entry(
        None,
        session_named(venue),
        day,
        status=BookingStatus.CONFIRMED,
        contact_name="Maxfiy Mijoz",
        contact_phone="+998901112233",
    )
    res = anon.get(SEARCH, {"date": day.isoformat()})
    slots = {s["name"]: s["is_free"] for s in res.data[0]["halls"][0]["slots"]}
    assert slots == {"Nahor": True, "Kunduzgi": True, "Kechki": False}
    assert "Maxfiy" not in str(res.data) and "998901112233" not in str(res.data)


@pytest.mark.django_db
def test_search_filters_by_guests_region_and_rejects_bad_date(venue_owner, make_venue, anon):
    make_venue(venue_owner, name="Katta", capacity_max=600)
    make_venue(venue_owner, name="Samarqand", region="SAMARKAND", capacity_max=900)
    day = in_days(3).isoformat()
    assert [r["venue"]["name"] for r in anon.get(SEARCH, {"date": day, "guests": 800}).data] == ["Samarqand"]
    assert [r["venue"]["name"] for r in anon.get(SEARCH, {"date": day, "region": "TASHKENT_CITY"}).data] == ["Katta"]
    assert anon.get(SEARCH, {"date": "20-noyabr"}).status_code == 400
    assert anon.get(SEARCH, {"date": in_days(-1).isoformat()}).data == []


@pytest.mark.django_db
def test_public_detail_and_availability(venue_owner, make_venue, anon):
    venue = make_venue(venue_owner)
    hidden = make_venue(venue_owner, approved=False)
    assert anon.get(f"/api/v1/venues/{hidden.pk}/").status_code == 404
    detail = anon.get(f"/api/v1/venues/{venue.pk}/")
    assert detail.status_code == 200
    assert len(detail.data["halls"][0]["sessions"]) == 3
    day = in_days(2)
    taken = session_named(venue)
    scheduling.venue_create_entry(None, taken, day, status=BookingStatus.BLOCKED)
    res = anon.get(f"/api/v1/venues/{venue.pk}/availability/", {"from": day.isoformat(), "to": in_days(3).isoformat()})
    free = res.data["free"][str(hall_of(venue).pk)]
    assert str(taken.pk) not in free[day.isoformat()]
    assert len(free[in_days(3).isoformat()]) == 3
    too_wide = anon.get(f"/api/v1/venues/{venue.pk}/availability/", {"from": day, "to": in_days(100)})
    assert too_wide.status_code == 400


# --------------------------------------------------------------- bookings
@pytest.mark.django_db
def test_full_flow_request_confirm_auto_rejects_rivals(venue_owner, make_venue, make_user, client_for, anon):
    venue = make_venue(venue_owner)
    session, day = session_named(venue), in_days(12)
    couple_a, couple_b = make_user(Role.USER), make_user(Role.USER)
    body = {"session": str(session.pk), "date": day.isoformat(), "event_type": "WEDDING", "guest_count": 300}

    a = client_for(couple_a).post(MINE, body)
    b = client_for(couple_b).post(MINE, body)
    assert a.status_code == 201 and b.status_code == 201
    assert a.data["status"] == "REQUESTED" and a.data["quoted_price"] == "45000000.00"
    # a request does not take the slot
    slots = anon.get(SEARCH, {"date": day.isoformat()}).data[0]["halls"][0]["slots"]
    assert all(s["is_free"] for s in slots)
    # the venue sees both requests with the couple's contact
    pending = client_for(venue_owner).get(f"{OWNER}{venue.pk}/bookings/", {"status": "REQUESTED"}).data
    assert {p["requester"]["id"] for p in pending} == {str(couple_a.pk), str(couple_b.pk)}

    ok = client_for(venue_owner).post(f"{OWNER}{venue.pk}/bookings/{a.data['id']}/confirm/")
    assert ok.status_code == 200 and ok.data["status"] == "CONFIRMED"
    assert HallBooking.objects.get(pk=b.data["id"]).status == BookingStatus.REJECTED
    slots = anon.get(SEARCH, {"date": day.isoformat()}).data[0]["halls"][0]["slots"]
    assert [s["is_free"] for s in slots] == [True, True, False]
    # now the slot is taken for new requests
    late = client_for(make_user(Role.USER)).post(MINE, body)
    assert late.status_code == 409
    # the couple sees their booking but never the venue's internal note
    mine = client_for(couple_a).get(MINE).data
    assert mine[0]["status"] == "CONFIRMED" and "venue_note" not in mine[0]


@pytest.mark.django_db
def test_request_validation(venue_owner, make_venue, make_user, client_for):
    venue = make_venue(venue_owner)
    hidden = make_venue(venue_owner, approved=False)
    couple = client_for(make_user(Role.USER))
    session = session_named(venue)
    past = couple.post(MINE, {"session": str(session.pk), "date": in_days(-1).isoformat()})
    assert past.status_code == 400
    too_many = couple.post(MINE, {"session": str(session.pk), "date": in_days(4).isoformat(), "guest_count": 5000})
    assert too_many.status_code == 400
    private = couple.post(MINE, {"session": str(session_named(hidden).pk), "date": in_days(4).isoformat()})
    assert private.status_code == 400
    first = couple.post(MINE, {"session": str(session.pk), "date": in_days(4).isoformat()})
    again = couple.post(MINE, {"session": str(session.pk), "date": in_days(4).isoformat()})
    assert first.status_code == 201 and again.status_code == 400


@pytest.mark.django_db
def test_double_booking_is_rejected_by_service_and_database(venue_owner, make_venue, client_for):
    venue = make_venue(venue_owner)
    session, day = session_named(venue), in_days(30)
    client = client_for(venue_owner)
    url = f"{OWNER}{venue.pk}/bookings/"
    first = client.post(url, {"session": str(session.pk), "date": day.isoformat(), "contact_name": "Aliyevlar"})
    assert first.status_code == 201 and first.data["status"] == "CONFIRMED"
    second = client.post(url, {"session": str(session.pk), "date": day.isoformat(), "status": "BLOCKED"})
    assert second.status_code == 409
    with pytest.raises(IntegrityError), transaction.atomic():  # the DB guard, even without the service check
        HallBooking.objects.create(
            hall=session.hall, session=session, date=day, status=BookingStatus.BLOCKED, source=BookingSource.VENUE
        )
    # cancelling frees the slot again
    assert client.post(f"{url}{first.data['id']}/cancel/").data["status"] == "CANCELLED"
    assert client.post(url, {"session": str(session.pk), "date": day.isoformat()}).status_code == 201


@pytest.mark.django_db
def test_confirm_on_a_taken_slot_is_409(venue_owner, make_venue, make_user, client_for):
    venue = make_venue(venue_owner)
    session, day = session_named(venue), in_days(9)
    req = client_for(make_user(Role.USER)).post(MINE, {"session": str(session.pk), "date": day.isoformat()})
    scheduling.venue_create_entry(None, session, day, status=BookingStatus.BLOCKED)
    # the BLOCKED entry was not a CONFIRMED event, so the request is still pending
    assert HallBooking.objects.get(pk=req.data["id"]).status == BookingStatus.REQUESTED
    res = client_for(venue_owner).post(f"{OWNER}{venue.pk}/bookings/{req.data['id']}/confirm/")
    assert res.status_code == 409


@pytest.mark.django_db
def test_booking_capabilities(venue_owner, make_venue, make_user, client_for):
    venue = make_venue(venue_owner)
    scheduler = make_user(Role.VENUE_OWNER)
    VenueMembership.objects.create(venue=venue, user=scheduler, role=MembershipRole.SCHEDULER)
    session, day = session_named(venue), in_days(6)
    url = f"{OWNER}{venue.pk}/bookings/"
    client = client_for(scheduler)
    assert client.post(url, {"session": str(session.pk), "date": day.isoformat()}).status_code == 403
    blocked = client.post(url, {"session": str(session.pk), "date": day.isoformat(), "status": "BLOCKED"})
    assert blocked.status_code == 201
    req = client_for(make_user(Role.USER)).post(
        MINE, {"session": str(session_named(venue, "Nahor").pk), "date": day.isoformat()}
    )
    assert client.post(f"{url}{req.data['id']}/confirm/").status_code == 403
    assert client.post(f"{url}{blocked.data['id']}/cancel/").status_code == 200
    # an admin-blocked venue is read-only for its members
    venue.is_active = False
    venue.save()
    assert client_for(venue_owner).post(f"{url}{req.data['id']}/confirm/").status_code == 403


@pytest.mark.django_db
def test_owner_calendar_lists_open_entries_of_range(venue_owner, make_venue, make_user, client_for):
    venue = make_venue(venue_owner)
    day = in_days(3)
    scheduling.venue_create_entry(None, session_named(venue), day, status=BookingStatus.CONFIRMED, event_type="NAHOR")
    req = client_for(make_user(Role.USER)).post(
        MINE, {"session": str(session_named(venue, "Kunduzgi").pk), "date": day.isoformat()}
    )
    client_for(make_user(Role.USER)).post(MINE, {"session": str(session_named(venue, "Nahor").pk), "date": in_days(90)})
    client_for(venue_owner).post(f"{OWNER}{venue.pk}/bookings/{req.data['id']}/reject/", {"venue_note": "Band"})
    res = client_for(venue_owner).get(f"{OWNER}{venue.pk}/calendar/", {"from": day, "to": in_days(10)})
    assert res.status_code == 200
    assert [b["status"] for b in res.data["bookings"]] == ["CONFIRMED"]
    assert [s["name"] for s in res.data["halls"][0]["sessions"]] == ["Nahor", "Kunduzgi", "Kechki"]


@pytest.mark.django_db
def test_booking_scope_is_own(venue_owner, make_venue, make_user, client_for):
    """Ownership: a couple sees only their bookings; a venue only bookings of its own halls."""
    venue = make_venue(venue_owner)
    other_owner = make_user(Role.VENUE_OWNER)
    other_venue = make_venue(other_owner)
    couple, stranger = make_user(Role.USER), make_user(Role.USER)
    booking = client_for(couple).post(MINE, {"session": str(session_named(venue).pk), "date": in_days(8)}).data
    assert client_for(stranger).get(f"{MINE}{booking['id']}/").status_code == 404
    assert client_for(stranger).post(f"{MINE}{booking['id']}/cancel/").status_code == 404
    assert client_for(stranger).get(MINE).data == []
    # another venue cannot touch it, not even via its own venue id
    other = client_for(other_owner)
    assert other.post(f"{OWNER}{other_venue.pk}/bookings/{booking['id']}/confirm/").status_code == 404
    assert other.post(f"{OWNER}{venue.pk}/bookings/{booking['id']}/confirm/").status_code == 404
    assert other.get(f"{OWNER}{venue.pk}/calendar/", {"from": in_days(0), "to": in_days(9)}).status_code == 404
    hall = hall_of(venue)
    assert other.get(f"{OWNER}{other_venue.pk}/halls/{hall.pk}/sessions/").status_code == 404
    # the couple cancels their own request
    assert client_for(couple).post(f"{MINE}{booking['id']}/cancel/").data["status"] == "CANCELLED"
    # studios / venue accounts cannot request bookings
    res = client_for(venue_owner).post(MINE, {"session": str(session_named(venue).pk), "date": in_days(8)})
    assert res.status_code == 403
