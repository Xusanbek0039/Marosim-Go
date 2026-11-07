"""Phone ownership verification (SMS OTP) — design contract, not wired to any endpoint yet.

Self-registered accounts start with ``User.is_phone_verified = False``. Authorized panel
admins may manually confirm a number using the audited verify-phone action. No SMS provider
has been chosen yet. When a provider is picked, implement this flow:

1. ``POST /api/v1/auth/phone/otp/``  {phone_number, purpose}
   * purposes: ``verify`` (own number after sign-up), ``change`` (new number, authenticated),
     ``reset_password`` (unauthenticated).
   * throttled per IP *and* per phone fingerprint, guarded by ``bot_protection.verify``;
     always answers 202 with the same body (no account enumeration).
   * store only ``hash(code)`` + attempt counter + expiry (≤ 5 min) — never the plain code.
2. ``POST /api/v1/auth/phone/verify/``  {phone_number, code, purpose}
   * constant-time compare, max 5 attempts, then the challenge is burned.
   * on success: ``mark_verified(user)``; for ``change`` swap the number and
     ``tokens.revoke_all_sessions(user)``; audit every outcome.
3. Unverified accounts older than N days can be pruned so a squatted number is released.

The provider is injected through ``settings.SMS_PROVIDER`` (dotted path to an ``SmsProvider``).
"""

from typing import Protocol

from django.utils import timezone


class SmsProvider(Protocol):
    def send(self, phone_number: str, text: str) -> None:  # pragma: no cover - contract only
        ...


def mark_verified(user) -> None:
    user.is_phone_verified = True
    user.phone_verified_at = timezone.now()
    user.save(update_fields=["is_phone_verified", "phone_verified_at", "updated_at"])
