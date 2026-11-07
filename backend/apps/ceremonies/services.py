"""Ceremony access rules in one place (views stay thin, tests target these)."""

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import Role
from apps.audit.services import AuditAction, record
from apps.studios.models import StudioMembership
from apps.studios.services import active_memberships

from .models import (
    COUPLE_TYPES,
    OPEN_STATUSES,
    VISIBLE_TO_PARTICIPANTS,
    AccessStatus,
    Ceremony,
    CeremonyParticipant,
)


# ------------------------------------------------------------------- scoping
def studio_ids(user, managing_only: bool = False) -> list:
    qs = active_memberships(user)
    if managing_only:
        qs = qs.filter(role__in=StudioMembership.MANAGING_ROLES)
    return list(qs.values_list("studio_id", flat=True))


def ceremonies_for(user):
    """Ceremonies a studio member or super admin may see (others: none)."""
    qs = Ceremony.objects.select_related("studio")
    if user.role == Role.SUPER_ADMIN:
        return qs
    if user.role == Role.STUDIO:
        return qs.filter(studio_id__in=studio_ids(user))
    return qs.none()


def can_manage(user, ceremony: Ceremony) -> bool:
    if user.role == Role.SUPER_ADMIN:
        return True
    return user.role == Role.STUDIO and ceremony.studio_id in studio_ids(user, managing_only=True)


def ensure_can_manage(user, ceremony: Ceremony) -> None:
    if not can_manage(user, ceremony):
        raise PermissionDenied("Bu marosimni boshqarish uchun studiyada OWNER yoki MANAGER bo'lishingiz kerak.")


def participations_for(user):
    """ACTIVE participations of a USER in ceremonies that are not studio drafts."""
    return CeremonyParticipant.objects.filter(
        user=user,
        access_status=AccessStatus.ACTIVE,
        ceremony__status__in=VISIBLE_TO_PARTICIPANTS,
        ceremony__studio__deleted_at__isnull=True,
    ).select_related("ceremony", "ceremony__studio")


def invitations_for(user):
    """Open invitations addressed to the caller's phone number."""
    if not user.phone_number:
        return CeremonyParticipant.objects.none()
    return CeremonyParticipant.objects.filter(
        phone_number=user.phone_number,
        access_status=AccessStatus.INVITED,
        ceremony__studio__deleted_at__isnull=True,
    ).select_related("ceremony", "ceremony__studio")


# --------------------------------------------------------------- invitations
DUPLICATE_PHONE = "Bu telefon raqamga ushbu marosimga taklif allaqachon yuborilgan."
DUPLICATE_ROLE = "Bu marosimda {label} allaqachon belgilangan."


@transaction.atomic
def invite(request, ceremony: Ceremony, phone_number: str, participant_type: str) -> CeremonyParticipant:
    """Create an invitation. Identical behaviour whether or not the number has an account."""
    ensure_can_manage(request.user, ceremony)
    open_rows = ceremony.participants.filter(access_status__in=OPEN_STATUSES)
    if open_rows.filter(phone_number=phone_number).exists():
        raise ValidationError({"phone_number": [DUPLICATE_PHONE]})
    if participant_type in COUPLE_TYPES and open_rows.filter(participant_type=participant_type).exists():
        label = dict(CeremonyParticipant._meta.get_field("participant_type").choices)[participant_type].lower()
        raise ValidationError({"participant_type": [DUPLICATE_ROLE.format(label=label)]})
    try:
        with transaction.atomic():
            participant = CeremonyParticipant.objects.create(
                ceremony=ceremony,
                phone_number=phone_number,
                participant_type=participant_type,
                invited_by=request.user,
            )
    except IntegrityError:  # concurrent duplicate
        raise ValidationError({"phone_number": [DUPLICATE_PHONE]}) from None
    record(request, AuditAction.PARTICIPANT_INVITE, participant, changes={"type": participant_type})
    return participant


@transaction.atomic
def revoke(request, participant: CeremonyParticipant) -> None:
    ensure_can_manage(request.user, participant.ceremony)
    if participant.access_status in (AccessStatus.REVOKED, AccessStatus.DECLINED):
        return
    participant.access_status = AccessStatus.REVOKED
    participant.save(update_fields=["access_status", "updated_at"])
    record(request, AuditAction.PARTICIPANT_REVOKE, participant)


def _ensure_invitee(user, participant: CeremonyParticipant) -> None:
    if participant.access_status != AccessStatus.INVITED or participant.phone_number != user.phone_number:
        raise ValidationError({"detail": ["Taklif topilmadi yoki allaqachon javob berilgan."]})


@transaction.atomic
def accept(request, participant: CeremonyParticipant) -> CeremonyParticipant:
    user = request.user
    _ensure_invitee(user, participant)
    if settings.CEREMONY_INVITE_REQUIRE_VERIFIED_PHONE and not user.is_phone_verified:
        raise PermissionDenied("Taklifni qabul qilish uchun telefon raqamingizni tasdiqlang.")
    participant.user = user
    participant.access_status = AccessStatus.ACTIVE
    participant.responded_at = timezone.now()
    participant.save(update_fields=["user", "access_status", "responded_at", "updated_at"])
    record(request, AuditAction.PARTICIPANT_ACCEPT, participant, actor=user)
    return participant


@transaction.atomic
def decline(request, participant: CeremonyParticipant) -> CeremonyParticipant:
    _ensure_invitee(request.user, participant)
    participant.access_status = AccessStatus.DECLINED
    participant.responded_at = timezone.now()
    participant.save(update_fields=["access_status", "responded_at", "updated_at"])
    record(request, AuditAction.PARTICIPANT_DECLINE, participant, actor=request.user)
    return participant
