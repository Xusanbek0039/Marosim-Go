"""Phone numbers — the login identifier of every account.

Stored as an E.164 string (``+998901234567``). Every entry point (serializers, manager,
management commands, login) goes through :func:`normalize`, so the unique constraint on
``User.phone_number`` compares canonical values only.

Accepted inputs (Uzbekistan by default, see ``PHONE_ALLOWED_REGIONS``)::

    901234567       -> +998901234567
    998901234567    -> +998901234567
    +998 90 123-45-67 -> +998901234567
"""

import hashlib
import re

import phonenumbers
from django.conf import settings
from django.core.exceptions import ValidationError

INVALID_MESSAGE = "Telefon raqam noto'g'ri. Masalan: +998901234567"
E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")
_JUNK_RE = re.compile(r"[\s\-().]")


def _regions() -> tuple[str, ...]:
    return tuple(getattr(settings, "PHONE_ALLOWED_REGIONS", ("UZ",)))


def normalize(raw: str | None) -> str:
    """Return the E.164 form or raise ``ValidationError`` (code ``invalid_phone``)."""
    value = _JUNK_RE.sub("", str(raw or ""))
    if not value or len(value) > 20:
        raise ValidationError(INVALID_MESSAGE, code="invalid_phone")
    if value.startswith("00"):
        value = f"+{value[2:]}"
    regions = _regions()
    try:
        number = phonenumbers.parse(value, regions[0])
    except phonenumbers.NumberParseException:
        raise ValidationError(INVALID_MESSAGE, code="invalid_phone") from None
    if not phonenumbers.is_valid_number(number) or phonenumbers.region_code_for_number(number) not in regions:
        raise ValidationError(INVALID_MESSAGE, code="invalid_phone")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def try_normalize(raw: str | None) -> str | None:
    try:
        return normalize(raw)
    except ValidationError:
        return None


def validate_e164(value: str) -> None:
    """Model-field validator: the stored value must already be canonical."""
    if value and (not E164_RE.fullmatch(value) or try_normalize(value) != value):
        raise ValidationError(INVALID_MESSAGE, code="invalid_phone")


def mask(value: str | None) -> str | None:
    """``+998901234567`` -> ``+99890***4567`` (for logs and lists that do not need the full number)."""
    if not value:
        return None
    return f"{value[:6]}***{value[-4:]}"


def fingerprint(value: str) -> str:
    """Stable, non-reversible key (cache keys, throttling) — never put raw numbers in cache keys."""
    return hashlib.sha256(value.encode()).hexdigest()
