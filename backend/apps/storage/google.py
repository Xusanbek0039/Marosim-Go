"""The only module that talks to Google. Everything above it uses ``GoogleGateway``'s small API,
so unit tests substitute a fake (``services.set_gateway``) and never hit the network.

Errors are normalized to ``GoogleError(code)`` with stable, non-secret codes.
"""

import json
import os
from dataclasses import dataclass, field

from django.conf import settings

from .client_config import OAuthClientConfig

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
TIMEOUT = 15

# Google may return scopes in a different order/form than requested (or fewer, with granular
# consent). We check the granted set ourselves instead of letting oauthlib raise.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")


class GoogleError(Exception):
    def __init__(self, code: str, status: int | None = None):
        super().__init__(code)
        self.code = code
        self.status = status


class GoogleAuthRevoked(GoogleError):
    """Refresh token expired/revoked (``invalid_grant``) — the owner must reconnect."""

    def __init__(self):
        super().__init__("invalid_grant", 400)


@dataclass
class TokenGrant:
    refresh_token: str | None = field(repr=False)
    access_token: str = field(repr=False)
    scopes: list[str]
    email: str


@dataclass
class AccountInfo:
    email: str
    display_name: str = ""
    quota_limit: int | None = None
    quota_usage: int | None = None


_DRIVE_REASONS = {
    "storageQuotaExceeded": "storage_quota_exceeded",
    "userRateLimitExceeded": "rate_limited",
    "rateLimitExceeded": "rate_limited",
    "dailyLimitExceeded": "quota_exceeded",
    "insufficientPermissions": "insufficient_permissions",
    "insufficientFilePermissions": "insufficient_permissions",
    "accessNotConfigured": "drive_api_disabled",
    "notFound": "not_found",
    "authError": "auth_error",
}


def _drive_error(exc) -> GoogleError:
    status = getattr(getattr(exc, "resp", None), "status", None)
    # Parse the body ourselves: HttpError.error_details is only filled lazily by __repr__.
    reason = ""
    try:
        payload = json.loads(exc.content.decode() if isinstance(exc.content, bytes) else exc.content)
        errors = (payload.get("error") or {}).get("errors") or []
        reason = errors[0].get("reason", "") if errors else ""
    except (AttributeError, IndexError, TypeError, ValueError):
        reason = ""
    code = _DRIVE_REASONS.get(reason)
    if code is None:
        code = {401: "auth_error", 403: "forbidden", 404: "not_found", 429: "rate_limited"}.get(status, "drive_error")
        if status and status >= 500:
            code = "google_unavailable"
    return GoogleError(code, status)


class GoogleGateway:
    """Real implementation (google-auth-oauthlib + google-api-python-client)."""

    def _flow(self, config: OAuthClientConfig, code_verifier: str):
        from google_auth_oauthlib.flow import Flow

        return Flow.from_client_config(
            config.as_google_client_config(),
            scopes=settings.GOOGLE_OAUTH_SCOPES,
            redirect_uri=config.redirect_uri,
            code_verifier=code_verifier,
            autogenerate_code_verifier=False,
        )

    def authorization_url(self, config: OAuthClientConfig, state: str, code_verifier: str) -> str:
        url, _ = self._flow(config, code_verifier).authorization_url(
            state=state,
            access_type="offline",  # → refresh token
            prompt="consent",  # → a refresh token even if the app was approved before
            include_granted_scopes="true",
        )
        return url

    def exchange_code(self, config: OAuthClientConfig, code: str, code_verifier: str) -> TokenGrant:
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token

        flow = self._flow(config, code_verifier)
        try:
            token = flow.fetch_token(code=code)
        except Exception as exc:  # noqa: BLE001 - oauthlib raises many types; never echo their text
            raise GoogleError("exchange_failed") from exc
        scope = token.get("scope") or []
        scopes = scope.split() if isinstance(scope, str) else list(scope)
        email = ""
        if token.get("id_token"):
            try:
                claims = id_token.verify_oauth2_token(token["id_token"], Request(), audience=config.client_id)
                email = claims.get("email", "") if claims.get("email_verified", True) else ""
            except ValueError as exc:
                raise GoogleError("id_token_invalid") from exc
        return TokenGrant(
            refresh_token=token.get("refresh_token"),
            access_token=token.get("access_token", ""),
            scopes=scopes,
            email=email,
        )

    def credentials(self, config: OAuthClientConfig, refresh_token: str, scopes: list[str]):
        """Fresh short-lived access credentials; only ever held in memory."""
        from google.auth.exceptions import RefreshError, TransportError
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=config.client_id,
            client_secret=config.client_secret,
            token_uri=config.token_uri,
            scopes=scopes or settings.GOOGLE_OAUTH_SCOPES,
        )
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            if "invalid_grant" in str(exc) or "invalid_client" in str(exc):
                raise GoogleAuthRevoked() from exc
            raise GoogleError("refresh_failed") from exc
        except TransportError as exc:
            raise GoogleError("network_error") from exc
        return creds

    def drive(self, creds):
        from googleapiclient.discovery import build

        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def account_info(self, creds) -> AccountInfo:
        from googleapiclient.errors import HttpError

        try:
            about = self.drive(creds).about().get(fields="user(emailAddress,displayName),storageQuota").execute()
        except HttpError as exc:
            raise _drive_error(exc) from exc
        quota = about.get("storageQuota") or {}
        user = about.get("user") or {}
        return AccountInfo(
            email=user.get("emailAddress", ""),
            display_name=user.get("displayName", ""),
            quota_limit=int(quota["limit"]) if quota.get("limit") else None,
            quota_usage=int(quota["usage"]) if quota.get("usage") else None,
        )

    def revoke(self, token: str) -> None:
        import requests

        try:
            requests.post(REVOKE_URL, data={"token": token}, timeout=TIMEOUT)
        except requests.RequestException:
            pass  # best effort: we drop the token locally regardless

    # --- used by the self-test command (real Drive, drive.file semantics) ---------------
    def create_folder(self, creds, name: str, parent_id: str | None) -> dict:
        from googleapiclient.errors import HttpError

        body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            body["parents"] = [parent_id]
        try:
            return self.drive(creds).files().create(body=body, fields="id,name,parents").execute()
        except HttpError as exc:
            raise _drive_error(exc) from exc

    def create_text_file(self, creds, name: str, parent_id: str, content: bytes) -> dict:
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaInMemoryUpload

        media = MediaInMemoryUpload(content, mimetype="text/plain", resumable=False)
        try:
            return (
                self.drive(creds)
                .files()
                .create(body={"name": name, "parents": [parent_id]}, media_body=media, fields="id,name,parents,size")
                .execute()
            )
        except HttpError as exc:
            raise _drive_error(exc) from exc

    def get_file(self, creds, file_id: str) -> dict:
        from googleapiclient.errors import HttpError

        try:
            return (
                self.drive(creds)
                .files()
                .get(fileId=file_id, fields="id,name,mimeType,parents,capabilities(canAddChildren),trashed")
                .execute()
            )
        except HttpError as exc:
            raise _drive_error(exc) from exc

    def delete_file(self, creds, file_id: str) -> None:
        from googleapiclient.errors import HttpError

        try:
            self.drive(creds).files().delete(fileId=file_id).execute()
        except HttpError as exc:
            raise _drive_error(exc) from exc

    # --- media upload (Phase D): resumable sessions -------------------------------------
    def find_child_folder(self, creds, name: str, parent_id: str) -> str | None:
        """An app-created folder with ``name`` under ``parent_id`` (drive.file: only ours are visible)."""
        from googleapiclient.errors import HttpError

        safe = name.replace("\\", "\\\\").replace("'", "\\'")
        query = (
            f"name = '{safe}' and '{parent_id}' in parents and trashed = false "
            "and mimeType = 'application/vnd.google-apps.folder'"
        )
        try:
            found = self.drive(creds).files().list(q=query, fields="files(id)", pageSize=1).execute()
        except HttpError as exc:
            raise _drive_error(exc) from exc
        files = found.get("files") or []
        return files[0]["id"] if files else None

    def start_resumable_upload(
        self,
        creds,
        *,
        name: str,
        parent_id: str,
        mime_type: str,
        size: int,
        app_properties: dict,
        origin: str | None = None,
    ) -> str:
        """Open a resumable upload session for one file; returns the session URI.

        The URI authorizes uploading the bytes of *this one file* only (no OAuth token is shared),
        and expires after about a week. Google enforces the declared length.

        ``origin``: the browser origin that will PUT the bytes. Google only adds CORS headers to the
        *final* (200/201) response when the session was opened with that Origin (verified live
        2026-11-07); without it a browser upload succeeds in Drive but the page sees a network error.
        """
        import requests
        from google.auth.transport.requests import AuthorizedSession

        body = {"name": name, "parents": [parent_id], "mimeType": mime_type, "appProperties": app_properties}
        headers = {"X-Upload-Content-Type": mime_type, "X-Upload-Content-Length": str(size)}
        if origin:
            headers["Origin"] = origin
        try:
            res = AuthorizedSession(creds).post(
                f"{UPLOAD_URL}?uploadType=resumable&fields={FILE_FIELDS}",
                json=body,
                headers=headers,
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            raise GoogleError("network_error") from exc
        if res.status_code != 200 or not res.headers.get("Location"):
            raise _http_error(res)
        return res.headers["Location"]

    def upload_status(self, session_uri: str, size: int) -> "UploadProgress":
        """Ask Google how far a session got. Completed sessions return the created file."""
        import requests

        try:
            res = requests.put(
                session_uri, headers={"Content-Range": f"bytes */{size}", "Content-Length": "0"}, timeout=TIMEOUT
            )
        except requests.RequestException as exc:
            raise GoogleError("network_error") from exc
        if res.status_code in (200, 201):
            return UploadProgress(state="complete", received=size, file=res.json())
        if res.status_code == 308:
            # "Range: bytes=0-<last>" — absent when nothing arrived yet.
            last = (res.headers.get("Range") or "").rpartition("-")[2]
            return UploadProgress(state="in_progress", received=int(last) + 1 if last.isdigit() else 0)
        if res.status_code in (404, 410):
            return UploadProgress(state="expired", received=0)
        raise _http_error(res)

    def cancel_upload(self, session_uri: str) -> None:
        import requests

        try:
            requests.delete(session_uri, timeout=TIMEOUT)  # Google answers 499; best effort
        except requests.RequestException:
            pass

    def file_metadata(self, creds, file_id: str) -> dict:
        from googleapiclient.errors import HttpError

        try:
            return self.drive(creds).files().get(fileId=file_id, fields=FILE_FIELDS).execute()
        except HttpError as exc:
            raise _drive_error(exc) from exc

    # ---------------------------------------------------------- reading media
    def open_media(self, creds, file_id: str, byte_range: str | None = None) -> "MediaStream":
        """Stream a file's bytes (``alt=media``), forwarding one validated HTTP Range.

        Bytes flow Google → server → client chunk by chunk; nothing is buffered whole. The caller
        must exhaust or ``close()`` the stream.
        """
        import requests
        from google.auth.transport.requests import AuthorizedSession

        headers = {"Range": byte_range} if byte_range else {}
        try:
            res = AuthorizedSession(creds).get(
                f"{FILES_URL}/{file_id}?alt=media", headers=headers, stream=True, timeout=(TIMEOUT, 120)
            )
        except requests.RequestException as exc:
            raise GoogleError("network_error") from exc
        if res.status_code not in (200, 206, 416):
            try:
                raise _http_error(res)
            finally:
                res.close()
        kept = {k: res.headers[k] for k in ("Content-Length", "Content-Range") if k in res.headers}
        return MediaStream(status=res.status_code, headers=kept, chunks=res.iter_content(MEDIA_CHUNK), close=res.close)

    def download_to_file(self, creds, file_id: str, path) -> int:
        """Copy a Drive file's bytes to a local path (server-side processing). Returns the byte count."""
        stream = self.open_media(creds, file_id)
        written = 0
        try:
            with open(path, "wb") as out:
                for chunk in stream.chunks:
                    out.write(chunk)
                    written += len(chunk)
        finally:
            stream.close()
        return written

    def upload_file(self, creds, *, name: str, parent_id: str, path, mime_type: str, app_properties: dict) -> dict:
        """Upload a local file into a platform folder (resumable, 8 MiB chunks). Returns its metadata."""
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(str(path), mimetype=mime_type, resumable=True, chunksize=8 * 1024 * 1024)
        body = {"name": name, "parents": [parent_id], "mimeType": mime_type, "appProperties": app_properties}
        try:
            request = self.drive(creds).files().create(body=body, media_body=media, fields=FILE_FIELDS)
            response = None
            while response is None:
                _, response = request.next_chunk(num_retries=3)
            return response
        except HttpError as exc:
            raise _drive_error(exc) from exc

    def thumbnail(self, creds, file_id: str, size: int) -> tuple[bytes, str] | None:
        """A Drive-generated preview image (photos and most videos), or ``None`` if Drive has none yet."""
        import re

        import requests
        from google.auth.transport.requests import AuthorizedSession
        from googleapiclient.errors import HttpError

        try:
            meta = self.drive(creds).files().get(fileId=file_id, fields="thumbnailLink").execute()
        except HttpError as exc:
            raise _drive_error(exc) from exc
        link = meta.get("thumbnailLink")
        if not link:
            return None
        link = re.sub(r"=s\d+$", f"=s{size}", link)
        try:
            res = AuthorizedSession(creds).get(link, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise GoogleError("network_error") from exc
        if res.status_code != 200 or not res.headers.get("Content-Type", "").startswith("image/"):
            return None
        return res.content, res.headers["Content-Type"]


UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
FILES_URL = "https://www.googleapis.com/drive/v3/files"
MEDIA_CHUNK = 256 * 1024
FILE_FIELDS = (
    "id,name,mimeType,size,md5Checksum,parents,appProperties,trashed,"
    "imageMediaMetadata(width,height),videoMediaMetadata(width,height,durationMillis)"
)


@dataclass
class UploadProgress:
    state: str  # in_progress | complete | expired
    received: int
    file: dict | None = None


@dataclass
class MediaStream:
    status: int  # 200 | 206 | 416
    headers: dict
    chunks: object  # iterator of bytes
    close: object  # callable


def _http_error(res) -> GoogleError:
    """Map a raw ``requests`` response from the Drive upload endpoint like ``_drive_error``."""

    class _Shim:
        def __init__(self, response):
            self.resp = type("R", (), {"status": response.status_code})()
            self.content = response.content or b"{}"

    return _drive_error(_Shim(res))
