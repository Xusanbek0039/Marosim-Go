"""Removing ceremony media: studios dismiss unfinished uploads; READY files go through an admin request."""

import pytest

from apps.accounts.models import Role
from apps.audit.models import AuditAction, AuditLog
from apps.media.models import CeremonyMedia, DeletionRequestStatus, MediaDeletionRequest, MediaStatus
from apps.storage.google import GoogleError

from .test_media_upload import MB, base, drive, start, studio  # noqa: F401 — fixtures

ADMIN_URL = "/api/v1/admin/media-deletion-requests/"


def ready_file(client, c, drive):  # noqa: F811
    created = start(client, c).data
    drive.finish(created["upload_url"])
    res = client.post(f"{base(c)}uploads/{created['media']['id']}/complete/")
    assert res.status_code == 200, res.data
    return CeremonyMedia.objects.get(pk=created["media"]["id"])


def ask(client, c, media, reason="Noto'g'ri marosimga yuklangan"):
    return client.post(f"{base(c)}{media.pk}/delete-request/", {"reason": reason}, format="json")


@pytest.fixture
def admins(make_user, client_for):
    viewer = make_user(Role.ADMIN, admin_permissions=["requests.view"])
    decider = make_user(Role.ADMIN, admin_permissions=["requests.view", "requests.media_delete"])
    return {
        "none": client_for(make_user(Role.ADMIN, admin_permissions=[])),
        "viewer": client_for(viewer),
        "decider": client_for(decider),
        "super": client_for(make_user(Role.SUPER_ADMIN)),
    }


# --------------------------------------------------------------- dismiss
@pytest.mark.django_db
def test_studio_dismisses_unfinished_upload_and_session_is_cancelled(studio, drive):  # noqa: F811
    c = studio["ceremony"]
    created = start(studio["uploader"], c).data
    url = f"{base(c)}uploads/{created['media']['id']}/"
    assert studio["rival"].delete(url).status_code == 404
    assert studio["uploader2"].delete(url).status_code == 403  # another uploader's file
    assert studio["uploader"].delete(url).status_code == 204
    row = CeremonyMedia.objects.get()
    assert row.status == MediaStatus.DELETED and row.deleted_at and row.upload_session_encrypted == ""
    assert drive.cancelled == [created["upload_url"]]
    assert studio["owner"].get(base(c)).data["count"] == 0  # hidden from the studio list
    assert AuditLog.objects.filter(action=AuditAction.MEDIA_DISMISS).count() == 1


@pytest.mark.django_db
def test_failed_upload_is_dismissed_by_manager(studio, drive):  # noqa: F811
    c = studio["ceremony"]
    created = start(studio["uploader"], c).data
    CeremonyMedia.objects.filter(pk=created["media"]["id"]).update(
        status=MediaStatus.FAILED, upload_session_encrypted=""
    )
    assert studio["owner"].delete(f"{base(c)}uploads/{created['media']['id']}/").status_code == 204
    assert CeremonyMedia.objects.get().status == MediaStatus.DELETED


@pytest.mark.django_db
def test_ready_file_cannot_be_dismissed(studio, drive):  # noqa: F811
    c = studio["ceremony"]
    media = ready_file(studio["uploader"], c, drive)
    res = studio["owner"].delete(f"{base(c)}uploads/{media.pk}/")
    assert res.status_code == 409
    media.refresh_from_db()
    assert media.status == MediaStatus.READY


# --------------------------------------------------------------- request
@pytest.mark.django_db
def test_request_is_listed_for_admins_and_approval_trashes_drive_files(studio, drive, admins):  # noqa: F811
    c = studio["ceremony"]
    media = ready_file(studio["uploader"], c, drive)
    media.wm_drive_file_id = "wm-copy"
    media.save(update_fields=["wm_drive_file_id"])
    drive.items["wm-copy"] = {"id": "wm-copy", "trashed": False}

    assert studio["rival"].post(f"{base(c)}{media.pk}/delete-request/", {"reason": "x"}).status_code == 404
    res = ask(studio["uploader2"], c, media)
    assert res.status_code == 201, res.data
    assert ask(studio["owner"], c, media).status_code == 409  # one pending request per file
    item = studio["owner"].get(base(c)).data["results"][0]
    assert item["deletion_request"]["reason"] == "Noto'g'ri marosimga yuklangan"

    assert admins["none"].get(ADMIN_URL).status_code == 403
    listing = admins["viewer"].get(ADMIN_URL, {"status": "PENDING"}).data
    assert listing["count"] == 1
    row = listing["results"][0]
    assert row["studio"]["name"] == c.studio.name and row["ceremony"]["title"] == c.title
    assert row["media"]["original_name"] == media.original_name
    assert admins["viewer"].get(f"{ADMIN_URL}summary/").data == {"pending": 1}
    assert admins["viewer"].post(f"{ADMIN_URL}{row['id']}/approve/").status_code == 403  # view only

    res = admins["decider"].post(f"{ADMIN_URL}{row['id']}/approve/", {"note": "Ok"}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["status"] == "APPROVED" and res.data["decided_by_name"]
    media.refresh_from_db()
    assert media.status == MediaStatus.DELETED and media.deleted_at
    assert drive.items[media.drive_file_id]["trashed"] and drive.items["wm-copy"]["trashed"]
    assert drive.deleted == []  # trashed, not permanently deleted
    assert studio["owner"].get(base(c)).data["count"] == 0
    assert admins["super"].post(f"{ADMIN_URL}{row['id']}/reject/").status_code == 409  # already decided
    assert AuditLog.objects.filter(action=AuditAction.MEDIA_DELETE_APPROVE).count() == 1


@pytest.mark.django_db
def test_rejected_request_keeps_the_file_and_a_new_one_can_follow(studio, drive, admins):  # noqa: F811
    c = studio["ceremony"]
    media = ready_file(studio["uploader"], c, drive)
    rid = ask(studio["uploader"], c, media).data["id"]
    res = admins["super"].post(f"{ADMIN_URL}{rid}/reject/", {"note": "Fayl kerak"}, format="json")
    assert res.status_code == 200 and res.data["status"] == "REJECTED" and res.data["decision_note"] == "Fayl kerak"
    media.refresh_from_db()
    assert media.status == MediaStatus.READY and not drive.items[media.drive_file_id]["trashed"]
    assert studio["owner"].get(base(c)).data["results"][0]["deletion_request"] is None
    assert ask(studio["uploader"], c, media).status_code == 201


@pytest.mark.django_db
def test_requester_or_manager_withdraws_request(studio, drive):  # noqa: F811
    c = studio["ceremony"]
    media = ready_file(studio["uploader"], c, drive)
    ask(studio["uploader"], c, media)
    url = f"{base(c)}{media.pk}/delete-request/cancel/"
    assert studio["uploader2"].post(url).status_code == 403
    assert studio["owner"].post(url).status_code == 204
    assert MediaDeletionRequest.objects.get().status == DeletionRequestStatus.CANCELLED
    assert studio["owner"].post(url).status_code == 409


@pytest.mark.django_db
def test_drive_error_keeps_request_pending(studio, drive, admins, monkeypatch):  # noqa: F811
    c = studio["ceremony"]
    media = ready_file(studio["uploader"], c, drive)
    rid = ask(studio["uploader"], c, media).data["id"]

    def down(creds, file_id):
        raise GoogleError("backend_error", 503)

    monkeypatch.setattr(drive, "trash_file", down)
    assert admins["decider"].post(f"{ADMIN_URL}{rid}/approve/").status_code == 503
    assert MediaDeletionRequest.objects.get().status == DeletionRequestStatus.PENDING
    media.refresh_from_db()
    assert media.status == MediaStatus.READY


@pytest.mark.django_db
def test_file_already_gone_from_drive_is_still_deleted(studio, drive, admins):  # noqa: F811
    c = studio["ceremony"]
    media = ready_file(studio["uploader"], c, drive)
    rid = ask(studio["uploader"], c, media).data["id"]
    drive.items.pop(media.drive_file_id)
    assert admins["decider"].post(f"{ADMIN_URL}{rid}/approve/").status_code == 200
    media.refresh_from_db()
    assert media.status == MediaStatus.DELETED
