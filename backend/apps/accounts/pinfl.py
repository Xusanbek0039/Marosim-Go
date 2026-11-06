"""JSHSHIR (PINFL) — Uzbekistan's 14-digit personal identification number.

Only these helpers ever see the plaintext. It is stored encrypted, indexed by a keyed hash
and shown masked (last 4 digits only — the leading digits encode sex and birth date).
"""

import re

from django.core.exceptions import ValidationError

from apps.core import crypto

PINFL_RE = re.compile(r"^\d{14}$")
MASK = "*" * 10


def normalize(raw: str) -> str:
    return re.sub(r"[\s-]", "", str(raw or ""))


def validate(raw: str) -> str:
    value = normalize(raw)
    if not PINFL_RE.fullmatch(value):
        raise ValidationError("JSHSHIR 14 ta raqamdan iborat bo'lishi kerak.", code="invalid_pinfl")
    if len(set(value)) == 1:
        raise ValidationError("JSHSHIR noto'g'ri.", code="invalid_pinfl")
    return value


def hash_of(value: str) -> str:
    return crypto.blind_index(normalize(value))


def mask(last4: str | None) -> str | None:
    return f"{MASK}{last4}" if last4 else None
