"""Google Drive connection lifecycle (Phase A).

Connect:   Super Admin (JWT) → ``start_connect`` → Google consent URL + a browser-binding cookie.
Callback:  Google redirects the *browser* (no JWT) → ``complete_callback`` verifies, in order:
           state exists · unused · unexpired (consumed atomically) → binding cookie matches →
           initiator is still an active SUPER_ADMIN → Google did not report an error →
           code exchange (PKCE) → refresh token present → drive.file granted.
Refresh:   ``access_credentials`` exchanges the stored refresh token for an in-memory access token;
           ``invalid_grant`` flips the connection to RECONNECT_REQUIRED.
"""

import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.services import AuditAction, record

from . import client_config, vault
from .google import DRIVE_FILE_SCOPE, AccountInfo, GoogleAuthRevoked, GoogleError, GoogleGateway
from .models import ConnectionStatus, OAuthState, Provider, StorageConnection, StorageCredential, digest

logger = logging.getLogger("apps.storage")

BINDING_COOKIE = "mg_oauth_bind"
BINDING_COOKIE_PATH = "/api/v1/admin/storage/google/"

_gateway: GoogleGateway | None = None


def gateway() -> GoogleGateway:
    global _gateway
    if _gateway is None:
        _gateway = GoogleGateway()
    return _gateway


def set_gateway(value: GoogleGateway | None) -> None:
    """Tests inject a fake provider here."""
    global _gateway
    _gateway = value


class StorageError(Exception):
    """A failure with a stable, non-secret code (shown to the Super Admin)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def connection() -> StorageConnection:
    conn, _ = StorageConnection.objects.get_or_create(
        provider=Provider.GOOGLE_DRIVE,
        defaults={"root_folder_id": settings.GOOGLE_DRIVE_ROOT_FOLDER_ID},
    )
    return conn


# ------------------------------------------------------------------ connect
@dataclass
class ConnectStart:
    authorization_url: str
    binding: str
    expires_at: object


def start_connect(user) -> ConnectStart:
    try:
        config = client_config.load()
    except client_config.ClientConfigError as exc:
        raise StorageError(exc.code) from None
    if not vault.is_configured():
        raise StorageError("encryption_key_missing")

    state = secrets.token_urlsafe(32)
    binding = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)  # 86 chars, within PKCE's 43–128
    expires_at = timezone.now() + timedelta(seconds=settings.GOOGLE_OAUTH_STATE_TTL_SECONDS)
    OAuthState.objects.filter(expires_at__lt=timezone.now() - timedelta(days=1)).delete()
    OAuthState.objects.create(
        state_hash=digest(state),
        binding_hash=digest(binding),
        code_verifier_encrypted=vault.seal(code_verifier),
        initiated_by=user,
        expires_at=expires_at,
    )
    url = gateway().authorization_url(config, state, code_verifier)
    return ConnectStart(authorization_url=url, binding=binding, expires_at=expires_at)


def _consume_state(state: str) -> OAuthState:
    if not state:
        raise StorageError("state_missing")
    now = timezone.now()
    with transaction.atomic():
        row = OAuthState.objects.select_for_update().filter(state_hash=digest(state)).first()
        if row is None:
            raise StorageError("state_invalid")
        if row.used_at is not None:
            raise StorageError("state_reused")
        # Consume before any further check: a state can never be tried twice.
        claimed = OAuthState.objects.filter(pk=row.pk, used_at__isnull=True).update(used_at=now)
        if not claimed:
            raise StorageError("state_reused")
    if row.expires_at < now:
        raise StorageError("state_expired")
    return row


def complete_callback(request, *, state: str, code: str, error: str, binding: str | None) -> StorageConnection:
    row = _consume_state(state)
    user = row.initiated_by
    try:
        if not binding or not hmac.compare_digest(digest(binding), row.binding_hash):
            raise StorageError("binding_mismatch")
        if not (user.is_active and not user.is_deleted and user.role == Role.SUPER_ADMIN):
            raise StorageError("forbidden")
        if error:
            raise StorageError("access_denied" if error == "access_denied" else "google_error")
        if not code:
            raise StorageError("code_missing")

        config = client_config.load()
        try:
            grant = gateway().exchange_code(config, code, vault.unseal(row.code_verifier_encrypted))
        except GoogleError as exc:
            raise StorageError(exc.code) from None
        if not grant.refresh_token:
            raise StorageError("no_refresh_token")
        if DRIVE_FILE_SCOPE not in grant.scopes:
            raise StorageError("scope_denied")  # owner unticked the Drive checkbox
    except StorageError as exc:
        record(request, AuditAction.STORAGE_CONNECT_FAILED, None, actor=user, changes={"code": exc.code})
        raise
    except client_config.ClientConfigError as exc:
        record(request, AuditAction.STORAGE_CONNECT_FAILED, None, actor=user, changes={"code": exc.code})
        raise StorageError(exc.code) from None

    with transaction.atomic():
        conn = connection()
        if conn.account_email and grant.email and conn.account_email != grant.email:
            # A different Google account: the old root folder belongs to someone else's Drive.
            conn.root_folder_id = ""
            conn.root_folder_name = ""
        conn.account_email = grant.email
        conn.scopes = sorted(set(grant.scopes))
        conn.status = ConnectionStatus.CONNECTED
        conn.connected_by = user
        conn.connected_at = conn.last_success_at = conn.last_checked_at = timezone.now()
        conn.last_error_code = ""
        conn.save()
        StorageCredential.objects.update_or_create(
            connection=conn, defaults={"refresh_token_encrypted": vault.seal(grant.refresh_token)}
        )
        record(
            request,
            AuditAction.STORAGE_CONNECT,
            conn,
            actor=user,
            changes={"account": grant.email, "scopes": conn.scopes},
        )
    return conn


# ----------------------------------------------------------------- tokens
def _mark(conn: StorageConnection, status: str, code: str = "") -> None:
    conn.status = status
    conn.last_error_code = code
    conn.last_checked_at = timezone.now()
    if status == ConnectionStatus.CONNECTED:
        conn.last_success_at = conn.last_checked_at
    conn.save(update_fields=["status", "last_error_code", "last_checked_at", "last_success_at", "updated_at"])


def access_credentials(conn: StorageConnection | None = None):
    """In-memory Google credentials for API calls. Raises ``StorageError`` with a code."""
    conn = conn or connection()
    credential = StorageCredential.objects.filter(connection=conn).first()
    if credential is None:
        if conn.status == ConnectionStatus.CONNECTED:
            _mark(conn, ConnectionStatus.RECONNECT_REQUIRED, "credential_missing")
        raise StorageError("not_connected")
    try:
        refresh_token = vault.unseal(credential.refresh_token_encrypted)
    except vault.VaultNotConfigured:
        _mark(conn, ConnectionStatus.ERROR, "encryption_key_invalid")
        raise StorageError("encryption_key_invalid") from None
    try:
        return gateway().credentials(client_config.load(), refresh_token, conn.scopes)
    except GoogleAuthRevoked:
        _mark(conn, ConnectionStatus.RECONNECT_REQUIRED, "invalid_grant")
        raise StorageError("reconnect_required") from None
    except GoogleError as exc:
        _mark(conn, ConnectionStatus.ERROR, exc.code)
        raise StorageError(exc.code) from None
    except client_config.ClientConfigError as exc:
        _mark(conn, ConnectionStatus.ERROR, exc.code)
        raise StorageError(exc.code) from None


def test_connection(request=None) -> AccountInfo:
    conn = connection()
    creds = access_credentials(conn)
    try:
        info = gateway().account_info(creds)
    except GoogleError as exc:
        _mark(conn, ConnectionStatus.ERROR, exc.code)
        raise StorageError(exc.code) from None
    if info.email and conn.account_email and info.email != conn.account_email:
        _mark(conn, ConnectionStatus.ERROR, "account_mismatch")
        raise StorageError("account_mismatch")
    _mark(conn, ConnectionStatus.CONNECTED)
    return info


def disconnect(request, user) -> StorageConnection:
    conn = connection()
    credential = StorageCredential.objects.filter(connection=conn).first()
    if credential is not None:
        try:
            gateway().revoke(vault.unseal(credential.refresh_token_encrypted))
        except vault.VaultNotConfigured:
            pass  # cannot decrypt → cannot revoke remotely; still forget it locally
        credential.delete()
    previous = conn.account_email
    conn.status = ConnectionStatus.DISCONNECTED
    conn.last_error_code = ""
    conn.scopes = []
    conn.save(update_fields=["status", "last_error_code", "scopes", "updated_at"])
    record(request, AuditAction.STORAGE_DISCONNECT, conn, actor=user, changes={"account": previous})
    return conn
