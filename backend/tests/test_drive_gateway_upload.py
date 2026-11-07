"""GoogleGateway resumable-upload HTTP handling (requests is stubbed — no network)."""

import pytest
import requests

from apps.storage.google import GoogleError, GoogleGateway

URI = "https://www.googleapis.com/upload/drive/v3/files?upload_id=abc"


class Res:
    def __init__(self, status, headers=None, body=None, content=b"{}"):
        self.status_code, self.headers, self._body, self.content = status, headers or {}, body, content

    def json(self):
        return self._body


@pytest.fixture
def put(monkeypatch):
    calls = []

    def install(response):
        def fake_put(url, headers=None, timeout=None):
            calls.append((url, headers))
            if isinstance(response, Exception):
                raise response
            return response

        monkeypatch.setattr(requests, "put", fake_put)
        return calls

    return install


@pytest.mark.parametrize(
    ("response", "state", "received"),
    [
        (Res(308, {"Range": "bytes=0-1048575"}), "in_progress", 1048576),
        (Res(308), "in_progress", 0),
        (Res(200, body={"id": "F1"}), "complete", 10),
        (Res(201, body={"id": "F1"}), "complete", 10),
        (Res(404), "expired", 0),
        (Res(410), "expired", 0),
    ],
)
def test_upload_status_parsing(put, response, state, received):
    calls = put(response)
    progress = GoogleGateway().upload_status(URI, 10)
    assert progress.state == state and progress.received == received
    assert calls[0][1]["Content-Range"] == "bytes */10"
    if state == "complete":
        assert progress.file == {"id": "F1"}


def test_upload_status_errors(put):
    put(Res(503))
    with pytest.raises(GoogleError) as exc:
        GoogleGateway().upload_status(URI, 10)
    assert exc.value.code == "google_unavailable"
    put(requests.ConnectionError("down"))
    with pytest.raises(GoogleError) as exc:
        GoogleGateway().upload_status(URI, 10)
    assert exc.value.code == "network_error"


def test_start_resumable_upload_returns_location(monkeypatch):
    sent = {}

    class Session:
        def __init__(self, creds):
            pass

        def post(self, url, json=None, headers=None, timeout=None):
            sent.update(url=url, json=json, headers=headers)
            return Res(200, {"Location": URI})

    monkeypatch.setattr("google.auth.transport.requests.AuthorizedSession", Session)
    uri = GoogleGateway().start_resumable_upload(
        object(), name="m.jpg", parent_id="P", mime_type="image/jpeg", size=5, app_properties={"mg_media": "m"}
    )
    assert uri == URI and "uploadType=resumable" in sent["url"]
    assert sent["headers"] == {"X-Upload-Content-Type": "image/jpeg", "X-Upload-Content-Length": "5"}
    assert sent["json"]["parents"] == ["P"] and sent["json"]["appProperties"] == {"mg_media": "m"}


def test_start_resumable_upload_maps_drive_errors(monkeypatch):
    body = b'{"error": {"errors": [{"reason": "storageQuotaExceeded"}]}}'

    class Session:
        def __init__(self, creds):
            pass

        def post(self, *a, **k):
            return Res(403, content=body)

    monkeypatch.setattr("google.auth.transport.requests.AuthorizedSession", Session)
    with pytest.raises(GoogleError) as exc:
        GoogleGateway().start_resumable_upload(
            object(), name="m", parent_id="P", mime_type="image/jpeg", size=5, app_properties={}
        )
    assert exc.value.code == "storage_quota_exceeded"
