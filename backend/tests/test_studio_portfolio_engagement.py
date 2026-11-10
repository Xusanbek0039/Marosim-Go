"""Studio portfolio reels, likes / dislikes / comments, customer ↔ studio chat (all galichka-only)
and the studio's own calendar (busy / day off) — user request 2026-11-10."""

import datetime
import shutil
import subprocess

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.accounts.models import Role
from apps.studios.models import PortfolioKind, StudioImage, StudioMembership
from apps.studios.services import sync_owner_membership
from apps.subscriptions.models import Subscription, SubscriptionPlan, SubscriptionStatus
from apps.subscriptions.services import add_months
from apps.venues import scheduling

from .conftest import image_file

PUBLIC = "/api/v1/public/studios/"


def me(studio) -> str:
    return f"/api/v1/studios/me/{studio.pk}/"


def give_badge(studio):
    plan = SubscriptionPlan.objects.get(code="STUDIO_M1")
    now = timezone.now()
    return Subscription.objects.create(
        user=studio.responsible_user,
        studio=studio,
        plan=plan,
        status=SubscriptionStatus.ACTIVE,
        price=plan.price,
        duration_months=plan.duration_months,
        max_viewers=plan.max_viewers,
        starts_at=now,
        ends_at=add_months(now, plan.duration_months),
        paid_amount=plan.price,
    )


def video_file(tmp_path, size="360x640", seconds=2) -> SimpleUploadedFile:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg / ffprobe kerak")
    out = tmp_path / f"reel-{size}.mp4"
    subprocess.run(  # noqa: S603
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color=c=blue:s={size}:d={seconds}",
         "-pix_fmt", "yuv420p", str(out)],
        check=True, timeout=60,
    )  # fmt: skip
    return SimpleUploadedFile("reel.mp4", out.read_bytes(), content_type="video/mp4")


@pytest.fixture
def studio(make_user, make_studio):
    s = make_studio(make_user(Role.STUDIO))
    sync_owner_membership(s)
    return s


@pytest.fixture
def photo(studio):
    return StudioImage.objects.create(studio=studio, image=image_file().name, position=0)


# ------------------------------------------------------------------- reels
@pytest.mark.django_db
def test_reels_need_galichka_and_vertical_video(client_for, anon, studio, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    owner = client_for(studio.responsible_user)
    url = f"{me(studio)}reels/"

    res = owner.post(url, {"video": video_file(tmp_path)}, format="multipart")
    assert res.status_code == 403 and res.data["error"]["code"] == "badge_required"

    give_badge(studio)
    res = owner.post(url, {"video": video_file(tmp_path, "640x360")}, format="multipart")
    assert res.status_code == 400 and "vertikal" in str(res.data)
    res = owner.post(url, {"video": video_file(tmp_path), "caption": " To'y kuni "}, format="multipart")
    assert res.status_code == 201, res.data
    assert res.data["kind"] == PortfolioKind.VIDEO and res.data["caption"] == "To'y kuni" and res.data["image"]
    assert res.data["duration"] == pytest.approx(2, abs=0.2)

    detail = anon.get(f"{PUBLIC}{studio.pk}/").data
    assert [r["id"] for r in detail["reels"]] == [res.data["id"]] and detail["images"] == []
    assert detail["chat_enabled"] is True

    # badge gone: reels are hidden from the public, but kept for the studio
    Subscription.objects.filter(studio=studio).update(ends_at=timezone.now())
    detail = anon.get(f"{PUBLIC}{studio.pk}/").data
    assert detail["reels"] == [] and detail["chat_enabled"] is False
    assert [i["id"] for i in owner.get(f"{me(studio)}images/").data] == [res.data["id"]]


@pytest.mark.django_db
def test_uploader_cannot_add_reels_or_edit_captions(make_user, make_studio, client_for, studio, photo):
    """Ownership: reels / captions only for the requester's own studio, and only OWNER / MANAGER."""
    give_badge(studio)
    other = make_studio(make_user(Role.STUDIO), name="Boshqa")
    sync_owner_membership(other)
    rogue = client_for(other.responsible_user)
    assert rogue.post(f"{me(studio)}reels/", {}, format="multipart").status_code == 404
    assert rogue.patch(f"{me(other)}images/{photo.pk}/", {"caption": "x"}, format="json").status_code == 404
    uploader = make_user(Role.STUDIO)
    StudioMembership.objects.create(studio=studio, user=uploader, role=StudioMembership.Role.UPLOADER)
    assert client_for(uploader).post(f"{me(studio)}reels/", {}, format="multipart").status_code == 403
    assert client_for(uploader).patch(f"{me(studio)}images/{photo.pk}/", {"caption": "x"}, format="json").status_code == 403
    res = client_for(studio.responsible_user).patch(f"{me(studio)}images/{photo.pk}/", {"caption": "Nikoh"}, format="json")
    assert res.status_code == 200 and res.data["caption"] == "Nikoh"


# --------------------------------------------------- reactions and comments
@pytest.mark.django_db
def test_reactions_and_comments(make_user, client_for, anon, studio, photo):
    """Ownership: a customer changes only their own reaction / comment; the studio moderates its own."""
    a, b = client_for(make_user(Role.USER)), client_for(make_user(Role.USER))
    item = f"{PUBLIC}{studio.pk}/portfolio/{photo.pk}/"

    res = a.put(f"{item}reaction/", {"value": "like"}, format="json")
    assert res.status_code == 403 and res.data["error"]["code"] == "badge_required"
    give_badge(studio)

    assert anon.put(f"{item}reaction/", {"value": "like"}, format="json").status_code == 401
    assert client_for(studio.responsible_user).put(f"{item}reaction/", {"value": "like"}, format="json").status_code == 403
    assert a.put(f"{item}reaction/", {"value": "like"}, format="json").data["like_count"] == 1
    res = b.put(f"{item}reaction/", {"value": "dislike"}, format="json")
    assert (res.data["like_count"], res.data["dislike_count"], res.data["my_reaction"]) == (1, 1, "dislike")
    res = a.put(f"{item}reaction/", {"value": "dislike"}, format="json")  # switch, never duplicate
    assert (res.data["like_count"], res.data["dislike_count"]) == (0, 2)
    assert a.delete(f"{item}reaction/").data["dislike_count"] == 1

    assert a.post(f"{item}comments/", {"text": "   "}, format="json").status_code == 400
    mine = a.post(f"{item}comments/", {"text": " Ajoyib! "}, format="json")
    assert mine.status_code == 201 and mine.data["text"] == "Ajoyib!" and mine.data["is_mine"] is True
    theirs = b.post(f"{item}comments/", {"text": "Narxi qancha?"}, format="json").data
    listed = anon.get(f"{item}comments/").data
    assert [c["text"] for c in listed] == ["Narxi qancha?", "Ajoyib!"] and "phone" not in str(listed)
    assert anon.get(f"{PUBLIC}{studio.pk}/").data["images"][0]["engagement"]["comment_count"] == 2

    assert a.delete(f"{item}comments/{theirs['id']}/").status_code == 404
    assert a.delete(f"{item}comments/{mine.data['id']}/").status_code == 204

    owner = client_for(studio.responsible_user)
    assert [c["id"] for c in owner.get(f"{me(studio)}images/{photo.pk}/comments/").data] == [theirs["id"]]
    assert owner.delete(f"{me(studio)}images/{photo.pk}/comments/{theirs['id']}/").status_code == 204
    assert anon.get(f"{item}comments/").data == []


@pytest.mark.django_db
def test_other_studio_cannot_moderate(make_user, make_studio, client_for, studio, photo):
    give_badge(studio)
    other = make_studio(make_user(Role.STUDIO), name="Boshqa")
    sync_owner_membership(other)
    comment = client_for(make_user(Role.USER)).post(
        f"{PUBLIC}{studio.pk}/portfolio/{photo.pk}/comments/", {"text": "Salom"}, format="json"
    ).data
    rogue = client_for(other.responsible_user)
    assert rogue.get(f"{me(studio)}images/{photo.pk}/comments/").status_code == 404
    assert rogue.delete(f"{me(other)}images/{photo.pk}/comments/{comment['id']}/").status_code == 404


# --------------------------------------------------------------------- chat
@pytest.mark.django_db
def test_chat_needs_galichka_and_is_private(make_user, make_studio, client_for, studio):
    """Ownership: customers see only their own conversations, studios only their own studio's."""
    alice, bob = make_user(Role.USER, first_name="Alisa", last_name="Karimova"), make_user(Role.USER)
    a = client_for(alice)
    thread = f"/api/v1/me/studio-chats/{studio.pk}/"

    res = a.post(thread, {"body": "Salom"}, format="json")
    assert res.status_code == 403 and res.data["error"]["code"] == "badge_required"
    assert a.get(thread).data == {
        "studio": {"is_verified": False, "id": str(studio.pk), "name": studio.name, "profile_picture": None},
        "can_write": False,
        "messages": [],
    }

    give_badge(studio)
    assert a.post(thread, {"body": " 12-dekabrga bo'shmisiz? "}, format="json").status_code == 201
    assert client_for(bob).get(thread).data["messages"] == []

    owner = client_for(studio.responsible_user)
    chats = owner.get(f"{me(studio)}chats/").data
    assert len(chats) == 1 and chats[0]["unread"] == 1 and chats[0]["customer"]["name"] == "Alisa Karimova"
    conversation = f"{me(studio)}chats/{chats[0]['id']}/"
    data = owner.get(conversation).data
    assert data["can_write"] is True and [m["body"] for m in data["messages"]] == ["12-dekabrga bo'shmisiz?"]
    assert owner.get(f"{me(studio)}chats/").data[0]["unread"] == 0
    assert owner.post(conversation, {"body": "Ha, bo'shmiz"}, format="json").status_code == 201

    mine = a.get("/api/v1/me/studio-chats/").data
    assert mine[0]["unread"] == 1 and mine[0]["last_message"]["from_studio"] is True
    assert "phone" not in str(chats) and "pinfl" not in str(chats)

    uploader = make_user(Role.STUDIO)
    StudioMembership.objects.create(studio=studio, user=uploader, role=StudioMembership.Role.UPLOADER)
    assert client_for(uploader).get(conversation).data["can_write"] is False
    assert client_for(uploader).post(conversation, {"body": "x"}, format="json").status_code == 403

    other = make_studio(make_user(Role.STUDIO), name="Boshqa")
    sync_owner_membership(other)
    assert client_for(other.responsible_user).get(conversation).status_code == 404
    assert client_for(other.responsible_user).get(f"{me(other)}chats/{chats[0]['id']}/").status_code == 404


# ----------------------------------------------------------------- schedule
@pytest.mark.django_db
def test_studio_marks_busy_and_off_days(make_user, make_studio, client_for, anon, studio):
    """Ownership: a studio edits only its own calendar; UPLOADER may only look."""
    owner = client_for(studio.responsible_user)
    other = make_studio(make_user(Role.STUDIO), name="Boshqa")
    sync_owner_membership(other)
    day = scheduling.today() + datetime.timedelta(days=4)
    off = day + datetime.timedelta(days=1)
    url = f"{me(studio)}schedule/"

    assert owner.put(f"{url}days/{day}/", {"status": "BUSY", "note": "Xorazmda to'y"}, format="json").status_code == 204
    assert owner.put(f"{url}days/{off}/", {"status": "OFF"}, format="json").status_code == 204
    assert owner.put(f"{url}days/not-a-date/", {"status": "OFF"}, format="json").status_code == 400
    assert owner.patch(url, {"off_weekdays": [6, 6, 0]}, format="json").data == {"off_weekdays": [0, 6]}
    assert owner.patch(url, {"off_weekdays": [7]}, format="json").status_code == 400

    panel = owner.get(url, {"from": day, "to": off}).data
    assert panel["days"] == {day.isoformat(): "BUSY", off.isoformat(): "OFF"}
    assert panel["notes"] == {day.isoformat(): "Xorazmda to'y"}

    public = anon.get(f"{PUBLIC}{studio.pk}/schedule/", {"from": day, "to": off}).data
    assert public["days"] == panel["days"] and public["off_weekdays"] == [0, 6]
    assert "notes" not in public and "Xorazm" not in str(public)

    assert owner.put(f"{url}days/{day}/", {"status": None}, format="json").status_code == 204
    assert owner.get(url, {"from": day, "to": off}).data["days"] == {off.isoformat(): "OFF"}

    uploader = make_user(Role.STUDIO)
    StudioMembership.objects.create(studio=studio, user=uploader, role=StudioMembership.Role.UPLOADER)
    assert client_for(uploader).get(url, {"from": day, "to": off}).status_code == 200
    assert client_for(uploader).put(f"{url}days/{day}/", {"status": "OFF"}, format="json").status_code == 403
    assert client_for(other.responsible_user).get(url, {"from": day, "to": off}).status_code == 404
    assert client_for(other.responsible_user).patch(url, {"off_weekdays": [1]}, format="json").status_code == 404
