"""Encryption for storage secrets (OAuth refresh tokens, PKCE verifiers, resumable session URIs later).

A dedicated key set (``GOOGLE_TOKEN_ENCRYPTION_KEY``) — separate from the PINFL keys, so one
leak does not expose the other. ``MultiFernet``: the first key encrypts, every key decrypts.
"""

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings


class VaultNotConfigured(Exception):
    """No (valid) GOOGLE_TOKEN_ENCRYPTION_KEY — storage stays disabled, the rest of the API works."""


def _fernet() -> MultiFernet:
    keys = [k.strip() for k in settings.GOOGLE_TOKEN_ENCRYPTION_KEYS if k.strip()]
    if not keys:
        raise VaultNotConfigured("GOOGLE_TOKEN_ENCRYPTION_KEY is not set.")
    try:
        return MultiFernet([Fernet(k.encode()) for k in keys])
    except ValueError:
        raise VaultNotConfigured("GOOGLE_TOKEN_ENCRYPTION_KEY is not a valid Fernet key.") from None


def is_configured() -> bool:
    try:
        _fernet()
    except VaultNotConfigured:
        return False
    return True


def seal(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def unseal(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        raise VaultNotConfigured("Stored secret cannot be decrypted with the configured keys.") from None


def reseal(token: str) -> str:
    """Re-encrypt with the current primary key (after a key rotation)."""
    return _fernet().rotate(token.encode()).decode()
