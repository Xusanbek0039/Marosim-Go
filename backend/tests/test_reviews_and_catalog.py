"""Reviews / likes of venues and studios, the public studio catalog + schedule, studio portfolio and
panel control of venue schedules (user request 2026-11-09)."""

import datetime

import pytest

from apps.accounts.models import Role
from apps.ceremonies.models import Ceremony
from apps.reviews.models import Like, Review
from apps.studios.models import StudioImage, StudioMembership
from apps.studios.services import sync_owner_membership
from apps.venues import scheduling
from apps.venues.models import BookingStatus, HallBooking, HallSession

from .conftest import image_file
from .test_venue_bookings import make_venue, venue_owner  # noqa: F401 - fixtures

VENUES = "/api/v1/venues/"
STUDIOS = "/api/v1/public/studios/"
ADMIN_VENUES = "/api/v1/admin/venues/"
ADMIN_REVIEWS = "/api/v1/admin/reviews/"
ADMIN_STUDIOS = "/api/v1/studios/"


def in_days(n: int) -> datetime.date:
    return scheduling.today() + datetime.timedelta(days=n)


def admin_with(make_user, *codes):
    return make_user(Role.ADMIN, admin_permissions=list(codes))


@pytest.fixture
def studio(make_user, make_studio):
    owner = make_user(Role.STUDIO)
    s = make_studio(owner, phone_number="+998901112233")
    sync_owner_membership(s)
    return s


# ----------------------------------------------------------------- reviews
@pytest.mark.django_db
def test_user_reviews_and_likes_a_venue(make_user, client_for, anon, venue_owner, make_venue):
    venue = make_venue(venue_owner)
    a, b = make_user(Role.USER, first_name="Aziz", last_name="Karimov"), make_user(Role.USER)
    url = f"{VENUES}{venue.pk}/"

    assert client_for(a).put(f"{url}reviews/mine/", {"rating": 6}, format="json").status_code == 400
    res = client_for(a).put(f"{url}reviews/mine/", {"rating": 4, "text": " Zo'r "}, format="json")
    assert res.status_code == 200 and res.data["author_name"] == "Aziz K." and res.data["text"] == "Zo'r"
    # second PUT updates, never duplicates
    client_for(a).put(f"{url}reviews/mine/", {"rating": 5}, format="json")
    client_for(b).put(f"{url}reviews/mine/", {"rating": 3}, format="json")
    assert Review.objects.filter(venue=venue).count() == 2

    assert client_for(a).post(f"{url}like/").data == {"liked": True, "like_count": 1}
    assert client_for(a).post(f"{url}like/").data["like_count"] == 1  # idempotent

    page = client_for(a).get(f"{url}reviews/").data
    assert page["summary"]["rating_avg"] == 4.0 and page["summary"]["rating_count"] == 2
    assert page["summary"]["liked"] is True and page["summary"]["my_review"]["rating"] == 5
    assert anon.get(f"{url}reviews/").data["summary"]["liked"] is False
    # card stats on the public catalog and detail
    [card] = anon.get(VENUES).data
    assert card["stats"] == {"rating_avg": 4.0, "rating_count": 2, "like_count": 1}
    assert anon.get(url).data["venue"]["stats"]["like_count"] == 1

    assert client_for(a).delete(f"{url}like/").data == {"liked": False, "like_count": 0}


@pytest.mark.django_db
def test_only_customers_review_and_only_public_targets(make_user, client_for, anon, venue_owner, make_venue):
    hidden = make_venue(venue_owner, approved=False, name="Yopiq")
    user = make_user(Role.USER)
    assert client_for(user).put(f"{VENUES}{hidden.pk}/reviews/mine/", {"rating": 5}, format="json").status_code == 404
    assert anon.get(f"{VENUES}{hidden.pk}/reviews/").status_code == 404
    public = make_venue(venue_owner, name="Ochiq")
    for role in (Role.STUDIO, Role.VENUE_OWNER, Role.ADMIN):
        res = client_for(make_user(role)).put(f"{VENUES}{public.pk}/reviews/mine/", {"rating": 5}, format="json")
        assert res.status_code == 403
    assert anon.post(f"{VENUES}{public.pk}/like/").status_code == 401


@pytest.mark.django_db
def test_review_scope_is_own(make_user, client_for, venue_owner, make_venue, studio):
    """Ownership: deleting / editing "mine" never touches another account's review or like."""
    venue = make_venue(venue_owner)
    a, b = make_user(Role.USER), make_user(Role.USER)
    for target in (f"{VENUES}{venue.pk}/", f"{STUDIOS}{studio.pk}/"):
        client_for(a).put(f"{target}reviews/mine/", {"rating": 2}, format="json")
        client_for(a).post(f"{target}like/")
        assert client_for(b).delete(f"{target}reviews/mine/").status_code == 204
        assert client_for(b).delete(f"{target}like/").data["like_count"] == 1
        client_for(b).put(f"{target}reviews/mine/", {"rating": 5}, format="json")
    assert Review.objects.filter(author=a).count() == 2 and Like.objects.filter(user=a).count() == 2
    assert set(Review.objects.filter(author=a).values_list("rating", flat=True)) == {2}


@pytest.mark.django_db
def test_admin_review_moderation_needs_codes(make_user, client_for, anon, super_admin, venue_owner, make_venue):
    """Ownership: the panel sees every review (hidden too); actions need ``reviews.*`` codes."""
    venue = make_venue(venue_owner)
    client_for(make_user(Role.USER)).put(f"{VENUES}{venue.pk}/reviews/mine/", {"rating": 1, "text": "x"}, format="json")
    review = Review.objects.get()

    assert client_for(admin_with(make_user)).get(ADMIN_REVIEWS).status_code == 403
    viewer = client_for(admin_with(make_user, "reviews.view"))
    assert viewer.get(ADMIN_REVIEWS).data["count"] == 1
    assert viewer.patch(f"{ADMIN_REVIEWS}{review.pk}/", {"is_hidden": True}, format="json").status_code == 403

    moderator = client_for(admin_with(make_user, "reviews.view", "reviews.moderate"))
    res = moderator.patch(f"{ADMIN_REVIEWS}{review.pk}/", {"is_hidden": True, "rating": 5}, format="json")
    assert res.status_code == 200 and res.data["is_hidden"] is True and res.data["rating"] == 1
    page = anon.get(f"{VENUES}{venue.pk}/reviews/").data
    assert page["results"] == [] and page["summary"]["rating_count"] == 0
    assert client_for(super_admin).get(ADMIN_REVIEWS, {"is_hidden": "true", "kind": "venue"}).data["count"] == 1
    assert moderator.delete(f"{ADMIN_REVIEWS}{review.pk}/").status_code == 204
    assert not Review.objects.exists()


# ------------------------------------------------------------ studio catalog
@pytest.mark.django_db
def test_public_studio_profile_and_busy_days(anon, make_user, make_studio, studio):
    Ceremony.objects.create(studio=studio, title="Ali & Vali to'yi", event_date=in_days(3))
    Ceremony.objects.create(studio=studio, title="Boshqa", event_date=in_days(3))
    Ceremony.objects.create(studio=studio, title="Uzoq", event_date=in_days(100))
    inactive = make_studio(make_user(Role.STUDIO), name="Yopiq studiya", is_active=False)

    ids = [s["id"] for s in anon.get(STUDIOS).data]
    assert ids == [str(studio.pk)]
    assert anon.get(f"{STUDIOS}{inactive.pk}/").status_code == 404
    detail = anon.get(f"{STUDIOS}{studio.pk}/").data
    assert detail["phone_number"] == "+998901112233" and "responsible_user" not in detail

    res = anon.get(f"{STUDIOS}{studio.pk}/schedule/", {"from": in_days(0), "to": in_days(30)})
    assert res.status_code == 200 and res.data["busy"] == {in_days(3).isoformat(): 2}
    assert "Ali" not in str(res.data)
    assert anon.get(f"{STUDIOS}{studio.pk}/schedule/", {"from": in_days(0), "to": in_days(90)}).status_code == 400


@pytest.mark.django_db
def test_studio_portfolio_is_own_studio(make_user, make_studio, client_for, studio):
    """Ownership: a studio member manages only its own portfolio; UPLOADER may only look."""
    owner = studio.responsible_user
    other = make_studio(make_user(Role.STUDIO), name="Boshqa studiya")
    sync_owner_membership(other)
    url = f"/api/v1/studios/me/{studio.pk}/images/"

    res = client_for(owner).post(url, {"image": image_file()}, format="multipart")
    assert res.status_code == 201
    assert client_for(owner).get(url).data[0]["id"] == res.data["id"]
    assert client_for(owner).get(f"/api/v1/studios/me/{other.pk}/images/").status_code == 404
    assert client_for(other.responsible_user).delete(f"{url}{res.data['id']}/").status_code == 404

    uploader = make_user(Role.STUDIO)
    StudioMembership.objects.create(studio=studio, user=uploader, role=StudioMembership.Role.UPLOADER)
    assert client_for(uploader).get(url).status_code == 200
    assert client_for(uploader).post(url, {"image": image_file()}, format="multipart").status_code == 403
    assert client_for(owner).delete(f"{url}{res.data['id']}/").status_code == 204
    assert not StudioImage.objects.exists()


@pytest.mark.django_db
def test_panel_studio_calendar_and_portfolio(make_user, client_for, studio):
    Ceremony.objects.create(studio=studio, title="To'y", event_date=in_days(5))
    viewer = client_for(admin_with(make_user, "studios.view"))
    res = viewer.get(f"{ADMIN_STUDIOS}{studio.pk}/calendar/", {"from": in_days(0), "to": in_days(30)})
    assert res.status_code == 200 and [r["title"] for r in res.data] == ["To'y"]
    assert viewer.post(f"{ADMIN_STUDIOS}{studio.pk}/images/", {"image": image_file()}, format="multipart").status_code == 403
    editor = client_for(admin_with(make_user, "studios.view", "studios.update"))
    res = editor.post(f"{ADMIN_STUDIOS}{studio.pk}/images/", {"image": image_file()}, format="multipart")
    assert res.status_code == 201
    assert editor.get(f"{ADMIN_STUDIOS}{studio.pk}/").data["images"][0]["id"] == res.data["id"]
    assert editor.delete(f"{ADMIN_STUDIOS}{studio.pk}/images/{res.data['id']}/").status_code == 204


# ------------------------------------------------------- panel venue schedule
@pytest.mark.django_db
def test_panel_controls_every_venue_schedule(make_user, client_for, super_admin, venue_owner, make_venue):
    """Ownership: the panel sees every venue's calendar (venues.view); changes need venues.schedule."""
    venue = make_venue(venue_owner)
    session = HallSession.objects.get(hall__venue=venue, name="Kechki")
    couple = make_user(Role.USER)
    res = client_for(couple).post(
        "/api/v1/me/venue-bookings/", {"session": str(session.pk), "date": in_days(10)}, format="json"
    )
    booking_id = res.data["id"]
    url = f"{ADMIN_VENUES}{venue.pk}/"

    viewer = client_for(admin_with(make_user, "venues.view"))
    cal = viewer.get(f"{url}calendar/", {"from": in_days(0), "to": in_days(30)})
    assert cal.status_code == 200 and [b["id"] for b in cal.data["bookings"]] == [booking_id]
    assert viewer.get(f"{url}bookings/", {"status": "REQUESTED"}).data[0]["requester"]["id"] == str(couple.pk)
    assert viewer.get(f"{url}halls/{session.hall_id}/sessions/").status_code == 200
    assert viewer.post(f"{url}bookings/{booking_id}/confirm/").status_code == 403
    assert viewer.post(f"{url}bookings/", {"session": str(session.pk), "date": in_days(11)}, format="json").status_code == 403

    scheduler = client_for(admin_with(make_user, "venues.view", "venues.schedule"))
    res = scheduler.post(f"{url}bookings/{booking_id}/confirm/")
    assert res.status_code == 200 and res.data["status"] == BookingStatus.CONFIRMED
    res = scheduler.post(
        f"{url}bookings/", {"session": str(session.pk), "date": in_days(12), "status": "BLOCKED"}, format="json"
    )
    assert res.status_code == 201
    assert scheduler.post(f"{url}bookings/{res.data['id']}/cancel/").data["status"] == BookingStatus.CANCELLED
    res = scheduler.patch(f"{url}halls/{session.hall_id}/sessions/{session.pk}/", {"name": "Oqshom"}, format="json")
    assert res.status_code == 200 and res.data["name"] == "Oqshom"
    res = scheduler.post(
        f"{url}halls/{session.hall_id}/sessions/", {"name": "Tun", "starts_at": "23:30", "ends_at": "23:59"}, format="json"
    )
    assert res.status_code == 201
    assert HallBooking.objects.get(pk=booking_id).decided_by is not None
    assert client_for(super_admin).get(f"{url}calendar/", {"from": in_days(0), "to": in_days(30)}).status_code == 200
