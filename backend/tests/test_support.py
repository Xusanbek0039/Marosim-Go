"""Help tickets: one shared staff queue; admins write to the Super Admin; full history for the Super Admin."""

import pytest

from apps.accounts.models import Role
from apps.studios.services import sync_owner_membership
from apps.support.models import SupportTicket, TicketAudience, TicketStatus

from .test_venue_bookings import make_venue  # noqa: F401 — fixture

MINE = "/api/v1/support/tickets/"
STAFF = "/api/v1/admin/support/tickets/"


def write(client, subject="Video ochilmayapti", body="Galereyada video 10 daqiqadan beri tayyorlanmoqda"):
    return client.post(MINE, {"subject": subject, "body": body}, format="json")


@pytest.fixture
def people(make_user, make_studio, make_venue, client_for):  # noqa: F811
    studio_owner = make_user(Role.STUDIO)
    studio = make_studio(studio_owner)
    sync_owner_membership(studio)
    venue_owner = make_user(Role.VENUE_OWNER)
    venue = make_venue(venue_owner)
    admin = make_user(Role.ADMIN, admin_permissions=["support.view"], first_name="Javobchi")
    monitor = make_user(Role.ADMIN, admin_permissions=["support.view", "support.monitor"])
    writer_admin = make_user(Role.ADMIN, admin_permissions=[])
    return {
        "studio": studio,
        "venue": venue,
        "user": client_for(make_user(Role.USER)),
        "studio_owner": client_for(studio_owner),
        "venue_owner": client_for(venue_owner),
        "admin": client_for(admin),
        "monitor": client_for(monitor),
        "writer_admin": client_for(writer_admin),
        "no_perms": client_for(make_user(Role.ADMIN, admin_permissions=[])),
        "super": client_for(make_user(Role.SUPER_ADMIN)),
    }


@pytest.mark.django_db
def test_tickets_record_where_they_came_from(people):
    res = write(people["studio_owner"])
    assert res.status_code == 201, res.data
    assert res.data["audience"] == "STAFF" and res.data["status"] == "OPEN"
    assert res.data["studio"]["name"] == people["studio"].name and res.data["venue"] is None
    assert res.data["messages"][0]["is_mine"] and res.data["can_reply"]

    res = write(people["venue_owner"])
    assert res.data["venue"]["name"] == people["venue"].name and res.data["studio"] is None
    assert write(people["user"]).data["author_role"] == "USER"
    assert write(people["super"]).status_code == 403  # the Super Admin has no one above


@pytest.mark.django_db
def test_admin_with_support_view_answers_client_tickets(people):
    tid = write(people["studio_owner"]).data["id"]
    assert people["no_perms"].get(STAFF).status_code == 403
    assert people["admin"].get(STAFF).data["count"] == 1
    assert people["admin"].get(STAFF, {"author_role": "STUDIO"}).data["count"] == 1
    assert people["admin"].get(STAFF, {"studio": str(people["studio"].pk)}).data["count"] == 1
    assert people["admin"].get(f"{STAFF}summary/").data == {"open": 1, "answered": 0, "closed": 0}

    res = people["admin"].post(f"{STAFF}{tid}/messages/", {"body": "Tekshirdik, endi ochiladi."}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["status"] == "ANSWERED" and res.data["handled_by_name"].startswith("Javobchi")
    assert res.data["messages"][-1]["author_name"].startswith("Javobchi")  # staff see who answered

    mine = people["studio_owner"].get(f"{MINE}{tid}/").data
    assert mine["messages"][-1]["author_name"] == "MarosimGo yordam xizmati"  # authors see the team
    assert mine["handled_by_name"] == "MarosimGo yordam xizmati"
    assert people["studio_owner"].get(f"{MINE}summary/").data["answered"] == 1


@pytest.mark.django_db
def test_admin_tickets_go_to_super_admin_only(people):
    res = write(people["writer_admin"], subject="Ruxsat kerak")
    assert res.status_code == 201 and res.data["audience"] == "SUPER_ADMIN"
    tid = res.data["id"]

    assert people["admin"].get(STAFF).data["count"] == 0  # support.view: client tickets only
    assert people["admin"].get(f"{STAFF}{tid}/").status_code == 404
    seen = people["monitor"].get(f"{STAFF}{tid}/")
    assert seen.status_code == 200 and seen.data["can_reply"] is False  # monitor reads, never answers
    assert people["monitor"].post(f"{STAFF}{tid}/messages/", {"body": "x"}, format="json").status_code == 403

    res = people["super"].post(f"{STAFF}{tid}/messages/", {"body": "Berildi"}, format="json")
    assert res.status_code == 201 and res.data["status"] == "ANSWERED"
    assert people["super"].get(STAFF, {"audience": "SUPER_ADMIN"}).data["count"] == 1
    assert people["super"].get(f"{STAFF}summary/").data["answered"] == 1


@pytest.mark.django_db
def test_authors_see_only_their_own_tickets_and_can_close_and_reopen(people):
    tid = write(people["user"]).data["id"]
    assert people["studio_owner"].get(f"{MINE}{tid}/").status_code == 404
    assert people["studio_owner"].get(MINE).data["count"] == 0
    assert people["user"].get(MINE).data["count"] == 1

    res = people["user"].post(f"{MINE}{tid}/close/")
    assert res.status_code == 200 and res.data["status"] == "CLOSED" and res.data["closed_at"]
    assert people["admin"].post(f"{STAFF}{tid}/messages/", {"body": "x"}, format="json").status_code == 409

    res = people["user"].post(f"{MINE}{tid}/messages/", {"body": "Yana takrorlandi"}, format="json")
    assert res.status_code == 201 and res.data["status"] == "OPEN" and res.data["message_count"] == 2
    ticket = SupportTicket.objects.get()
    assert ticket.status == TicketStatus.OPEN and ticket.closed_at is None


@pytest.mark.django_db
def test_staff_close_and_search(people):
    tid = write(people["venue_owner"], subject="Zal narxi").data["id"]
    write(people["user"], subject="Parol")
    assert people["admin"].get(STAFF, {"search": "Zal"}).data["count"] == 1
    assert people["admin"].get(STAFF, {"search": people["venue"].name}).data["count"] == 1
    res = people["admin"].post(f"{STAFF}{tid}/close/")
    assert res.status_code == 200 and res.data["status"] == "CLOSED" and res.data["closed_by_name"]
    assert people["admin"].get(STAFF, {"status": "CLOSED"}).data["count"] == 1
    assert SupportTicket.objects.filter(audience=TicketAudience.STAFF).count() == 2
