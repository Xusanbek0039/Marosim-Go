"""Phase D — studio media upload to Google Drive (direct resumable sessions), against a fake Drive."""

import itertools
import json

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.models import AuditAction, AuditLog
from apps.ceremonies.models import Ceremony, CeremonyOwnership, CeremonyStatus, OwnershipStatus, OwnerType
from apps.media.models import CeremonyMedia, MediaStatus
from apps.storage import services as storage_services
from apps.storage import vault
from apps.storage.google import GoogleError, UploadProgress
from apps.storage.models import ConnectionStatus, DriveFolder, StorageConnection, StorageCredential
from apps.studios.models import StudioMembership
from apps.studios.services import sync_owner_membership

FOLDER = "application/vnd.google-apps.folder"
MB = 1024 * 1024


class FakeDrive:
    """Just enough of Drive: folders, files and resumable sessions. Never touches the network."""

    def __init__(self):
        self.ids = itertools.count(1)
        self.items: dict[str, dict] = {}  # id -> {name, parents, mimeType, size, appProperties, trashed}
        self.sessions: dict[str, dict] = {}
        self.folder_creates = 0
        self.fail_start: GoogleError | None = None
        self.deleted: list[str] = []
        self.cancelled: list[str] = []

    # --- auth
    def credentials(self, config, refresh_token, scopes):
        return object()

    # --- folders / files
    def create_folder(self, creds, name, parent_id):
        self.folder_creates += 1
        fid = f"folder{next(self.ids)}"
        self.items[fid] = {"id": fid, "name": name, "parents": [parent_id] if parent_id else [], "mimeType": FOLDER}
        return {"id": fid, "name": name}

    def find_child_folder(self, creds, name, parent_id):
        return next(
            (i for i, f in self.items.items() if f["mimeType"] == FOLDER and f["name"] == name
             and parent_id in f["parents"] and not f.get("trashed")),
            None,
        )  # fmt: skip

    def delete_file(self, creds, file_id):
        self.deleted.append(file_id)
        self.items.pop(file_id, None)

    def trash_file(self, creds, file_id):
        if file_id not in self.items:
            raise GoogleError("not_found", 404)
        self.items[file_id]["trashed"] = True

    def file_metadata(self, creds, file_id):
        if file_id not in self.items:
            raise GoogleError("not_found", 404)
        return dict(self.items[file_id])

    # --- resumable sessions
    def start_resumable_upload(self, creds, *, name, parent_id, mime_type, size, app_properties, origin=None):
        if self.fail_start:
            error, self.fail_start = self.fail_start, None
            raise error
        if parent_id not in self.items:
            raise GoogleError("not_found", 404)
        uri = f"https://www.googleapis.com/upload/drive/v3/files?upload_id=SESSION-{next(self.ids)}"
        self.sessions[uri] = {
            "name": name, "parents": [parent_id], "mimeType": mime_type, "size": size,
            "appProperties": app_properties, "received": 0, "file": None, "expired": False, "origin": origin,
        }  # fmt: skip
        return uri

    def upload_status(self, uri, size):
        s = self.sessions[uri]
        if s["expired"]:
            return UploadProgress(state="expired", received=0)
        if s["file"]:
            return UploadProgress(state="complete", received=size, file={"id": s["file"]})
        return UploadProgress(state="in_progress", received=s["received"])

    def cancel_upload(self, uri):
        self.cancelled.append(uri)

    # --- what a client (or an attacker) does with the session URI
    def push(self, uri, received):
        self.sessions[uri]["received"] = received

    def finish(self, uri, **tamper):
        s = self.sessions[uri]
        fid = f"file{next(self.ids)}"
        self.items[fid] = {
            "id": fid, "name": s["name"], "parents": s["parents"], "mimeType": s["mimeType"], "size": str(s["size"]),
            "appProperties": s["appProperties"], "md5Checksum": "0" * 32, "trashed": False,
            "imageMediaMetadata": {"width": 4000, "height": 3000}, **tamper,
        }  # fmt: skip
        s["file"] = fid
        return fid


@pytest.fixture
def drive(db):
    fake = FakeDrive()
    storage_services.set_gateway(fake)
    conn = storage_services.connection()
    conn.account_email, conn.status = "owner@gmail.com", ConnectionStatus.CONNECTED
    conn.root_folder_id = ""  # independent of a GOOGLE_DRIVE_ROOT_FOLDER_ID in the local .env
    conn.save()
    StorageCredential.objects.create(connection=conn, refresh_token_encrypted=vault.seal("1//refresh"))
    yield fake
    storage_services.set_gateway(None)


@pytest.fixture
def studio(make_user, make_studio, client_for):
    owner, uploader, rival_owner = make_user(Role.STUDIO), make_user(Role.STUDIO), make_user(Role.STUDIO)
    uploader2 = make_user(Role.STUDIO)
    s, rival = make_studio(owner), make_studio(rival_owner)
    sync_owner_membership(s)
    sync_owner_membership(rival)
    for u in (uploader, uploader2):
        StudioMembership.objects.create(studio=s, user=u, role=StudioMembership.Role.UPLOADER)
    c = Ceremony.objects.create(studio=s, title="To'y", event_date="2026-09-12", status=CeremonyStatus.READY)
    return {
        "ceremony": c,
        "owner": client_for(owner),
        "uploader": client_for(uploader),
        "uploader2": client_for(uploader2),
        "rival": client_for(rival_owner),
        "uploader_user": uploader,
    }


def base(c):
    return f"/api/v1/ceremonies/{c.pk}/media/"


def start(client, c, mime="image/jpeg", size=3 * MB, name="IMG_0001.JPG", **extra):
    body = {"filename": name, "mime_type": mime, "size_bytes": size, **extra}
    return client.post(f"{base(c)}uploads/", body, format="json")


def drive_ids_leak(payload, drive) -> bool:
    text = json.dumps(payload, default=str)
    return any(i in text for i in drive.items) or "upload_id=" in text


# ------------------------------------------------------------------ start
@pytest.mark.django_db
def test_studio_member_starts_upload_into_folder_tree(studio, drive):
    c = studio["ceremony"]
    res = start(studio["uploader"], c, mime="video/quicktime", size=700 * MB, name="C:\\DCIM\\Dilnoza to'y.MOV")
    assert res.status_code == 201, res.data
    assert res.data["upload_url"].startswith("https://www.googleapis.com/upload/drive/v3/files?upload_id=")
    assert res.data["chunk_size_multiple"] == 256 * 1024 and res.data["received_bytes"] == 0
    media = CeremonyMedia.objects.get()
    assert res.data["media"]["kind"] == "VIDEO" and res.data["media"]["status"] == "UPLOADING"
    assert media.original_name == "Dilnoza to'y.MOV"  # path stripped

    names = {f["name"] for f in drive.items.values()}
    # No client known yet: the folder carries only a short ceremony id.
    assert {"MarosimGo", f"Studio_{c.studio.name}", f"Mijoz_{c.pk.hex[:6]}", "Videos"} <= names
    session = next(iter(drive.sessions.values()))
    assert session["name"] == f"{media.pk}.mov"  # no personal data in Drive names
    assert session["appProperties"] == {"mg_media": str(media.pk), "mg_ceremony": str(c.pk)}
    c.refresh_from_db()
    assert c.drive_folder_id and StorageConnection.objects.get().root_folder_id
    # the session URI is stored encrypted only
    assert "upload_id" not in media.upload_session_encrypted and vault.unseal(media.upload_session_encrypted)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("origin", "forwarded"),
    [("http://localhost:3001", "http://localhost:3001"), ("https://evil.example", None), (None, None)],
)
def test_session_is_opened_for_the_allowlisted_browser_origin_only(studio, drive, origin, forwarded):
    """Google sends CORS headers on the final PUT response only if the session was opened with that Origin."""
    headers = {"HTTP_ORIGIN": origin} if origin else {}
    c = studio["ceremony"]
    body = {"filename": "a.jpg", "mime_type": "image/jpeg", "size_bytes": MB}
    assert studio["uploader"].post(f"{base(c)}uploads/", body, format="json", **headers).status_code == 201
    assert next(iter(drive.sessions.values()))["origin"] == forwarded


@pytest.mark.django_db
def test_client_folder_shows_only_last_four_jshshir_digits(studio, drive, make_user):
    """User decision 2026-11-07: Studio_<name> / Mijoz_****<last4>_<id6>; the full JSHSHIR never reaches Drive."""
    c = studio["ceremony"]
    bride = make_user(Role.USER, pinfl="31203199512345")
    CeremonyOwnership.objects.create(
        ceremony=c, user=bride, owner_type=OwnerType.BRIDE, status=OwnershipStatus.ACCEPTED, accepted_at=timezone.now()
    )
    assert start(studio["uploader"], c).status_code == 201
    names = {f["name"] for f in drive.items.values()}
    assert f"Mijoz_****2345_{c.pk.hex[:6]}" in names and "Photos" in names
    assert not any("3120319951" in n for n in names)


@pytest.mark.django_db
def test_folders_are_created_once(studio, drive):
    c = studio["ceremony"]
    start(studio["owner"], c)
    created = drive.folder_creates
    start(studio["owner"], c, name="b.jpg")
    assert drive.folder_creates == created == 4  # root, studio, ceremony, Photos
    start(studio["owner"], c, mime="video/mp4", name="v.mp4")
    assert drive.folder_creates == 5  # + Videos
    DriveFolder.objects.all().delete()  # lost cache: existing folders are found again, not duplicated
    start(studio["owner"], c, name="c.jpg")
    assert drive.folder_creates == 5


@pytest.mark.django_db
def test_deleted_drive_folder_is_rebuilt(studio, drive):
    c = studio["ceremony"]
    start(studio["owner"], c)
    photos = DriveFolder.objects.get(key__endswith="/photo").folder_id
    drive.items.pop(photos)
    assert start(studio["owner"], c, name="again.jpg").status_code == 201
    assert DriveFolder.objects.get(key__endswith="/photo").folder_id != photos


@pytest.mark.django_db
def test_upload_scope_and_roles(studio, drive, make_user, client_for, super_admin):
    c = studio["ceremony"]
    assert start(studio["rival"], c).status_code == 404
    assert studio["rival"].get(base(c)).status_code == 404
    for role in (Role.USER, Role.ADMIN):
        assert start(client_for(make_user(role)), c).status_code == 403
    assert start(client_for(super_admin), c).status_code == 201


@pytest.mark.django_db
@override_settings(MEDIA_UPLOAD={"PHOTO_MAX_BYTES": 10 * MB, "VIDEO_MAX_BYTES": 100 * MB,
                                 "MAX_ACTIVE_PER_CEREMONY": 2, "SESSION_TTL_HOURS": 144})  # fmt: skip
def test_upload_validation(studio, drive):
    c, client = studio["ceremony"], studio["owner"]
    assert start(client, c, mime="application/pdf").status_code == 400
    assert start(client, c, mime="image/svg+xml").status_code == 400
    assert "size_bytes" in start(client, c, size=11 * MB).data["error"]["details"]
    assert start(client, c, size=0).status_code == 400
    assert start(client, c, md5="not-a-checksum").status_code == 400
    assert start(client, c).status_code == 201 and start(client, c).status_code == 201
    assert start(client, c).status_code == 400  # active upload limit
    Ceremony.objects.filter(pk=c.pk).update(status=CeremonyStatus.ARCHIVED)
    assert start(client, c, mime="video/mp4").status_code == 400


@pytest.mark.django_db
def test_storage_unavailable(studio, drive):
    c = studio["ceremony"]
    StorageCredential.objects.all().delete()
    res = start(studio["owner"], c)
    assert res.status_code == 503 and res.data["error"]["code"] == "storage_unavailable"
    assert CeremonyMedia.objects.get().status == MediaStatus.FAILED

    StorageCredential.objects.create(connection=storage_services.connection(), refresh_token_encrypted=vault.seal("x"))
    drive.fail_start = GoogleError("storage_quota_exceeded", 403)
    res = start(studio["owner"], c, name="b.jpg")
    assert res.status_code == 503 and "storage_quota_exceeded" in res.data["error"]["message"]


# --------------------------------------------------------------- progress
@pytest.mark.django_db
def test_progress_is_live_and_url_only_for_uploader(studio, drive):
    c = studio["ceremony"]
    created = start(studio["uploader"], c, mime="video/mp4", size=50 * MB).data
    url = f"{base(c)}uploads/{created['media']['id']}/"
    drive.push(created["upload_url"], 10 * MB)
    mine = studio["uploader"].get(url).data
    assert mine["received_bytes"] == 10 * MB and mine["upload_url"] == created["upload_url"]
    theirs = studio["owner"].get(url).data
    assert theirs["received_bytes"] == 10 * MB and theirs["upload_url"] is None
    assert studio["rival"].get(url).status_code == 404


# --------------------------------------------------------------- complete
@pytest.mark.django_db
def test_complete_verifies_and_marks_ready(studio, drive):
    c = studio["ceremony"]
    created = start(studio["uploader"], c).data
    url = f"{base(c)}uploads/{created['media']['id']}/complete/"
    drive.push(created["upload_url"], MB)
    res = studio["uploader"].post(url)
    assert res.status_code == 409 and res.data["error"]["code"] == "upload_incomplete"

    drive.finish(created["upload_url"])
    res = studio["uploader"].post(url)
    assert res.status_code == 200, res.data
    media = res.data["media"]
    assert media["status"] == "READY" and media["width"] == 4000 and res.data["upload_url"] is None
    row = CeremonyMedia.objects.get()
    assert row.drive_file_id and row.upload_session_encrypted == "" and row.completed_at
    assert studio["uploader"].post(url).status_code == 200  # idempotent
    assert AuditLog.objects.filter(action=AuditAction.MEDIA_UPLOAD).count() == 1

    listing = studio["owner"].get(base(c)).data
    assert listing["count"] == 1 and listing["results"][0]["status"] == "READY"
    assert not drive_ids_leak(listing, drive) and not drive_ids_leak(res.data, drive)


@pytest.mark.django_db
def test_progress_poll_finalises_finished_upload(studio, drive):
    c = studio["ceremony"]
    created = start(studio["uploader"], c).data
    drive.finish(created["upload_url"])
    res = studio["owner"].get(f"{base(c)}uploads/{created['media']['id']}/")
    assert res.data["media"]["status"] == "READY"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("tamper", "code"),
    [
        ({"size": "1"}, "size_mismatch"),
        ({"parents": ["folder-elsewhere"]}, "wrong_folder"),
        ({"appProperties": {"mg_media": "someone-else"}}, "marker_mismatch"),
        ({"mimeType": "text/html"}, "type_mismatch"),
        ({"trashed": True}, "file_trashed"),
    ],
)
def test_tampered_upload_is_rejected_and_deleted(studio, drive, tamper, code):
    c = studio["ceremony"]
    created = start(studio["uploader"], c).data
    fid = drive.finish(created["upload_url"], **tamper)
    res = studio["uploader"].post(f"{base(c)}uploads/{created['media']['id']}/complete/")
    assert (
        res.status_code == 409
        and res.data["error"]["code"] == "upload_rejected"
        and code in res.data["error"]["message"]
    )
    assert fid in drive.deleted
    row = CeremonyMedia.objects.get()
    assert row.status == MediaStatus.FAILED and row.error_code == code and not row.drive_file_id
    assert AuditLog.objects.filter(action=AuditAction.MEDIA_UPLOAD_FAILED).exists()


@pytest.mark.django_db
def test_checksum_mismatch_rejected(studio, drive):
    c = studio["ceremony"]
    created = start(studio["uploader"], c, md5="A" * 32).data
    drive.finish(created["upload_url"])  # Drive reports 000…0
    res = studio["uploader"].post(f"{base(c)}uploads/{created['media']['id']}/complete/")
    assert res.status_code == 409 and "checksum_mismatch" in res.data["error"]["message"]


# ----------------------------------------------------- expiry / cancel
@pytest.mark.django_db
def test_expired_session(studio, drive):
    c = studio["ceremony"]
    created = start(studio["uploader"], c).data
    drive.sessions[created["upload_url"]]["expired"] = True
    assert studio["uploader"].post(f"{base(c)}uploads/{created['media']['id']}/complete/").status_code == 409
    assert CeremonyMedia.objects.get().status == MediaStatus.EXPIRED

    other = start(studio["uploader"], c, name="b.jpg").data
    CeremonyMedia.objects.filter(pk=other["media"]["id"]).update(session_expires_at="2000-01-01T00:00:00Z")
    call_command("expire_media_uploads")
    assert CeremonyMedia.objects.get(pk=other["media"]["id"]).status == MediaStatus.EXPIRED
    assert other["upload_url"] in drive.cancelled


@pytest.mark.django_db
def test_cancel_rights(studio, drive):
    c = studio["ceremony"]
    a = start(studio["uploader"], c).data
    b = start(studio["uploader"], c, name="b.jpg").data
    cancel = lambda client, d: client.post(f"{base(c)}uploads/{d['media']['id']}/cancel/")  # noqa: E731
    assert cancel(studio["uploader2"], a).status_code == 403  # another uploader
    assert cancel(studio["uploader"], a).data["media"]["status"] == "CANCELLED"
    assert cancel(studio["owner"], b).status_code == 200  # studio OWNER/MANAGER
    assert cancel(studio["owner"], b).status_code == 409
    assert set(drive.cancelled) == {a["upload_url"], b["upload_url"]}


# ------------------------------------------------------------- isolation
@pytest.mark.django_db
def test_other_account_never_reuses_folder_ids(studio, drive):
    c = studio["ceremony"]
    start(studio["owner"], c)
    before = drive.folder_creates
    StorageConnection.objects.update(account_email="someone-else@gmail.com", root_folder_id="")
    start(studio["owner"], c, name="b.jpg")
    assert drive.folder_creates == before * 2
