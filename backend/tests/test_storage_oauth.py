import json
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.models import AuditAction, AuditLog
from apps.monitoring.models import RequestLog
from apps.storage import client_config, services, vault
from apps.storage.google import DRIVE_FILE_SCOPE, AccountInfo, GoogleAuthRevoked, GoogleError, TokenGrant
from apps.storage.models import ConnectionStatus, OAuthState, StorageConnection, StorageCredential, digest

BASE = "/api/v1/admin/storage/google"
CONNECT, CALLBACK, STATUS, TEST, DISCONNECT = (
    f"{BASE}/{p}/" for p in ("connect", "callback", "status", "test", "disconnect")
)
REFRESH_TOKEN = "1//fake-refresh-token-SECRET-value"
ACCESS_TOKEN = "ya29.fake-access-token-SECRET"


class FakeGoogle:
    """Stands in for GoogleGateway — records calls, never touches the network."""

    def __init__(self):
        self.grant = TokenGrant(
            refresh_token=REFRESH_TOKEN,
            access_token=ACCESS_TOKEN,
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", DRIVE_FILE_SCOPE],
            email="owner@gmail.com",
        )
        self.exchange_error: GoogleError | None = None
        self.refresh_error: GoogleError | None = None
        self.about_error: GoogleError | None = None
        self.exchanged: list[tuple[str, str]] = []
        self.refreshed: list[str] = []
        self.revoked: list[str] = []
        self.auth_kwargs: dict = {}

    def authorization_url(self, config, state, code_verifier):
        self.auth_kwargs = {"state": state, "code_verifier": code_verifier}
        return f"https://accounts.google.com/o/oauth2/auth?state={state}&access_type=offline&prompt=consent"

    def exchange_code(self, config, code, code_verifier):
        self.exchanged.append((code, code_verifier))
        if self.exchange_error:
            raise self.exchange_error
        return self.grant

    def credentials(self, config, refresh_token, scopes):
        self.refreshed.append(refresh_token)
        if self.refresh_error:
            raise self.refresh_error
        return object()

    def account_info(self, creds):
        if self.about_error:
            raise self.about_error
        return AccountInfo(email="owner@gmail.com", quota_limit=15 * 1024**3, quota_usage=1024)

    def revoke(self, token):
        self.revoked.append(token)


@pytest.fixture
def google():
    fake = FakeGoogle()
    services.set_gateway(fake)
    yield fake
    services.set_gateway(None)


def start(client):
    res = client.get(CONNECT)
    assert res.status_code == 200, res.data
    state = parse_qs(urlparse(res.data["authorization_url"]).query)["state"][0]
    return res, state


def callback(client, **params):
    return client.get(CALLBACK, params)


def connect_fully(client, google):
    _, state = start(client)
    return callback(client, state=state, code="auth-code-123")


# ------------------------------------------------------------- config loading
def write_client_json(tmp_path, data):
    path = tmp_path / "google_oauth_client.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


WEB = {
    "web": {
        "client_id": "1022061897605-abc.apps.googleusercontent.com",
        "client_secret": "fake-client-secret-very-secret",
        "project_id": "marosimgo",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8000/api/v1/admin/storage/google/callback/"],
    }
}


def test_client_json_loaded_and_secret_never_in_repr(tmp_path):
    path = write_client_json(tmp_path, WEB)
    with override_settings(GOOGLE_OAUTH_CLIENT_FILE=path, GOOGLE_OAUTH_CLIENT_ID="", GOOGLE_OAUTH_CLIENT_SECRET=""):
        config = client_config.load()
        report = client_config.diagnose()
    assert config.source == "file" and config.project_number == "1022061897605"
    assert "very-secret" not in repr(config) and "very-secret" not in str(config)
    assert "very-secret" not in json.dumps(report)
    assert report["configured"] is True


@pytest.mark.parametrize(
    "data,code",
    [
        ({"installed": WEB["web"]}, "client_type_invalid"),
        ({"web": {**WEB["web"], "client_secret": ""}}, "client_fields_missing"),
        ({"web": {**WEB["web"], "redirect_uris": ["http://localhost:9999/cb/"]}}, "redirect_uri_mismatch"),
    ],
)
def test_client_json_problems_are_reported_by_code(tmp_path, data, code):
    path = write_client_json(tmp_path, data)
    with override_settings(GOOGLE_OAUTH_CLIENT_FILE=path, GOOGLE_OAUTH_CLIENT_ID="", GOOGLE_OAUTH_CLIENT_SECRET=""):
        with pytest.raises(client_config.ClientConfigError) as exc:
            client_config.load()
    assert exc.value.code == code
    assert "very-secret" not in exc.value.message


def test_missing_client_json(tmp_path):
    with override_settings(
        GOOGLE_OAUTH_CLIENT_FILE=tmp_path / "nope.json", GOOGLE_OAUTH_CLIENT_ID="", GOOGLE_OAUTH_CLIENT_SECRET=""
    ):
        report = client_config.diagnose()
    assert report["configured"] is False
    assert report["issues"][0]["code"] == "client_file_missing"


# ------------------------------------------------------------------ vault
def test_token_encryption_roundtrip_and_rotation():
    sealed = vault.seal(REFRESH_TOKEN)
    assert REFRESH_TOKEN not in sealed and vault.unseal(sealed) == REFRESH_TOKEN
    from cryptography.fernet import Fernet

    new_key = Fernet.generate_key().decode()
    old_keys = list(__import__("django.conf").conf.settings.GOOGLE_TOKEN_ENCRYPTION_KEYS)
    with override_settings(GOOGLE_TOKEN_ENCRYPTION_KEYS=[new_key, *old_keys]):
        assert vault.unseal(sealed) == REFRESH_TOKEN  # old key still decrypts
        rotated = vault.reseal(sealed)
    with override_settings(GOOGLE_TOKEN_ENCRYPTION_KEYS=[new_key]):
        assert vault.unseal(rotated) == REFRESH_TOKEN
        with pytest.raises(vault.VaultNotConfigured):
            vault.unseal(sealed)  # the retired key is gone


def test_vault_rejects_invalid_key():
    with override_settings(GOOGLE_TOKEN_ENCRYPTION_KEYS=["too-short"]):
        assert vault.is_configured() is False


# ------------------------------------------------------------------- RBAC
@pytest.mark.django_db
@pytest.mark.parametrize("url,method", [(CONNECT, "get"), (STATUS, "get"), (TEST, "post"), (DISCONNECT, "post")])
def test_only_super_admin_can_manage_storage(url, method, make_user, client_for, anon, google):
    full_admin = make_user(Role.ADMIN, admin_permissions=["dashboard.view", "users.view", "studios.view"])
    assert getattr(anon, method)(url).status_code == 401
    for user in (full_admin, make_user(Role.STUDIO), make_user(Role.USER)):
        assert getattr(client_for(user), method)(url).status_code == 403
    assert not OAuthState.objects.exists()


# ---------------------------------------------------------------- connect
@pytest.mark.django_db
def test_connect_issues_hashed_single_use_state_with_pkce_and_binding_cookie(super_admin, client_for, google):
    client = client_for(super_admin)
    res, state = start(client)
    url = res.data["authorization_url"]
    assert url.startswith("https://accounts.google.com/") and "access_type=offline" in url

    row = OAuthState.objects.get()
    assert row.state_hash == digest(state) and state not in json.dumps(list(OAuthState.objects.values()), default=str)
    assert vault.unseal(row.code_verifier_encrypted) == google.auth_kwargs["code_verifier"]
    assert 43 <= len(google.auth_kwargs["code_verifier"]) <= 128
    assert row.expires_at > timezone.now() and row.initiated_by == super_admin

    cookie = res.cookies[services.BINDING_COOKIE]
    assert cookie["httponly"] and cookie["samesite"] == "Lax" and cookie["path"] == services.BINDING_COOKIE_PATH
    assert digest(cookie.value) == row.binding_hash


@pytest.mark.django_db
def test_connect_reports_missing_configuration(super_admin, client_for, google, tmp_path):
    with override_settings(
        GOOGLE_OAUTH_CLIENT_FILE=tmp_path / "x.json", GOOGLE_OAUTH_CLIENT_ID="", GOOGLE_OAUTH_CLIENT_SECRET=""
    ):
        res = client_for(super_admin).get(CONNECT)
    assert res.status_code == 503 and res.data["error"]["code"] == "client_file_missing"


# --------------------------------------------------------------- callback
@pytest.mark.django_db
def test_callback_success_stores_encrypted_token_only(super_admin, client_for, google):
    client = client_for(super_admin)
    res = connect_fully(client, google)
    assert res.status_code == 302
    assert res["Location"] == "http://localhost:3000/storage?google=connected"
    assert res.cookies[services.BINDING_COOKIE].value == ""  # binding cookie cleared

    conn = StorageConnection.objects.get()
    assert conn.status == ConnectionStatus.CONNECTED and conn.account_email == "owner@gmail.com"
    assert DRIVE_FILE_SCOPE in conn.scopes and conn.connected_by == super_admin
    cred = StorageCredential.objects.get()
    assert (
        REFRESH_TOKEN not in cred.refresh_token_encrypted
        and vault.unseal(cred.refresh_token_encrypted) == REFRESH_TOKEN
    )
    assert REFRESH_TOKEN not in repr(cred)
    assert google.exchanged[0][0] == "auth-code-123"
    assert AuditLog.objects.filter(action=AuditAction.STORAGE_CONNECT).exists()
    audit_dump = json.dumps(list(AuditLog.objects.values("changes")), default=str)
    assert REFRESH_TOKEN not in audit_dump and ACCESS_TOKEN not in audit_dump


@pytest.mark.django_db
def test_status_never_exposes_tokens(super_admin, client_for, google):
    client = client_for(super_admin)
    connect_fully(client, google)
    res = client.get(STATUS)
    assert res.status_code == 200
    body = json.dumps(res.data, default=str)
    assert res.data["connection"]["status"] == "CONNECTED" and res.data["has_credential"] is True
    for secret in (REFRESH_TOKEN, ACCESS_TOKEN, "refresh_token", "test-client-secret"):
        assert secret not in body


@pytest.mark.django_db
def test_callback_rejects_unknown_state(super_admin, client_for, google):
    res = callback(client_for(super_admin), state="forged-state", code="x")
    assert "reason=state_invalid" in res["Location"]
    assert not StorageCredential.objects.exists() and not google.exchanged


@pytest.mark.django_db
def test_callback_state_is_single_use(super_admin, client_for, google):
    client = client_for(super_admin)
    _, state = start(client)
    binding = client.cookies[services.BINDING_COOKIE].value
    assert "google=connected" in callback(client, state=state, code="c1")["Location"]
    client.cookies[services.BINDING_COOKIE] = binding  # replay with the original cookie
    assert "reason=state_reused" in callback(client, state=state, code="c2")["Location"]
    assert len(google.exchanged) == 1


@pytest.mark.django_db
def test_callback_rejects_expired_state(super_admin, client_for, google):
    client = client_for(super_admin)
    _, state = start(client)
    OAuthState.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert "reason=state_expired" in callback(client, state=state, code="c")["Location"]
    assert not google.exchanged


@pytest.mark.django_db
def test_callback_requires_the_initiating_browser(super_admin, client_for, google):
    """Login-CSRF / account-linking attack: a valid state replayed from another browser fails."""
    _, state = start(client_for(super_admin))
    other_browser = client_for(super_admin)  # no binding cookie
    res = callback(other_browser, state=state, code="attacker-code")
    assert "reason=binding_mismatch" in res["Location"]
    assert not google.exchanged
    assert AuditLog.objects.filter(action=AuditAction.STORAGE_CONNECT_FAILED, changes__code="binding_mismatch").exists()
    # ...and the state is burned, so it cannot be retried with a stolen cookie either.
    assert OAuthState.objects.get().used_at is not None


@pytest.mark.django_db
def test_callback_rejects_initiator_who_lost_super_admin(super_admin, client_for, google):
    client = client_for(super_admin)
    _, state = start(client)
    type(super_admin).objects.filter(pk=super_admin.pk).update(is_active=False)
    assert "reason=forbidden" in callback(client, state=state, code="c")["Location"]
    assert not StorageCredential.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mutate,reason",
    [
        (lambda g: setattr(g.grant, "refresh_token", None), "no_refresh_token"),
        (lambda g: setattr(g.grant, "scopes", ["openid"]), "scope_denied"),
        (lambda g: setattr(g, "exchange_error", GoogleError("exchange_failed")), "exchange_failed"),
    ],
)
def test_callback_failures(super_admin, client_for, google, mutate, reason):
    mutate(google)
    res = connect_fully(client_for(super_admin), google)
    assert f"reason={reason}" in res["Location"]
    assert not StorageCredential.objects.exists()


@pytest.mark.django_db
def test_callback_user_denied_consent(super_admin, client_for, google):
    client = client_for(super_admin)
    _, state = start(client)
    assert "reason=access_denied" in callback(client, state=state, error="access_denied")["Location"]
    assert not google.exchanged


@pytest.mark.django_db
def test_callback_is_public_but_never_logs_code_or_state(super_admin, client_for, google):
    client = client_for(super_admin)
    _, state = start(client)
    callback(client, state=state, code="auth-code-SECRET")
    dump = json.dumps(list(RequestLog.objects.values()), default=str)
    assert "auth-code-SECRET" not in dump and state not in dump
    assert RequestLog.objects.filter(route=CALLBACK, status_code=302).exists()


def test_log_redaction_of_oauth_query():
    from apps.core.logging import redact

    line = '"GET /api/v1/admin/storage/google/callback/?state=abc123&code=4/0AQSecret&scope=x HTTP/1.1" 302'
    out = redact(line)
    assert "abc123" not in out and "4/0AQSecret" not in out
    assert redact("status_code=200") == "status_code=200"


@pytest.mark.django_db
def test_reconnect_with_other_account_clears_root_folder(super_admin, client_for, google):
    client = client_for(super_admin)
    connect_fully(client, google)
    StorageConnection.objects.update(root_folder_id="folder-of-owner")
    google.grant.email = "someone.else@gmail.com"
    connect_fully(client, google)
    conn = StorageConnection.objects.get()
    assert conn.account_email == "someone.else@gmail.com" and conn.root_folder_id == ""
    assert StorageCredential.objects.count() == 1


# ------------------------------------------------------- refresh / test
@pytest.mark.django_db
def test_test_connection_refreshes_token(super_admin, client_for, google):
    client = client_for(super_admin)
    connect_fully(client, google)
    StorageConnection.objects.update(last_success_at=None)
    res = client.post(TEST)
    assert res.status_code == 200 and res.data["ok"] is True and res.data["quota_limit"] == 15 * 1024**3
    assert google.refreshed == [REFRESH_TOKEN]
    assert StorageConnection.objects.get().last_success_at is not None
    assert ACCESS_TOKEN not in json.dumps(res.data, default=str)


@pytest.mark.django_db
def test_revoked_or_expired_refresh_token_requires_reconnect(super_admin, client_for, google):
    client = client_for(super_admin)
    connect_fully(client, google)
    google.refresh_error = GoogleAuthRevoked()
    res = client.post(TEST)
    assert res.status_code == 409 and res.data["error"]["code"] == "reconnect_required"
    conn = StorageConnection.objects.get()
    assert conn.status == ConnectionStatus.RECONNECT_REQUIRED and conn.last_error_code == "invalid_grant"
    assert client.get(STATUS).data["connection"]["status"] == "RECONNECT_REQUIRED"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "code", ["insufficient_permissions", "storage_quota_exceeded", "rate_limited", "drive_api_disabled"]
)
def test_google_api_errors_are_mapped(super_admin, client_for, google, code):
    client = client_for(super_admin)
    connect_fully(client, google)
    google.about_error = GoogleError(code, 403)
    res = client.post(TEST)
    assert res.data["error"]["code"] == code
    conn = StorageConnection.objects.get()
    assert conn.status == ConnectionStatus.ERROR and conn.last_error_code == code


@pytest.mark.django_db
def test_lost_credential_marks_reconnect(super_admin, client_for, google):
    client = client_for(super_admin)
    connect_fully(client, google)
    StorageCredential.objects.all().delete()
    assert client.post(TEST).data["error"]["code"] == "not_connected"
    assert StorageConnection.objects.get().status == ConnectionStatus.RECONNECT_REQUIRED


@pytest.mark.django_db
def test_test_connection_when_never_connected(super_admin, client_for, google):
    res = client_for(super_admin).post(TEST)
    assert res.status_code == 409 and res.data["error"]["code"] == "not_connected"


# -------------------------------------------------------------- disconnect
@pytest.mark.django_db
def test_disconnect_revokes_and_forgets_token(super_admin, client_for, google):
    client = client_for(super_admin)
    connect_fully(client, google)
    res = client.post(DISCONNECT)
    assert res.status_code == 200 and res.data["status"] == "DISCONNECTED"
    assert google.revoked == [REFRESH_TOKEN]
    assert not StorageCredential.objects.exists()
    assert AuditLog.objects.filter(action=AuditAction.STORAGE_DISCONNECT).exists()


# ------------------------------------------------------------------ docs
@pytest.mark.django_db
def test_storage_endpoints_are_documented(super_admin, client_for):
    from apps.monitoring import catalog

    catalog.reset_cache()
    paths = catalog.get_schema()["paths"]
    for url in (CONNECT, CALLBACK, STATUS, TEST, DISCONNECT):
        assert url in paths
    assert paths[CALLBACK]["get"]["x-access"]["auth_required"] is False
    assert paths[CONNECT]["get"]["x-access"]["roles"] == ["SUPER_ADMIN"]


# ------------------------------------------------- real gateway, offline parts
def test_real_gateway_builds_offline_pkce_consent_url():
    from apps.storage.google import GoogleGateway

    config = client_config.load()
    url = GoogleGateway().authorization_url(config, "the-state", "v" * 64)
    q = parse_qs(urlparse(url).query)
    assert url.startswith("https://accounts.google.com/o/oauth2/auth?")
    assert q["access_type"] == ["offline"] and q["prompt"] == ["consent"]
    assert q["state"] == ["the-state"] and q["response_type"] == ["code"]
    assert q["code_challenge_method"] == ["S256"] and q["code_challenge"][0] != "v" * 64
    assert q["redirect_uri"] == ["http://localhost:8000/api/v1/admin/storage/google/callback/"]
    assert DRIVE_FILE_SCOPE in q["scope"][0].split()
    assert "https://www.googleapis.com/auth/drive " not in q["scope"][0] + " "  # never the broad scope
    assert "test-client-secret" not in url


@pytest.mark.parametrize(
    "status,reason,code",
    [
        (403, "storageQuotaExceeded", "storage_quota_exceeded"),
        (403, "insufficientFilePermissions", "insufficient_permissions"),
        (403, "accessNotConfigured", "drive_api_disabled"),
        (429, "", "rate_limited"),
        (404, "notFound", "not_found"),
        (503, "", "google_unavailable"),
    ],
)
def test_drive_http_errors_are_normalized(status, reason, code):
    import httplib2
    from googleapiclient.errors import HttpError

    from apps.storage.google import _drive_error

    body = json.dumps({"error": {"code": status, "errors": [{"reason": reason}] if reason else []}}).encode()
    err = _drive_error(HttpError(httplib2.Response({"status": status}), body))
    assert err.code == code and err.status == status
