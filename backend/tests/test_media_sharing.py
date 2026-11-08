"""Owner sharing (time-limited, max 5 per owner) and the couple / guest media endpoints.

User decisions 2026-11-07: each owner shares with up to 5 people by phone or JSHSHIR, the
recipient must accept, access lasts 24 hours / 3 days / 1 week / 1 month, viewers can only watch.
"""

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.audit.models import AuditAction, AuditLog
from apps.ceremonies.models import (
    CeremonyInvitation,
    CeremonyOwnership,
    CeremonyViewerAccess,
    OwnershipStatus,
    OwnerType,
    ViewerStatus,
)
from apps.media.models import CeremonyMedia, MediaKind, MediaStatus
from apps.storage import services as storage_services
from apps.storage import vault
from apps.storage.google import MediaStream
from apps.storage.models import ConnectionStatus, StorageCredential

from .conftest import subscribe

# ``world`` / ``wedding`` are pytest fixtures: imported so this module can use them.
from .test_ceremony_invitations import INV, MY, answer, owner_invite, wedding, world  # noqa: F401
from .test_media_upload import FakeDrive

PHOTO = b"\xff\xd8\xff" + bytes(range(256)) * 40  # 10 243 bytes of "jpeg"


class ViewDrive(FakeDrive):
    """FakeDrive plus the read side: byte ranges and thumbnails."""

    def __init__(self):
        super().__init__()
        self.blobs: dict[str, bytes] = {}
        self.ranges: list[str | None] = []
        self.thumb_calls = 0

    def open_media(self, creds, file_id, byte_range=None):
        self.ranges.append(byte_range)
        data = self.blobs[file_id]
        if not byte_range:
            return MediaStream(200, {"Content-Length": str(len(data))}, iter([data]), lambda: None)
        start, _, end = byte_range.removeprefix("bytes=").partition("-")
        if start == "":
            start, end = len(data) - int(end), len(data) - 1
        start, end = int(start), int(end) if end else len(data) - 1
        if start >= len(data):
            return MediaStream(416, {}, iter([]), lambda: None)
        part = data[start : end + 1]
        headers = {"Content-Length": str(len(part)), "Content-Range": f"bytes {start}-{end}/{len(data)}"}
        return MediaStream(206, headers, iter([part]), lambda: None)

    def thumbnail(self, creds, file_id, size):
        self.thumb_calls += 1
        return (b"\x89PNG-thumb-%d" % size, "image/png")


@pytest.fixture
def drive(db):
    fake = ViewDrive()
    storage_services.set_gateway(fake)
    conn = storage_services.connection()
    conn.account_email, conn.status = "owner@gmail.com", ConnectionStatus.CONNECTED
    conn.save()
    StorageCredential.objects.create(connection=conn, refresh_token_encrypted=vault.seal("1//refresh"))
    cache.clear()
    yield fake
    storage_services.set_gateway(None)


@pytest.fixture
def gallery(wedding, drive):
    """The bride's ceremony with one READY photo and one READY video in Drive."""
    c = wedding["ceremony"]
    photo = CeremonyMedia.objects.create(
        ceremony=c, kind=MediaKind.PHOTO, status=MediaStatus.READY, original_name="Dilnoza 1.jpg",
        mime_type="image/jpeg", size_bytes=len(PHOTO), drive_file_id="file-photo", completed_at=timezone.now(),
    )  # fmt: skip
    video = CeremonyMedia.objects.create(
        ceremony=c, kind=MediaKind.VIDEO, status=MediaStatus.READY, original_name="to'y.mp4",
        mime_type="video/mp4", size_bytes=len(PHOTO), drive_file_id="file-video", completed_at=timezone.now(),
    )  # fmt: skip
    CeremonyMedia.objects.create(  # still uploading: never visible to the couple
        ceremony=c, kind=MediaKind.VIDEO, status=MediaStatus.UPLOADING, original_name="x.mp4",
        mime_type="video/mp4", size_bytes=10, drive_file_id="",
    )  # fmt: skip
    drive.blobs = {"file-photo": PHOTO, "file-video": PHOTO}
    return {**wedding, "photo": photo, "video": video}


def media_url(c, media=None, action=""):
    base = f"{MY}{c.pk}/media/"
    return f"{base}{media.pk}/{action}/" if media else base


def share_with_guest(w, duration="1W"):
    assert (
        owner_invite(w["c"]["bride"], w["ceremony"], w["users"]["guest"].phone_number, duration=duration).status_code
        == 201
    )
    assert answer(w["c"]["guest"]).status_code == 200
    return CeremonyViewerAccess.objects.get(user=w["users"]["guest"], status=ViewerStatus.ACCEPTED)


# ------------------------------------------------------------- durations
@pytest.mark.django_db
@pytest.mark.parametrize("duration", ["", "2W", "forever"])
def test_viewer_invitation_requires_a_known_duration(wedding, duration):
    res = owner_invite(wedding["c"]["bride"], wedding["ceremony"], "+998901112233", duration=duration)
    assert res.status_code == 400 and "access_duration" in res.data["error"]["details"]


@pytest.mark.django_db
@pytest.mark.parametrize(("code", "delta"), [("24H", timedelta(hours=24)), ("3D", timedelta(days=3)),
                                             ("1W", timedelta(weeks=1)), ("1M", timedelta(days=30))])  # fmt: skip
def test_access_lasts_exactly_the_chosen_duration(wedding, code, delta):
    access = share_with_guest(wedding, code)
    assert access.expires_at - access.accepted_at == delta
    inv = wedding["c"]["guest"].get(INV)  # nothing pending any more
    assert inv.data == []
    members = wedding["c"]["bride"].get(f"{MY}{wedding['ceremony'].pk}/members/").data
    assert members["viewers"][0]["expires_at"] is not None


@pytest.mark.django_db
def test_recipient_sees_duration_before_accepting(wedding):
    owner_invite(wedding["c"]["bride"], wedding["ceremony"], wedding["users"]["guest"].phone_number, duration="3D")
    assert wedding["c"]["guest"].get(INV).data[0]["access_duration"] == "3D"


@pytest.mark.django_db
def test_expired_share_stops_immediately_and_can_be_renewed(gallery):
    w, c = gallery, gallery["ceremony"]
    access = share_with_guest(w, "24H")
    guest = w["c"]["guest"]
    assert guest.get(media_url(c)).status_code == 200

    CeremonyViewerAccess.objects.filter(pk=access.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
    assert guest.get(f"{MY}{c.pk}/").status_code == 404
    assert guest.get(media_url(c)).status_code == 404
    assert guest.get(media_url(c, w["photo"], "stream")).status_code == 404
    assert guest.get(MY).data["count"] == 0
    assert w["c"]["bride"].get(f"{MY}{c.pk}/members/").data["viewers"] == []

    # The owner shares again: the stale ACCEPTED row must not block the new one.
    share_with_guest(w, "1W")
    assert CeremonyViewerAccess.objects.get(pk=access.pk).status == ViewerStatus.EXPIRED
    assert guest.get(media_url(c)).status_code == 200


# ------------------------------------------------------------------ quota
def make_groom_owner(w):
    CeremonyOwnership.objects.create(
        ceremony=w["ceremony"], user=w["users"]["groom"], owner_type=OwnerType.GROOM,
        status=OwnershipStatus.ACCEPTED, accepted_at=timezone.now(),
    )  # fmt: skip


@pytest.mark.django_db
def test_each_owner_shares_with_at_most_five_people(wedding):
    w, c = wedding, wedding["ceremony"]
    make_groom_owner(w)
    share_with_guest(w)  # 1 live access …
    for i in range(4):  # … + 4 pending invitations = 5
        assert owner_invite(w["c"]["bride"], c, f"+99890555000{i}").status_code == 201
    res = owner_invite(w["c"]["bride"], c, "+998905550009")
    assert res.status_code == 400 and "5" in str(res.data["error"]["details"])

    # The groom has his own five.
    for i in range(5):
        assert owner_invite(w["c"]["groom"], c, f"+99890666000{i}").status_code == 201
    assert owner_invite(w["c"]["groom"], c, "+998906660009").status_code == 400

    # Revoking a pending invitation frees a slot.
    pending = CeremonyInvitation.objects.filter(invited_by=w["users"]["bride"], status="PENDING").first()
    assert w["c"]["bride"].post(f"{MY}{c.pk}/invitations/{pending.pk}/revoke/").status_code == 204
    assert owner_invite(w["c"]["bride"], c, "+998905550009").status_code == 201


@pytest.mark.django_db
def test_expired_access_does_not_count_against_quota(wedding):
    w, c = wedding, wedding["ceremony"]
    access = share_with_guest(w)
    for i in range(4):
        owner_invite(w["c"]["bride"], c, f"+99890555000{i}")
    assert owner_invite(w["c"]["bride"], c, "+998905550009").status_code == 400
    CeremonyViewerAccess.objects.filter(pk=access.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
    assert owner_invite(w["c"]["bride"], c, "+998905550009").status_code == 201


# ------------------------------------------------------------------ media
@pytest.mark.django_db
def test_owner_and_viewer_list_only_ready_media_without_drive_ids(gallery):
    w, c = gallery, gallery["ceremony"]
    share_with_guest(w)
    subscribe(w["users"]["bride"])  # originals + download need a running subscription (2026-11-08)
    for who, can_download in (("bride", True), ("guest", False)):
        res = w["c"][who].get(media_url(c))
        assert res.status_code == 200
        assert {m["id"] for m in res.data} == {str(w["photo"].pk), str(w["video"].pk)}
        assert all(m["can_download"] is can_download for m in res.data)
        assert "file-photo" not in res.content.decode() and "Dilnoza" not in res.content.decode()


@pytest.mark.django_db
def test_strangers_studio_and_other_ceremonies_get_404(gallery, client_for, make_user):
    w, c = gallery, gallery["ceremony"]
    for client in (w["c"]["stranger"], w["c"]["mother"]):
        assert client.get(media_url(c)).status_code == 404
        assert client.get(media_url(c, w["photo"], "stream")).status_code == 404
    assert w["studio"].get(media_url(c)).status_code == 403  # USER-only endpoint
    # a media id of this ceremony under another ceremony's URL
    assert w["c"]["bride"].get(f"{MY}{w['other'].pk}/media/{w['photo'].pk}/stream/").status_code == 404


@pytest.mark.django_db
def test_stream_supports_ranges_inline(gallery, drive):
    w, c = gallery, gallery["ceremony"]
    subscribe(w["users"]["bride"])
    res = w["c"]["bride"].get(media_url(c, w["video"], "stream"), HTTP_RANGE="bytes=0-99")
    assert res.status_code == 206
    assert b"".join(res.streaming_content) == PHOTO[:100]
    assert res["Content-Range"] == f"bytes 0-99/{len(PHOTO)}" and res["Accept-Ranges"] == "bytes"
    assert res["Content-Disposition"].startswith("inline;") and "to'y" not in res["Content-Disposition"]
    assert res["Cache-Control"] == "no-store"  # every /api/ response (core middleware)

    full = w["c"]["bride"].get(media_url(c, w["photo"], "stream"), HTTP_ACCEPT="image/avif,image/webp,*/*")
    assert full.status_code == 200 and b"".join(full.streaming_content) == PHOTO
    assert w["c"]["bride"].get(media_url(c, w["photo"], "stream"), HTTP_RANGE=f"bytes={10**9}-").status_code == 416


@pytest.mark.django_db
@pytest.mark.parametrize("raw", ["bytes=0-10,20-30", "items=0-5", "bytes=9-1", "bytes=-", "bytes=abc"])
def test_unsafe_ranges_are_not_forwarded(gallery, drive, raw):
    subscribe(gallery["users"]["bride"])
    gallery["c"]["bride"].get(media_url(gallery["ceremony"], gallery["photo"], "stream"), HTTP_RANGE=raw)
    assert drive.ranges[-1] is None


@pytest.mark.django_db
def test_only_owners_download_and_downloads_are_audited(gallery):
    w, c = gallery, gallery["ceremony"]
    share_with_guest(w)
    denied = w["c"]["guest"].get(media_url(c, w["photo"], "download"))
    assert denied.status_code == 403
    subscribe(w["users"]["bride"])
    res = w["c"]["bride"].get(media_url(c, w["photo"], "download"))
    assert res.status_code == 200 and b"".join(res.streaming_content) == PHOTO
    assert res["Content-Disposition"].startswith("attachment;")
    assert AuditLog.objects.filter(action=AuditAction.MEDIA_DOWNLOAD).count() == 1


@pytest.mark.django_db
def test_thumbnails_are_cached(gallery, drive):
    w, c = gallery, gallery["ceremony"]
    url = media_url(c, w["photo"], "thumbnail")
    subscribe(w["users"]["bride"])  # raw preview: no logo for a subscribed owner
    for _ in range(3):
        res = w["c"]["bride"].get(url, {"size": 240}, HTTP_ACCEPT="image/*")
        assert res.status_code == 200 and res.content == b"\x89PNG-thumb-240" and res["Content-Type"] == "image/png"
    assert drive.thumb_calls == 1
    assert w["c"]["bride"].get(url, {"size": 99999}).content == b"\x89PNG-thumb-480"  # unknown size → default
