"""Storage connection state.

* ``StorageConnection`` — public, non-secret facts (account, status, root folder). Serializable.
* ``StorageCredential`` — the encrypted refresh token, in its own table, never serialized.
* ``OAuthState`` — one pending authorization attempt: only *hashes* of the state and the browser
  binding nonce are stored, plus the encrypted PKCE verifier. Single use, short-lived.
"""

import hashlib
import uuid

from django.conf import settings
from django.db import models


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Provider(models.TextChoices):
    GOOGLE_DRIVE = "GOOGLE_DRIVE", "Google Drive"


class ConnectionStatus(models.TextChoices):
    DISCONNECTED = "DISCONNECTED", "Ulanmagan"
    CONNECTED = "CONNECTED", "Ulangan"
    RECONNECT_REQUIRED = "RECONNECT_REQUIRED", "Qayta ulash kerak"
    ERROR = "ERROR", "Xatolik"


class StorageConnection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=32, choices=Provider.choices, unique=True)
    account_email = models.EmailField(blank=True)
    root_folder_id = models.CharField(max_length=128, blank=True)
    root_folder_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=24, choices=ConnectionStatus.choices, default=ConnectionStatus.DISCONNECTED)
    scopes = models.JSONField(default=list, blank=True)
    connected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    connected_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.provider} {self.status} {self.account_email or '-'}"

    @property
    def has_credential(self) -> bool:
        return StorageCredential.objects.filter(connection=self).exists()


class StorageCredential(models.Model):
    connection = models.OneToOneField(StorageConnection, on_delete=models.CASCADE, related_name="credential")
    refresh_token_encrypted = models.TextField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __repr__(self) -> str:  # never let the ciphertext slip into tracebacks/logs either
        return f"<StorageCredential connection={self.connection_id}>"

    __str__ = __repr__


class OAuthState(models.Model):
    id = models.BigAutoField(primary_key=True)
    state_hash = models.CharField(max_length=64, unique=True)
    binding_hash = models.CharField(max_length=64)
    code_verifier_encrypted = models.TextField()
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    provider = models.CharField(max_length=32, choices=Provider.choices, default=Provider.GOOGLE_DRIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"OAuthState #{self.pk} by {self.initiated_by_id}"
