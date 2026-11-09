"""Anti-bot challenge for the public partner-application form (no account, no CAPTCHA service).

1. ``issue()`` hands the page a signed token ``{n: nonce, t: issued_at}`` and a difficulty.
2. The browser looks for a ``proof`` such that ``sha256("<token>:<proof>")`` starts with
   ``difficulty`` zero bits (proof-of-work: ~65k hashes at 16 bits — under a second for a person,
   expensive for a script sending thousands).
3. ``verify()`` checks the signature, that the form was open at least ``MIN_SECONDS`` (bots post
   instantly) and at most ``MAX_AGE_SECONDS``, the work, and that the token is used only once.

Settings: ``PARTNER_APPLY = {"POW_BITS": 16, "MIN_SECONDS": 3, "MAX_AGE_SECONDS": 7200}``.
"""

import hashlib
import secrets
import time

from django.conf import settings
from django.core import signing
from django.core.cache import cache

from apps.accounts.bot_protection import BotCheckFailed

SALT = "marosimgo.partner-apply"


def _conf() -> dict:
    return {"POW_BITS": 16, "MIN_SECONDS": 3, "MAX_AGE_SECONDS": 7200, **getattr(settings, "PARTNER_APPLY", {})}


def issue() -> dict:
    conf = _conf()
    token = signing.dumps({"n": secrets.token_hex(12), "t": int(time.time())}, salt=SALT, compress=True)
    return {"token": token, "difficulty": conf["POW_BITS"], "min_seconds": conf["MIN_SECONDS"]}


def leading_zero_bits(digest: bytes) -> int:
    bits = 0
    for byte in digest:
        if byte == 0:
            bits += 8
            continue
        return bits + (8 - byte.bit_length())
    return bits


def verify(token: str, proof: str) -> None:
    conf = _conf()
    try:
        data = signing.loads(token or "", salt=SALT, max_age=conf["MAX_AGE_SECONDS"])
    except signing.BadSignature:  # also SignatureExpired
        raise BotCheckFailed("Sahifa eskirgan. Sahifani yangilab, qayta yuboring.") from None
    if time.time() - data.get("t", 0) < conf["MIN_SECONDS"]:
        raise BotCheckFailed("Juda tez yuborildi. Bir necha soniyadan keyin qayta urinib ko'ring.")
    proof = str(proof or "")[:64]
    digest = hashlib.sha256(f"{token}:{proof}".encode()).digest()
    if leading_zero_bits(digest) < conf["POW_BITS"]:
        raise BotCheckFailed()
    if not cache.add(f"partner-apply:used:{data['n']}", 1, timeout=conf["MAX_AGE_SECONDS"]):
        raise BotCheckFailed("Bu forma allaqachon yuborilgan. Sahifani yangilang.")
