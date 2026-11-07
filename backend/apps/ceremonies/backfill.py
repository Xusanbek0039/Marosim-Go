"""Copy v1 ``CeremonyParticipant`` rows into the ownership model (invitations + ownerships).

Called from migrations with historical models (``apps.get_model``), so it must not import this
app's real models. Idempotent: a participant that already has an invitation is skipped, so the
Phase C migration can run it again to pick up rows created in between.

Mapping (every v1 participant was a studio-sent owner invitation by phone):

* INVITED  → invitation PENDING (fresh TTL — v1 invitations never expired)
* ACTIVE   → invitation ACCEPTED + ownership ACCEPTED (existing access is preserved as is)
* DECLINED → invitation DECLINED
* REVOKED  → invitation REVOKED (+ ownership REVOKED if it had been accepted)
* BRIDE / GROOM keep their type, OTHER becomes OTHER_OWNER.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.accounts import phone as phone_utils
from apps.core import crypto

OWNER_TYPE = {"BRIDE": "BRIDE", "GROOM": "GROOM", "OTHER": "OTHER_OWNER"}
INVITATION_STATUS = {"INVITED": "PENDING", "ACTIVE": "ACCEPTED", "DECLINED": "DECLINED", "REVOKED": "REVOKED"}


def _phone_index(e164: str) -> str:
    return crypto.blind_index(f"phone:{e164}")  # same derivation as ownership.phone_index


def backfill(apps) -> int:
    Participant = apps.get_model("ceremonies", "CeremonyParticipant")
    Invitation = apps.get_model("ceremonies", "CeremonyInvitation")
    Ownership = apps.get_model("ceremonies", "CeremonyOwnership")

    now = timezone.now()
    ttl = timedelta(days=settings.CEREMONY_INVITATION_TTL_DAYS)
    copied = 0
    rows = Participant.objects.filter(invitation__isnull=True).select_related("invited_by").order_by("created_at")
    for p in rows:
        status = INVITATION_STATUS[p.access_status]
        if status == "ACCEPTED" and p.user_id is None:  # cannot happen in v1; never grant blindly
            status = "PENDING"
        inviter = p.invited_by
        invitation = Invitation.objects.create(
            ceremony_id=p.ceremony_id,
            invited_user_id=p.user_id,
            identifier_type="PHONE",
            recipient_identifier_encrypted=crypto.encrypt(p.phone_number),
            recipient_identifier_hash=_phone_index(p.phone_number),
            recipient_hint=phone_utils.mask(p.phone_number),
            requested_role="OWNER",
            owner_type=OWNER_TYPE[p.participant_type],
            invited_by_id=p.invited_by_id,
            inviter_kind="SUPER_ADMIN" if inviter is not None and inviter.role == "SUPER_ADMIN" else "STUDIO",
            status=status,
            expires_at=now + ttl if status == "PENDING" else p.created_at + ttl,
            responded_at=p.responded_at,
            revoked_at=p.updated_at if status == "REVOKED" else None,
            last_sent_at=p.created_at,
            legacy_participant_id=p.pk,
        )
        Invitation.objects.filter(pk=invitation.pk).update(created_at=p.created_at)

        accepted_at = p.responded_at or p.updated_at
        if status == "ACCEPTED" or (status == "REVOKED" and p.user_id):
            ownership = Ownership.objects.create(
                ceremony_id=p.ceremony_id,
                user_id=p.user_id,
                owner_type=OWNER_TYPE[p.participant_type],
                invited_by_id=p.invited_by_id,
                invitation_id=invitation.pk,
                status="ACCEPTED" if status == "ACCEPTED" else "REVOKED",
                accepted_at=accepted_at,
                revoked_at=p.updated_at if status == "REVOKED" else None,
            )
            Ownership.objects.filter(pk=ownership.pk).update(created_at=accepted_at)
        copied += 1
    return copied
