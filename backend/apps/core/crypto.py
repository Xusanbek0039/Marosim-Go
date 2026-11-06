"""Application-level encryption helpers for sensitive personal data.

* ``encrypt``/``decrypt`` use ``MultiFernet`` (AES-128-CBC + HMAC-SHA256). The first key in
  ``PINFL_ENCRYPTION_KEYS`` encrypts; every listed key can decrypt, so keys can be rotated.
* ``blind_index`` is a keyed HMAC-SHA256 used for uniqueness checks and exact-match search
  without ever storing or comparing the plaintext.
"""

import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fernet() -> MultiFernet:
    keys = [k.strip() for k in settings.PINFL_ENCRYPTION_KEYS if k.strip()]
    if not keys:
        raise ImproperlyConfigured("PINFL_ENCRYPTION_KEYS is empty.")
    return MultiFernet([Fernet(k.encode()) for k in keys])


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:  # wrong/rotated-out key or tampered data
        raise ValueError("Encrypted value cannot be decrypted with the configured keys.") from exc


def rotate(token: str) -> str:
    """Re-encrypt ``token`` with the current primary key."""
    return _fernet().rotate(token.encode()).decode()


def blind_index(value: str) -> str:
    key = settings.PINFL_HASH_KEY.encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()
