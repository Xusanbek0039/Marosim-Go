"""Invitation, acceptance, owner-approval and revocation flows of the ownership model.

*Who may* do something is decided only in ``ownership.py``; this module performs the change.
Every state change is a conditional ``UPDATE … WHERE status = <expected>`` (compare-and-set), so two
concurrent requests can never both win — e.g. one invitation accepted twice — on any database.
"""

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

from apps.audit.services import AuditAction, record
from apps.core.exceptions import Conflict

from . import ownership
from .models import (
    OPEN_OWNERSHIP,
    SINGLE_OWNER_TYPES,
    AccessRole,
    ApprovalDecision,
    Ceremony,
    CeremonyInvitation,
    CeremonyOwnership,
    CeremonyOwnershipApproval,
    CeremonyViewerAccess,
    IdentifierType,
    InvitationStatus,
    InviterKind,
    OwnershipStatus,
    OwnerType,
    ViewerStatus,
)

#: v1 API vocabulary (``participant_type``) ↔ owner types.
OWNER_TYPE_FROM_LEGACY = {"BRIDE": OwnerType.BRIDE, "GROOM": OwnerType.GROOM, "OTHER": OwnerType.OTHER_OWNER}
LEGACY_FROM_OWNER_TYPE = {
    OwnerType.BRIDE: "BRIDE",
    OwnerType.GROOM: "GROOM",
    OwnerType.FAMILY_OWNER: "OTHER",
    OwnerType.OTHER_OWNER: "OTHER",
}

DUPLICATE = "Bu oluvchiga ushbu marosim bo'yicha taklif allaqachon yuborilgan."
SELF_INVITE = "O'zingizni taklif qila olmaysiz."
PINFL_FIRST_OWNER = (
    "Birinchi egalar faqat telefon raqami orqali taklif qilinadi: JSHSHIR shaxsni tasdiqlamaydi, "
    "uni tasdiqlaydigan ega esa hali yo'q."
)
TOO_MANY = "Bu marosimda javob kutilayotgan takliflar juda ko'p. Avval eskilarini bekor qiling."
NO_INVITE_RIGHT = "Bu turdagi taklifni yuborish huquqingiz yo'q."


class InvitationExpired(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = "Taklif muddati tugagan. Yuboruvchidan qayta yuborishni so'rang."
    default_code = "invitation_expired"


class PhoneNotVerified(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Taklifni qabul qilish uchun telefon raqamingizni tasdiqlang."
    default_code = "phone_not_verified"


class IdentityUnverified(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Bu egalik taklifini hozir qabul qilib bo'lmaydi: uni tasdiqlaydigan marosim egasi yo'q."
    default_code = "identity_unverified"


def _label(choices, value) -> str:
    return str(dict(choices.choices).get(value, value)).lower()


def _now():
    return timezone.now()


# ------------------------------------------------------------------ create
@transaction.atomic
def create_invitation(
    request,
    ceremony: Ceremony,
    *,
    identifier_type: str,
    identifier: str,
    requested_role: str,
    owner_type: str = "",
    allowed_kinds: tuple[str, ...] = (InviterKind.OWNER, InviterKind.STUDIO, InviterKind.SUPER_ADMIN),
) -> CeremonyInvitation:
    """Create an invitation. The response never depends on whether the identifier has an account."""
    user = request.user
    kind = ownership.inviter_kind(user, ceremony, requested_role)
    if kind is None or kind not in allowed_kinds:
        raise PermissionDenied(NO_INVITE_RIGHT)

    if requested_role == AccessRole.VIEWER:
        owner_type = ""
    elif not owner_type:
        raise ValidationError({"owner_type": ["Egalik turini tanlang."]})

    try:
        sealed = ownership.seal_identifier(identifier_type, identifier)
    except DjangoValidationError as exc:
        raise ValidationError({"identifier": exc.messages}) from None
    if ownership.recipient_indexes(user).get(identifier_type) == sealed["recipient_identifier_hash"]:
        raise ValidationError({"identifier": [SELF_INVITE]})

    if (
        identifier_type == IdentifierType.PINFL
        and requested_role == AccessRole.OWNER
        and not ownership.approvers_for(ceremony)
    ):
        raise ValidationError({"identifier_type": [PINFL_FIRST_OWNER]})

    now = _now()
    live = ceremony.invitations.filter(status=InvitationStatus.PENDING, expires_at__gt=now)
    if owner_type in SINGLE_OWNER_TYPES and (
        ceremony.ownerships.filter(owner_type=owner_type, status__in=OPEN_OWNERSHIP).exists()
        or live.filter(owner_type=owner_type).exists()
    ):
        raise ValidationError(
            {"owner_type": [f"Bu marosimda {_label(OwnerType, owner_type)} allaqachon belgilangan."]}
        )
    if live.count() >= settings.CEREMONY_MAX_PENDING_INVITATIONS:
        raise ValidationError({"non_field_errors": [TOO_MANY]})

    # A stale PENDING row to the same recipient would trip the unique constraint: expire it first.
    _expire(
        ceremony.invitations.filter(
            status=InvitationStatus.PENDING,
            expires_at__lte=now,
            identifier_type=identifier_type,
            recipient_identifier_hash=sealed["recipient_identifier_hash"],
        )
    )
    try:
        with transaction.atomic():
            invitation = CeremonyInvitation.objects.create(
                ceremony=ceremony,
                requested_role=requested_role,
                owner_type=owner_type,
                invited_by=user,
                inviter_kind=kind,
                expires_at=ownership.default_expiry(),
                last_sent_at=now,
                **sealed,
            )
    except IntegrityError:  # concurrent or existing duplicate
        raise ValidationError({"identifier": [DUPLICATE]}) from None

    action = AuditAction.OWNER_INVITE if requested_role == AccessRole.OWNER else AuditAction.VIEWER_INVITE
    record(
        request,
        action,
        invitation,
        changes={
            "ceremony": str(ceremony.pk),
            "requested_role": requested_role,
            "owner_type": owner_type or None,
            "identifier_type": identifier_type,
            "recipient": invitation.recipient_hint,
            "inviter_kind": kind,
        },
        target_label=f"{ceremony.title} → {invitation.recipient_hint}",
    )
    return invitation


# ---------------------------------------------------------------- respond
def _expire(qs) -> int:
    return qs.update(status=InvitationStatus.EXPIRED, updated_at=_now())


def expire_stale() -> int:
    """Mark every overdue PENDING invitation EXPIRED (``manage.py expire_ceremony_invitations``)."""
    return _expire(CeremonyInvitation.objects.filter(status=InvitationStatus.PENDING, expires_at__lte=_now()))


def _refuse(refusal: str, invitation: CeremonyInvitation):
    if refusal == ownership.Refusal.EXPIRED:
        _expire(CeremonyInvitation.objects.filter(pk=invitation.pk, status=InvitationStatus.PENDING))
        raise InvitationExpired()
    if refusal == ownership.Refusal.PHONE_NOT_VERIFIED:
        raise PhoneNotVerified()
    if refusal == ownership.Refusal.IDENTITY_UNVERIFIED:
        raise IdentityUnverified()
    if refusal == ownership.Refusal.ALREADY_HAS_ACCESS:
        raise Conflict("Sizda bu marosimga kirish huquqi allaqachon bor.")
    raise NotFound()


def _claim(invitation: CeremonyInvitation, user, new_status: str) -> None:
    now = _now()
    won = CeremonyInvitation.objects.filter(pk=invitation.pk, status=InvitationStatus.PENDING).update(
        status=new_status, invited_user=user, responded_at=now, updated_at=now
    )
    if not won:  # somebody (or a parallel request) answered first
        raise NotFound()
    invitation.status, invitation.invited_user, invitation.responded_at = new_status, user, now


def accept(request, invitation: CeremonyInvitation) -> dict:
    """Accept. VIEWER → access now. OWNER → ACCEPTED, or PENDING until current owners approve.

    Refusals are checked outside the transaction so an EXPIRED mark survives the error response.
    """
    refusal = ownership.response_refusal(request.user, invitation, accepting=True)
    if refusal:
        _refuse(refusal, invitation)
    return _accept(request, invitation)


@transaction.atomic
def _accept(request, invitation: CeremonyInvitation) -> dict:
    user = request.user
    _claim(invitation, user, InvitationStatus.ACCEPTED)
    ceremony = invitation.ceremony

    if invitation.requested_role == AccessRole.VIEWER:
        try:
            with transaction.atomic():
                CeremonyViewerAccess.objects.create(
                    ceremony=ceremony,
                    user=user,
                    granted_by_id=invitation.invited_by_id,
                    invitation=invitation,
                    accepted_at=invitation.responded_at,
                )
        except IntegrityError:
            raise Conflict("Sizda bu marosimga kirish huquqi allaqachon bor.") from None
        record(request, AuditAction.VIEWER_ACCEPT, invitation, actor=user, changes={"ceremony": str(ceremony.pk)})
        return {"status": "ACCEPTED", "access_role": AccessRole.VIEWER, "ownership": None}

    approvers = ownership.approvers_for(ceremony)
    try:
        with transaction.atomic():
            row = CeremonyOwnership.objects.create(
                ceremony=ceremony,
                user=user,
                owner_type=invitation.owner_type,
                invited_by_id=invitation.invited_by_id,
                invitation=invitation,
                status=OwnershipStatus.PENDING,
            )
    except IntegrityError:
        label = _label(OwnerType, invitation.owner_type)
        raise Conflict(f"Bu marosimda {label} allaqachon bor yoki siz allaqachon egasiz.") from None
    now = _now()
    CeremonyOwnershipApproval.objects.bulk_create(
        [
            CeremonyOwnershipApproval(
                ownership=row,
                approver_id=approver_id,
                # Inviting a new owner is the inviting owner's approval.
                decision=ApprovalDecision.APPROVED
                if approver_id == invitation.invited_by_id
                else ApprovalDecision.PENDING,
                decided_at=now if approver_id == invitation.invited_by_id else None,
            )
            for approver_id in approvers
        ]
    )
    _settle(row)
    record(
        request,
        AuditAction.OWNER_ACCEPT,
        invitation,
        actor=user,
        changes={"ceremony": str(ceremony.pk), "ownership_status": row.status, "approvers": len(approvers)},
    )
    result = "ACCEPTED" if row.status == OwnershipStatus.ACCEPTED else "PENDING_APPROVAL"
    return {"status": result, "access_role": AccessRole.OWNER, "ownership": row}


def decline(request, invitation: CeremonyInvitation) -> None:
    refusal = ownership.response_refusal(request.user, invitation, accepting=False)
    if refusal:
        _refuse(refusal, invitation)
    _claim(invitation, request.user, InvitationStatus.DECLINED)
    record(request, AuditAction.INVITATION_DECLINE, invitation, actor=request.user)


# ------------------------------------------------------------- management
@transaction.atomic
def revoke_invitation(request, invitation: CeremonyInvitation) -> None:
    if not ownership.can_revoke_invitation(request.user, invitation):
        raise PermissionDenied("Bu taklifni faqat uni yuborgan tomon bekor qila oladi.")
    now = _now()
    CeremonyInvitation.objects.filter(pk=invitation.pk, status=InvitationStatus.PENDING).update(
        status=InvitationStatus.REVOKED, revoked_at=now, revoked_by=request.user, updated_at=now
    )
    record(request, AuditAction.INVITATION_REVOKE, invitation, changes={"recipient": invitation.recipient_hint})


@transaction.atomic
def resend(request, invitation: CeremonyInvitation) -> CeremonyInvitation:
    """Renew the expiry (the invitee sees it in "Mening takliflarim"; no SMS provider yet)."""
    if not ownership.can_resend_invitation(request.user, invitation):
        raise PermissionDenied("Bu taklifni faqat uni yuborgan tomon qayta yubora oladi.")
    if invitation.send_count >= settings.CEREMONY_MAX_INVITATION_SENDS:
        raise ValidationError({"non_field_errors": ["Taklif juda ko'p marta yuborilgan. Yangi taklif yarating."]})
    now = _now()
    try:
        with transaction.atomic():
            won = CeremonyInvitation.objects.filter(
                pk=invitation.pk,
                status__in=(InvitationStatus.PENDING, InvitationStatus.EXPIRED),
                send_count=invitation.send_count,
            ).update(
                status=InvitationStatus.PENDING,
                expires_at=ownership.default_expiry(),
                send_count=invitation.send_count + 1,
                last_sent_at=now,
                updated_at=now,
            )
    except IntegrityError:  # a newer pending invitation to the same recipient exists
        raise ValidationError({"identifier": [DUPLICATE]}) from None
    if not won:
        raise Conflict("Taklif holati o'zgargan. Ro'yxatni yangilang.")
    invitation.refresh_from_db()
    record(request, AuditAction.INVITATION_RESEND, invitation, changes={"send_count": invitation.send_count})
    return invitation


def _settle(row: CeremonyOwnership) -> None:
    """Finalise a PENDING ownership once its approvals decide it."""
    if row.status != OwnershipStatus.PENDING:
        return
    outcome = ownership.approval_outcome(row)
    if outcome == ApprovalDecision.PENDING:
        return
    now = _now()
    final = OwnershipStatus.ACCEPTED if outcome == ApprovalDecision.APPROVED else OwnershipStatus.REJECTED
    won = CeremonyOwnership.objects.filter(pk=row.pk, status=OwnershipStatus.PENDING).update(
        status=final, accepted_at=now if final == OwnershipStatus.ACCEPTED else None, updated_at=now
    )
    if won:
        row.status = final
        row.accepted_at = now if final == OwnershipStatus.ACCEPTED else None


def _settle_ceremony(ceremony: Ceremony) -> None:
    for row in CeremonyOwnership.objects.filter(ceremony=ceremony, status=OwnershipStatus.PENDING):
        _settle(row)


@transaction.atomic
def decide_owner_request(request, row: CeremonyOwnership, *, approve: bool) -> CeremonyOwnership:
    user = request.user
    if not ownership.can_decide_owner_request(user, row):
        raise PermissionDenied("Siz bu so'rov bo'yicha qaror qabul qila olmaysiz.")
    decision = ApprovalDecision.APPROVED if approve else ApprovalDecision.REJECTED
    won = CeremonyOwnershipApproval.objects.filter(
        ownership=row, approver=user, decision=ApprovalDecision.PENDING
    ).update(decision=decision, decided_at=_now(), updated_at=_now())
    if not won:
        raise Conflict("Siz bu so'rov bo'yicha allaqachon qaror qabul qilgansiz.")
    _settle(row)
    action = AuditAction.OWNER_REQUEST_APPROVE if approve else AuditAction.OWNER_REJECT
    record(request, action, row, changes={"decision": decision, "ownership_status": row.status})
    return row


@transaction.atomic
def revoke_ownership(request, row: CeremonyOwnership) -> None:
    """Leave (own row) or Super Admin removal. The owner's pending invitations lapse with it."""
    user = request.user
    if not ownership.can_revoke_ownership(user, row):
        raise PermissionDenied("Boshqa egani faqat Super Admin olib tashlay oladi.")
    now = _now()
    won = CeremonyOwnership.objects.filter(pk=row.pk, status__in=OPEN_OWNERSHIP).update(
        status=OwnershipStatus.REVOKED, revoked_at=now, revoked_by=user, updated_at=now
    )
    if not won:
        return
    CeremonyInvitation.objects.filter(
        ceremony_id=row.ceremony_id,
        invited_by_id=row.user_id,
        inviter_kind=InviterKind.OWNER,
        status=InvitationStatus.PENDING,
    ).update(status=InvitationStatus.REVOKED, revoked_at=now, revoked_by=user, updated_at=now)
    _settle_ceremony(row.ceremony)  # their pending votes no longer count
    record(
        request,
        AuditAction.ACCESS_REVOKE,
        row,
        changes={"role": AccessRole.OWNER, "user": str(row.user_id), "self": row.user_id == user.pk},
    )


@transaction.atomic
def revoke_viewer(request, access: CeremonyViewerAccess) -> None:
    user = request.user
    if not ownership.can_revoke_viewer(user, access):
        raise PermissionDenied("Ko'rish huquqini faqat uni bergan ega bekor qila oladi.")
    now = _now()
    CeremonyViewerAccess.objects.filter(pk=access.pk, status=ViewerStatus.ACCEPTED).update(
        status=ViewerStatus.REVOKED, revoked_at=now, revoked_by=user, updated_at=now
    )
    record(
        request,
        AuditAction.ACCESS_REVOKE,
        access,
        changes={"role": AccessRole.VIEWER, "user": str(access.user_id), "self": access.user_id == user.pk},
    )


def leave(request, ceremony: Ceremony) -> None:
    user = request.user
    row = CeremonyOwnership.objects.filter(ceremony=ceremony, user=user, status=OwnershipStatus.ACCEPTED).first()
    if row is not None:
        return revoke_ownership(request, row)
    access = CeremonyViewerAccess.objects.filter(ceremony=ceremony, user=user, status=ViewerStatus.ACCEPTED).first()
    if access is None:
        raise NotFound()
    return revoke_viewer(request, access)
