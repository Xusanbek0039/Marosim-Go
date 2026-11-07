"""Ceremony-specific access: who is an OWNER / VIEWER of which ceremony and what each actor may do.

Every endpoint of the ownership model (Phases C–E) decides access through these functions only;
``tests/test_ceremony_ownership.py`` pins the rules. Summary (details in docs/CEREMONY_OWNERSHIP.md):

* Access exists only through an ACCEPTED ``CeremonyOwnership`` or ``CeremonyViewerAccess`` row of an
  alive USER-role account, on a ceremony that is not a studio DRAFT and whose studio is not deleted.
  A pending invitation, a Drive file id or knowing a phone / JSHSHIR grants nothing.
* OWNER and VIEWER are ceremony-scoped, not ``User.role`` values.
* Owners share VIEWER access and propose new owners. A new owner needs the approval of every
  owner ACCEPTED when they accepted (inviter's own invitation counts as their approval); with no
  owners yet (the studio's first invitations) a verified phone is the initial verification.
* An owner can revoke only what they granted (their viewers, their pending invitations) and leave
  themselves. Removing another owner is a Super Admin action.
* JSHSHIR is only an identifier for addressing an invitation; it never authenticates anyone.
"""

import hmac
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.accounts import phone as phone_utils
from apps.accounts import pinfl as pinfl_utils
from apps.accounts.models import Role
from apps.core import crypto
from apps.studios.models import StudioMembership
from apps.studios.services import active_memberships

from .models import (
    VISIBLE_TO_PARTICIPANTS,
    AccessRole,
    ApprovalDecision,
    Ceremony,
    CeremonyInvitation,
    CeremonyOwnership,
    CeremonyViewerAccess,
    IdentifierType,
    InvitationStatus,
    InviterKind,
    OwnershipStatus,
    ViewerStatus,
)


# ------------------------------------------------------------- identifiers
def phone_index(e164: str) -> str:
    # Domain-separated from the JSHSHIR index, which shares the HMAC key.
    return crypto.blind_index(f"phone:{e164}")


def seal_identifier(identifier_type: str, raw: str) -> dict:
    """Validate + normalise a recipient identifier and return the fields stored on an invitation.

    Raises ``django.core.exceptions.ValidationError`` for malformed input. The plaintext leaves
    this function only encrypted.
    """
    if identifier_type == IdentifierType.PHONE:
        value = phone_utils.normalize(raw)
        index, hint = phone_index(value), phone_utils.mask(value)
    elif identifier_type == IdentifierType.PINFL:
        value = pinfl_utils.validate(raw)
        index, hint = pinfl_utils.hash_of(value), pinfl_utils.mask(value[-4:])
    else:
        raise ValueError(f"Unknown identifier type: {identifier_type}")
    return {
        "identifier_type": identifier_type,
        "recipient_identifier_encrypted": crypto.encrypt(value),
        "recipient_identifier_hash": index,
        "recipient_hint": hint,
    }


def recipient_indexes(user) -> dict[str, str]:
    """Blind indexes an invitation must carry to be addressed to ``user``."""
    indexes = {}
    if user.phone_number:
        indexes[IdentifierType.PHONE.value] = phone_index(user.phone_number)
    if user.pinfl_hash:
        indexes[IdentifierType.PINFL.value] = user.pinfl_hash
    return indexes


def is_recipient(user, invitation: CeremonyInvitation) -> bool:
    expected = recipient_indexes(user).get(invitation.identifier_type)
    return bool(expected) and hmac.compare_digest(expected, invitation.recipient_identifier_hash)


def default_expiry():
    return timezone.now() + timedelta(days=settings.CEREMONY_INVITATION_TTL_DAYS)


# ------------------------------------------------------------------ actors
def _alive(user) -> bool:
    return bool(user and user.is_authenticated and user.is_active and not user.is_deleted)


def is_client(user) -> bool:
    """Only USER-role accounts hold ceremony access (studio staff and admins never do)."""
    return _alive(user) and user.role == Role.USER


def is_super_admin(user) -> bool:
    return _alive(user) and user.role == Role.SUPER_ADMIN


def manages_studio_of(user, ceremony: Ceremony) -> bool:
    return (
        _alive(user)
        and user.role == Role.STUDIO
        and active_memberships(user)
        .filter(studio_id=ceremony.studio_id, role__in=StudioMembership.MANAGING_ROLES)
        .exists()
    )


# ------------------------------------------------------------------ access
def _shareable(ceremony: Ceremony) -> bool:
    return ceremony.status in VISIBLE_TO_PARTICIPANTS and ceremony.studio.deleted_at is None


def role_in(user, ceremony: Ceremony) -> str | None:
    """``OWNER`` / ``VIEWER`` / ``None`` — re-evaluated from the database on every call."""
    if not is_client(user) or not _shareable(ceremony):
        return None
    if CeremonyOwnership.objects.filter(ceremony=ceremony, user=user, status=OwnershipStatus.ACCEPTED).exists():
        return AccessRole.OWNER
    if CeremonyViewerAccess.objects.filter(ceremony=ceremony, user=user, status=ViewerStatus.ACCEPTED).exists():
        return AccessRole.VIEWER
    return None


def is_owner(user, ceremony: Ceremony) -> bool:
    return role_in(user, ceremony) == AccessRole.OWNER


def can_view(user, ceremony: Ceremony) -> bool:
    """Ceremony details and every media endpoint (list, thumbnail, preview, stream, download)."""
    return role_in(user, ceremony) is not None


def _shareable_ceremonies():
    return Ceremony.objects.filter(status__in=VISIBLE_TO_PARTICIPANTS, studio__deleted_at__isnull=True)


def owned_ceremonies(user):
    if not is_client(user):
        return Ceremony.objects.none()
    ids = CeremonyOwnership.objects.filter(user=user, status=OwnershipStatus.ACCEPTED).values("ceremony_id")
    return _shareable_ceremonies().filter(pk__in=ids)


def accessible_ceremonies(user):
    """Every ceremony ``user`` may open, as OWNER or VIEWER."""
    if not is_client(user):
        return Ceremony.objects.none()
    owned = CeremonyOwnership.objects.filter(user=user, status=OwnershipStatus.ACCEPTED).values("ceremony_id")
    viewed = CeremonyViewerAccess.objects.filter(user=user, status=ViewerStatus.ACCEPTED).values("ceremony_id")
    return _shareable_ceremonies().filter(pk__in=owned.union(viewed))


# ------------------------------------------------------------- invitations
def inviter_kind(user, ceremony: Ceremony, requested_role: str) -> str | None:
    """The capacity in which ``user`` may send this invitation, or ``None`` if they may not.

    * VIEWER — accepted owners only.
    * OWNER — accepted owners (approval follows), managing studio staff, Super Admin.
    """
    if is_owner(user, ceremony):
        return InviterKind.OWNER
    if requested_role != AccessRole.OWNER:
        return None
    if manages_studio_of(user, ceremony):
        return InviterKind.STUDIO
    if is_super_admin(user):
        return InviterKind.SUPER_ADMIN
    return None


def can_invite(user, ceremony: Ceremony, requested_role: str) -> bool:
    return inviter_kind(user, ceremony, requested_role) is not None


def invitations_for(user):
    """Pending, unexpired invitations addressed to ``user`` ("Mening takliflarim")."""
    if not is_client(user):
        return CeremonyInvitation.objects.none()
    indexes = recipient_indexes(user)
    if not indexes:
        return CeremonyInvitation.objects.none()
    match = Q()
    for identifier_type, index in indexes.items():
        match |= Q(identifier_type=identifier_type, recipient_identifier_hash=index)
    return CeremonyInvitation.objects.filter(
        match,
        status=InvitationStatus.PENDING,
        expires_at__gt=timezone.now(),
        ceremony__studio__deleted_at__isnull=True,
    ).select_related("ceremony", "ceremony__studio")


def requires_verified_phone(invitation: CeremonyInvitation) -> bool:
    if invitation.requested_role == AccessRole.OWNER:
        return settings.CEREMONY_OWNER_REQUIRE_VERIFIED_PHONE
    return settings.CEREMONY_INVITE_REQUIRE_VERIFIED_PHONE


class Refusal:
    """Why a recipient may not respond. Callers map NOT_FOUND to 404 (never confirm existence)."""

    NOT_FOUND = "not_found"
    EXPIRED = "expired"
    PHONE_NOT_VERIFIED = "phone_not_verified"
    ALREADY_HAS_ACCESS = "already_has_access"


def response_refusal(user, invitation: CeremonyInvitation, *, accepting: bool) -> str | None:
    """``None`` if ``user`` may accept (``accepting``) or decline ``invitation`` now."""
    if not is_client(user) or invitation.status != InvitationStatus.PENDING or not is_recipient(user, invitation):
        return Refusal.NOT_FOUND
    if invitation.ceremony.studio.deleted_at is not None:
        return Refusal.NOT_FOUND
    if invitation.expires_at <= timezone.now():
        return Refusal.EXPIRED
    if not accepting:
        return None
    if requires_verified_phone(invitation) and not user.is_phone_verified:
        return Refusal.PHONE_NOT_VERIFIED
    ceremony = invitation.ceremony
    open_ownership = CeremonyOwnership.objects.filter(
        ceremony=ceremony, user=user, status__in=(OwnershipStatus.PENDING, OwnershipStatus.ACCEPTED)
    ).exists()
    if open_ownership:
        return Refusal.ALREADY_HAS_ACCESS
    if invitation.requested_role == AccessRole.VIEWER and CeremonyViewerAccess.objects.filter(
        ceremony=ceremony, user=user, status=ViewerStatus.ACCEPTED
    ).exists():
        return Refusal.ALREADY_HAS_ACCESS
    return None


def can_revoke_invitation(user, invitation: CeremonyInvitation) -> bool:
    """The sender while they still hold the capacity they sent it in; studio managers for studio
    invitations; Super Admin. Never another owner."""
    if invitation.status != InvitationStatus.PENDING:
        return False
    if is_super_admin(user):
        return True
    ceremony = invitation.ceremony
    if invitation.inviter_kind == InviterKind.STUDIO:
        return manages_studio_of(user, ceremony)
    if invitation.inviter_kind == InviterKind.OWNER:
        return invitation.invited_by_id == user.pk and is_owner(user, ceremony)
    return False


# ------------------------------------------------------------ owner requests
def approvers_for(ceremony: Ceremony, exclude_user_id=None) -> list:
    """Owners whose approval a new ownership needs: everyone ACCEPTED right now."""
    qs = CeremonyOwnership.objects.filter(ceremony=ceremony, status=OwnershipStatus.ACCEPTED)
    if exclude_user_id is not None:
        qs = qs.exclude(user_id=exclude_user_id)
    return list(qs.values_list("user_id", flat=True))


def approval_outcome(ownership: CeremonyOwnership) -> str:
    """PENDING until every still-accepted approver approved; any rejection rejects.

    Votes of approvers who are no longer owners do not count (neither block nor approve).
    """
    current_owners = set(approvers_for(ownership.ceremony, exclude_user_id=ownership.user_id))
    decisions = [a.decision for a in ownership.approvals.all() if a.approver_id in current_owners]
    if ApprovalDecision.REJECTED in decisions:
        return ApprovalDecision.REJECTED
    if all(d == ApprovalDecision.APPROVED for d in decisions):
        return ApprovalDecision.APPROVED
    return ApprovalDecision.PENDING


def can_decide_owner_request(user, ownership: CeremonyOwnership) -> bool:
    return (
        ownership.status == OwnershipStatus.PENDING
        and is_owner(user, ownership.ceremony)
        and ownership.approvals.filter(approver=user, decision=ApprovalDecision.PENDING).exists()
    )


# --------------------------------------------------------------- revocation
def can_revoke_viewer(user, access: CeremonyViewerAccess) -> bool:
    """The granting owner (while still an owner), the viewer leaving, or Super Admin."""
    if access.status != ViewerStatus.ACCEPTED:
        return False
    if is_super_admin(user) or (is_client(user) and access.user_id == user.pk):
        return True
    return access.granted_by_id == user.pk and is_owner(user, access.ceremony)


def can_revoke_ownership(user, ownership: CeremonyOwnership) -> bool:
    """An owner may leave; only a Super Admin may remove somebody else's ownership."""
    if ownership.status not in (OwnershipStatus.PENDING, OwnershipStatus.ACCEPTED):
        return False
    return is_super_admin(user) or (is_client(user) and ownership.user_id == user.pk)
