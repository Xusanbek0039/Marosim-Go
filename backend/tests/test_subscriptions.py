"""Subscriptions (manual payment, admin approval) and the logo / download rules that depend on them."""

import io
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from PIL import Image

from apps.accounts.models import Role
from apps.media import watermark, watermark_jobs
from apps.media.models import WatermarkStatus
from apps.subscriptions import services
from apps.subscriptions.models import Subscription, SubscriptionPlan

from .conftest import subscribe
from .test_ceremony_invitations import owner_invite, wedding, world  # noqa: F401
from .test_media_sharing import PHOTO, ViewDrive, drive, gallery, media_url, share_with_guest  # noqa: F401

PLANS = "/api/v1/subscriptions/plans/"
MINE = "/api/v1/me/subscriptions/"
ADMIN = "/api/v1/admin/subscriptions/"
ADMIN_PLANS = "/api/v1/admin/subscription-plans/"
SETTINGS = "/api/v1/admin/subscription-settings/"


def plan(code):
    return SubscriptionPlan.objects.get(code=code)


def admin_with(make_user, *codes):
    return make_user(Role.ADMIN, admin_permissions=list(codes))


# ------------------------------------------------------------------ plans
@pytest.mark.django_db
def test_seeded_plans_match_the_price_list(anon):
    res = anon.get(PLANS)
    assert res.status_code == 200
    got = [(p["code"], p["duration_months"], p["price"], p["max_viewers"]) for p in res.data]
    assert got == [
        ("M1", 1, "25000.00", 10),
        ("M3", 3, "60000.00", 20),
        ("Y1", 12, "100000.00", 30),
        ("Y5", 60, "300000.00", 50),
    ]


@pytest.mark.django_db
def test_prices_are_managed_only_with_the_plans_permission(make_user, super_admin, client_for, plain_user):
    url = f"{ADMIN_PLANS}{plan('M1').pk}/"
    viewer = admin_with(make_user, "subscriptions.view")
    assert client_for(viewer).get(ADMIN_PLANS).status_code == 200
    assert client_for(viewer).patch(url, {"price": "1"}).status_code == 403
    assert client_for(admin_with(make_user, "subscriptions.plans")).patch(url, {"price": "30000"}).status_code == 200
    # a running purchase keeps the price it was sold for
    sub = services.request_subscription(None, plain_user, plan("M3"))
    assert client_for(super_admin).patch(f"{ADMIN_PLANS}{plan('M3').pk}/", {"price": "70000"}).status_code == 200
    sub.refresh_from_db()
    assert sub.price == Decimal("60000.00") and plan("M1").price == Decimal("30000.00")
    created = client_for(super_admin).post(
        ADMIN_PLANS, {"code": "m6", "name": "6 oy", "duration_months": 6, "price": "80000", "max_viewers": 25}
    )
    assert created.status_code == 201 and created.data["code"] == "M6"


@pytest.mark.django_db
def test_payment_instructions(make_user, client_for, plain_user):
    editor = client_for(admin_with(make_user, "subscriptions.view", "subscriptions.plans"))
    res = editor.patch(SETTINGS, {"payment_instructions": "Karta: 8600 **** 1234, Ali V."}, format="json")
    assert res.status_code == 200
    assert client_for(admin_with(make_user, "subscriptions.view")).patch(SETTINGS, {}).status_code == 403
    status = client_for(plain_user).get(f"{MINE}status/").data
    assert status["payment_instructions"].startswith("Karta") and len(status["plans"]) == 4
    assert status["clean_access"] is False and status["viewer_limit"] == 5


# --------------------------------------------------------------- requests
@pytest.mark.django_db
def test_request_approve_and_renewal_stacks(make_user, client_for, plain_user):
    couple = client_for(plain_user)
    res = couple.post(MINE, {"plan": str(plan("M1").pk), "user_note": "Click, chek 123"})
    assert res.status_code == 201 and res.data["state"] == "PENDING"
    assert couple.post(MINE, {"plan": str(plan("Y1").pk)}).status_code == 400  # one pending at a time

    approver = client_for(admin_with(make_user, "subscriptions.view", "subscriptions.update"))
    ok = approver.post(f"{ADMIN}{res.data['id']}/approve/", {"payment_method": "CLICK", "payment_reference": "123"})
    assert ok.status_code == 200 and ok.data["state"] == "ACTIVE" and ok.data["paid_amount"] == "25000.00"
    first = Subscription.objects.get(pk=res.data["id"])
    assert services.has_clean_access(plain_user) and services.viewer_limit(plain_user) == 10

    # renewal before the end starts when the current period ends — no paid day is lost
    second = couple.post(MINE, {"plan": str(plan("M3").pk)})
    approver.post(f"{ADMIN}{second.data['id']}/approve/", {})
    renewal = Subscription.objects.get(pk=second.data["id"])
    assert renewal.starts_at == first.ends_at
    assert services.state_of(renewal) == "SCHEDULED"
    assert services.viewer_limit(plain_user) == 10  # the running one decides
    assert couple.get(f"{MINE}status/").data["paid_until"] is not None


@pytest.mark.django_db
def test_reject_cancel_and_expiry(make_user, client_for, plain_user, super_admin):
    couple = client_for(plain_user)
    req = couple.post(MINE, {"plan": str(plan("M1").pk)}).data
    assert (
        client_for(super_admin).post(f"{ADMIN}{req['id']}/reject/", {"admin_note": "To'lov topilmadi"}).data["state"]
        == "REJECTED"
    )
    req2 = couple.post(MINE, {"plan": str(plan("M1").pk)}).data
    assert couple.post(f"{MINE}{req2['id']}/cancel/").data["state"] == "CANCELLED"

    sub = subscribe(plain_user)
    assert services.has_clean_access(plain_user)
    Subscription.objects.filter(pk=sub.pk).update(ends_at=timezone.now() - timedelta(seconds=1))
    assert not services.has_clean_access(plain_user) and services.viewer_limit(plain_user) == 5
    assert couple.get(MINE).data[0]["state"] == "EXPIRED"


@pytest.mark.django_db
def test_admin_grants_and_revokes_and_sees_revenue(make_user, client_for, plain_user):
    seller = client_for(admin_with(make_user, "subscriptions.view", "subscriptions.create", "subscriptions.update"))
    res = seller.post(ADMIN, {"user_id": str(plain_user.pk), "plan": str(plan("Y5").pk), "payment_method": "CASH"})
    assert res.status_code == 201 and res.data["state"] == "ACTIVE" and res.data["max_viewers"] == 50
    assert services.viewer_limit(plain_user) == 50
    summary = seller.get(f"{ADMIN}summary/").data
    assert summary["active"] == 1 and Decimal(summary["revenue_total"]) == Decimal("300000")
    assert seller.get(ADMIN, {"state": "ACTIVE"}).data["count"] == 1
    revoked = seller.post(f"{ADMIN}{res.data['id']}/cancel/", {"admin_note": "Qaytarildi"})
    assert revoked.data["state"] == "CANCELLED" and not services.has_clean_access(plain_user)
    # only USER accounts can hold a subscription
    studio = make_user(Role.STUDIO)
    bad = seller.post(ADMIN, {"user_id": str(studio.pk), "plan": str(plan("M1").pk)})
    assert bad.status_code == 400


@pytest.mark.django_db
def test_admin_rights_come_only_from_granted_codes(make_user, client_for, plain_user):
    req = services.request_subscription(None, plain_user, plan("M1"))
    nobody = client_for(admin_with(make_user))
    assert nobody.get(ADMIN).status_code == 403
    looker = client_for(admin_with(make_user, "subscriptions.view"))
    assert looker.get(ADMIN).status_code == 200
    assert looker.post(f"{ADMIN}{req.pk}/approve/", {}).status_code == 403
    assert looker.post(ADMIN, {"user_id": str(plain_user.pk), "plan": str(plan("M1").pk)}).status_code == 403


@pytest.mark.django_db
def test_my_subscriptions_scope_is_own(make_user, client_for, plain_user):
    """Ownership: a couple sees and cancels only their own requests; admins see all with the code."""
    other = make_user(Role.USER)
    req = services.request_subscription(None, plain_user, plan("M1"))
    stranger = client_for(other)
    assert stranger.get(MINE).data == []
    assert stranger.post(f"{MINE}{req.pk}/cancel/").status_code == 404
    assert client_for(make_user(Role.STUDIO)).get(MINE).status_code == 403
    admin = client_for(admin_with(make_user, "subscriptions.view"))
    assert admin.get(f"{ADMIN}{req.pk}/").data["user"]["id"] == str(plain_user.pk)


# --------------------------------------------------- sharing limits / media
@pytest.mark.django_db
def test_viewer_limit_follows_the_subscription(wedding):
    bride = wedding["users"]["bride"]
    members = wedding["c"]["bride"].get(f"/api/v1/me/ceremonies/{wedding['ceremony'].pk}/members/").data
    assert members["viewer_limit"] == 5
    for i in range(5):
        assert owner_invite(wedding["c"]["bride"], wedding["ceremony"], f"+9989011100{i:02d}").status_code == 201
    assert owner_invite(wedding["c"]["bride"], wedding["ceremony"], "+998901110099").status_code == 400
    subscribe(bride, "M1")
    assert owner_invite(wedding["c"]["bride"], wedding["ceremony"], "+998901110099").status_code == 201


def _png(size=(800, 600)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 180, 160)).save(buf, format="PNG")
    return buf.getvalue()


class WatermarkDrive(ViewDrive):
    """ViewDrive with real preview images and the server-side copy operations."""

    def __init__(self):
        super().__init__()
        self.uploaded: dict[str, bytes] = {}

    def thumbnail(self, creds, file_id, size):
        self.thumb_calls += 1
        return (_png(), "image/png")

    def download_to_file(self, creds, file_id, path):
        path.write_bytes(self.blobs[file_id])
        return len(self.blobs[file_id])

    def upload_file(self, creds, *, name, parent_id, path, mime_type, app_properties):
        data = path.read_bytes()
        self.blobs["file-video-wm"] = data
        self.uploaded[name] = data
        return {"id": "file-video-wm", "size": str(len(data))}


@pytest.fixture
def wm_drive(drive, monkeypatch):
    from apps.storage import services as storage_services

    fake = WatermarkDrive()
    fake.__dict__.update({k: v for k, v in drive.__dict__.items() if k not in ("uploaded",)})
    storage_services.set_gateway(fake)
    monkeypatch.setattr(
        watermark, "burn_video", lambda src, dst, work, **kw: dst.write_bytes(b"LOGO" + src.read_bytes()[:50])
    )
    return fake


@pytest.mark.django_db
def test_without_subscription_everything_has_the_logo_and_nothing_downloads(gallery, wm_drive):
    w, c = gallery, gallery["ceremony"]
    wm_drive.blobs = {"file-photo": PHOTO, "file-video": PHOTO}
    bride = w["c"]["bride"]
    listed = bride.get(media_url(c)).data
    assert all(m["watermarked"] and not m["can_download"] for m in listed)
    video_row = next(m for m in listed if m["kind"] == "VIDEO")
    assert video_row["processing"] is True

    # photo: a stamped JPEG, never the original bytes
    photo = bride.get(media_url(c, w["photo"], "stream"), HTTP_ACCEPT="image/*")
    assert photo.status_code == 200 and photo["Content-Type"] == "image/jpeg" and photo.content != PHOTO
    thumb = bride.get(media_url(c, w["photo"], "thumbnail"), HTTP_ACCEPT="image/*")
    assert thumb["Content-Type"] == "image/jpeg"
    # video: 409 until the logo copy exists
    pending = bride.get(media_url(c, w["video"], "stream"))
    assert pending.status_code == 409 and pending.data["error"]["code"] == "watermark_pending"
    # download: owner without subscription → 403 subscription_required
    denied = bride.get(media_url(c, w["photo"], "download"))
    assert denied.status_code == 403 and denied.data["error"]["code"] == "subscription_required"


@pytest.mark.django_db
def test_watermark_job_and_who_gets_which_file(gallery, wm_drive):
    w, c = gallery, gallery["ceremony"]
    wm_drive.blobs = {"file-photo": PHOTO, "file-video": PHOTO}
    video = w["video"]
    video.wm_status = WatermarkStatus.PENDING
    video.drive_folder_id = "folder-1"
    video.save()
    assert watermark_jobs.drain() == 1
    video.refresh_from_db()
    assert video.wm_status == WatermarkStatus.READY and video.wm_drive_file_id == "file-video-wm"
    assert watermark_jobs.drain() == 0  # nothing left, READY is never redone

    share_with_guest(w)
    subscribe(w["users"]["bride"])
    # the guest of a subscribed owner still gets the logo copy and cannot download
    guest = w["c"]["guest"]
    stream = guest.get(media_url(c, video, "stream"))
    assert stream.status_code == 200 and b"".join(stream.streaming_content).startswith(b"LOGO")
    assert guest.get(media_url(c, video, "download")).status_code == 403
    # the subscribed owner gets the original and may download it
    bride = w["c"]["bride"]
    assert b"".join(bride.get(media_url(c, video, "stream")).streaming_content) == PHOTO
    dl = bride.get(media_url(c, video, "download"))
    assert dl.status_code == 200 and dl["Content-Disposition"].startswith("attachment;")


@pytest.mark.django_db
def test_failed_watermark_is_retried_then_given_up(gallery, wm_drive, monkeypatch):
    video = gallery["video"]
    video.wm_status = WatermarkStatus.PENDING
    video.save()

    def boom(src, dst, work, **kw):
        raise watermark.WatermarkError("ffmpeg_failed: test")

    monkeypatch.setattr(watermark, "burn_video", boom)
    monkeypatch.setattr(watermark_jobs, "RETRY_AFTER", timedelta(0))
    wm_drive.blobs = {"file-video": PHOTO}
    assert watermark_jobs.drain() == watermark_jobs.MAX_ATTEMPTS
    video.refresh_from_db()
    assert video.wm_status == WatermarkStatus.FAILED and video.wm_attempts == watermark_jobs.MAX_ATTEMPTS
    assert "ffmpeg_failed" in video.wm_error


@pytest.mark.django_db
def test_failed_watermark_waits_before_the_next_attempt(gallery, wm_drive, monkeypatch):
    video = gallery["video"]
    video.wm_status = WatermarkStatus.PENDING
    video.save()

    def boom(src, dst, work, **kw):
        raise watermark.WatermarkError("not_a_video")

    monkeypatch.setattr(watermark, "burn_video", boom)
    wm_drive.blobs = {"file-video": PHOTO}
    assert watermark_jobs.drain(limit=1) == 1
    video.refresh_from_db()
    assert video.wm_status == WatermarkStatus.FAILED and video.wm_attempts == 1
    assert not watermark_jobs._candidates().filter(pk=video.pk).exists()  # not retried back-to-back
    assert watermark_jobs.needs_work(type(video).objects.filter(pk=video.pk))
    type(video).objects.filter(pk=video.pk).update(wm_started_at=timezone.now() - watermark_jobs.RETRY_AFTER * 2)
    assert watermark_jobs._candidates().filter(pk=video.pk).exists()


def test_stamp_image_adds_the_logo_in_the_corner():
    out, mime = watermark.stamp_image(_png((1200, 800)))
    img = Image.open(io.BytesIO(out)).convert("RGB")
    assert mime == "image/jpeg" and img.size == (1200, 800)
    assert img.getpixel((10, 10)) == pytest.approx((200, 180, 160), abs=6)  # untouched corner
    corner = img.crop((900, 650, 1190, 790))
    assert len(set(corner.get_flattened_data())) > 20  # the logo is there


@pytest.mark.skipif(not watermark.ffmpeg_bin(), reason="ffmpeg not installed")
def test_burn_video_with_real_ffmpeg(tmp_path):
    import subprocess

    src = tmp_path / "in.mp4"
    subprocess.run(
        [watermark.ffmpeg_bin(), "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=640x360:d=1", str(src)],
        check=True,
    )
    dst = tmp_path / "out.mp4"
    watermark.burn_video(src, dst, tmp_path)
    assert dst.stat().st_size > 0
