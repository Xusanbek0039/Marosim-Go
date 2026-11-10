"""Phase B — ceremony ownership model: constraints, access layer (``ceremonies.ownership``), backfill.

Endpoint-level tests (invite / accept / media) arrive with Phases C–E; these pin the rules every
endpoint will delegate to.
"""

from datetime import timedelta

import pytest
from django.apps import apps as django_apps
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.accounts.models import Role
from apps.ceremonies import ownership
from apps.ceremonies.backfill import backfill
from apps.ceremonies.models import (
    AccessRole,
    AccessStatus,
    ApprovalDecision,
    Ceremony,
    CeremonyInvitation,
    CeremonyOwnership,
    CeremonyOwnershipApproval,
    CeremonyParticipant,
    CeremonyStatus,
    CeremonyViewerAccess,
    IdentifierType,
    InvitationStatus,
    InviterKind,
    OwnershipStatus,
    OwnerType,
    ViewerStatus,
)
from apps.ceremonies.permissions import IsCeremonyMember, IsCeremonyOwner
from apps.studios.models import StudioMembership
from apps.studios.services import sync_owner_membership

from .conftest import next_pinfl


# ------------------------------------------------------------------ helpers
@pytest.fixture
def world(make_user, make_studio):
    studio_owner, other_studio_owner = make_user(Role.STUDIO), make_user(Role.STUDIO)
    studio, other_studio = make_studio(studio_owner), make_studio(other_studio_owner)
    sync_owner_membership(studio)
    sync_owner_membership(other_studio)
    uploader = make_user(Role.STUDIO)
    StudioMembership.objects.create(studio=studio, user=uploader, role=StudioMembership.Role.UPLOADER)
    ceremony = Ceremony.objects.create(
        studio=studio, title="To'y", event_date="2026-09-12", status=CeremonyStatus.READY
    )
    other = Ceremony.objects.create(
        studio=other_studio, title="Boshqa to'y", event_date="2026-10-01", status=CeremonyStatus.READY
    )
    return {
        "studio": studio,
        "studio_owner": studio_owner,
        "other_studio_owner": other_studio_owner,
        "uploader": uploader,
        "ceremony": ceremony,
        "other": other,
    }


def own(ceremony, user, owner_type=OwnerType.OTHER_OWNER, status=OwnershipStatus.ACCEPTED, **extra):
    accepted = timezone.now() if status == OwnershipStatus.ACCEPTED else None
    return CeremonyOwnership.objects.create(
        ceremony=ceremony, user=user, owner_type=owner_type, status=status, accepted_at=accepted, **extra
    )


def view(ceremony, user, granted_by=None, status=ViewerStatus.ACCEPTED):
    return CeremonyViewerAccess.objects.create(
        ceremony=ceremony, user=user, granted_by=granted_by, status=status, accepted_at=timezone.now()
    )


def invitation(ceremony, raw, *, identifier_type=IdentifierType.PHONE, role=AccessRole.OWNER, by=None, **extra):
    kind = extra.pop("inviter_kind", InviterKind.OWNER if role == AccessRole.VIEWER else InviterKind.STUDIO)
    return CeremonyInvitation.objects.create(
        ceremony=ceremony,
        requested_role=role,
        owner_type=extra.pop("owner_type", OwnerType.OTHER_OWNER if role == AccessRole.OWNER else ""),
        invited_by=by,
        inviter_kind=kind,
        expires_at=extra.pop("expires_at", ownership.default_expiry()),
        **ownership.seal_identifier(identifier_type, raw),
        **extra,
    )


def violates(fn) -> bool:
    try:
        with transaction.atomic():
            fn()
    except IntegrityError:
        return True
    return False


# ------------------------------------------------------------ access rules
@pytest.mark.django_db
def test_multiple_owners_each_have_owner_access(world, make_user):
    bride, groom, mother = make_user(), make_user(), make_user()
    c = world["ceremony"]
    own(c, bride, OwnerType.BRIDE)
    own(c, groom, OwnerType.GROOM)
    own(c, mother, OwnerType.FAMILY_OWNER)
    assert all(ownership.role_in(u, c) == AccessRole.OWNER for u in (bride, groom, mother))
    assert set(ownership.owned_ceremonies(bride)) == {c}


@pytest.mark.django_db
def test_pending_invitation_or_ownership_grants_nothing(world, make_user):
    user, c = make_user(), world["ceremony"]
    invitation(c, user.phone_number)
    assert ownership.role_in(user, c) is None
    own(c, user, status=OwnershipStatus.PENDING)  # accepted invitation awaiting owner approval
    assert ownership.role_in(user, c) is None
    assert not ownership.can_view(user, c)
    assert list(ownership.accessible_ceremonies(user)) == []


@pytest.mark.django_db
def test_viewer_access_and_cross_ceremony_denied(world, make_user):
    owner, guest, c, other = make_user(), make_user(), world["ceremony"], world["other"]
    own(c, owner)
    view(c, guest, granted_by=owner)
    assert ownership.role_in(guest, c) == AccessRole.VIEWER
    assert ownership.can_view(guest, c) and not ownership.is_owner(guest, c)
    assert ownership.role_in(owner, other) is None and ownership.role_in(guest, other) is None
    assert set(ownership.accessible_ceremonies(guest)) == {c}
    assert list(ownership.owned_ceremonies(guest)) == []


@pytest.mark.django_db
def test_revocation_closes_access_immediately(world, make_user):
    owner, guest, c = make_user(), make_user(), world["ceremony"]
    o = own(c, owner)
    v = view(c, guest, granted_by=owner)
    v.status = ViewerStatus.REVOKED
    v.save()
    o.status = OwnershipStatus.REVOKED
    o.save()
    assert ownership.role_in(guest, c) is None and ownership.role_in(owner, c) is None
    assert list(ownership.accessible_ceremonies(owner)) == []


@pytest.mark.django_db
def test_hidden_ceremony_states_and_dead_accounts(world, make_user):
    owner, c = make_user(), world["ceremony"]
    own(c, owner)
    c.status = CeremonyStatus.DRAFT
    c.save()
    assert ownership.role_in(owner, c) is None and list(ownership.accessible_ceremonies(owner)) == []
    c.status = CeremonyStatus.READY
    c.save()
    world["studio"].soft_delete()
    c.refresh_from_db()
    assert ownership.role_in(owner, c) is None and list(ownership.accessible_ceremonies(owner)) == []


@pytest.mark.django_db
@pytest.mark.parametrize("change", ["inactive", "deleted"])
def test_inactive_or_deleted_owner_has_no_access(world, make_user, change):
    owner, c = make_user(), world["ceremony"]
    own(c, owner)
    if change == "inactive":
        owner.is_active = False
        owner.save()
    else:
        owner.soft_delete()
    assert ownership.role_in(owner, c) is None and list(ownership.accessible_ceremonies(owner)) == []


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.STUDIO, Role.ADMIN, Role.SUPER_ADMIN])
def test_ceremony_access_is_never_held_by_non_user_roles(world, make_user, role):
    staff, c = make_user(role), world["ceremony"]
    own(c, staff)
    assert ownership.role_in(staff, c) is None
    assert list(ownership.accessible_ceremonies(staff)) == []


# ------------------------------------------------------------ who may invite
@pytest.mark.django_db
def test_invite_capacities(world, make_user, super_admin):
    owner, guest, stranger, c = make_user(), make_user(), make_user(), world["ceremony"]
    own(c, owner)
    view(c, guest, granted_by=owner)
    viewer, owner_role = AccessRole.VIEWER, AccessRole.OWNER
    assert ownership.inviter_kind(owner, c, viewer) == InviterKind.OWNER
    assert ownership.inviter_kind(owner, c, owner_role) == InviterKind.OWNER
    assert ownership.inviter_kind(world["studio_owner"], c, owner_role) == InviterKind.STUDIO
    assert ownership.inviter_kind(super_admin, c, owner_role) == InviterKind.SUPER_ADMIN
    # Viewers cannot reshare; studios/admins cannot hand out VIEWER; strangers/uploaders/other studios nothing.
    assert not ownership.can_invite(guest, c, viewer) and not ownership.can_invite(guest, c, owner_role)
    assert not ownership.can_invite(world["studio_owner"], c, viewer)
    assert not ownership.can_invite(super_admin, c, viewer)
    for nobody in (stranger, world["uploader"], world["other_studio_owner"]):
        assert not ownership.can_invite(nobody, c, viewer) and not ownership.can_invite(nobody, c, owner_role)


# --------------------------------------------------------------- revocation
@pytest.mark.django_db
def test_owner_cannot_revoke_unrelated_ownership(world, make_user, super_admin):
    bride, groom, c = make_user(), make_user(), world["ceremony"]
    bride_row = own(c, bride, OwnerType.BRIDE)
    groom_row = own(c, groom, OwnerType.GROOM)
    assert not ownership.can_revoke_ownership(bride, groom_row)
    assert not ownership.can_revoke_ownership(world["studio_owner"], groom_row)
    assert ownership.can_revoke_ownership(groom, groom_row)  # leaving is allowed
    assert ownership.can_revoke_ownership(super_admin, bride_row)


@pytest.mark.django_db
def test_owner_revokes_only_viewers_they_granted(world, make_user, super_admin):
    a, b, guest, c = make_user(), make_user(), make_user(), world["ceremony"]
    a_row = own(c, a)
    own(c, b)
    access = view(c, guest, granted_by=a)
    assert ownership.can_revoke_viewer(a, access)
    assert not ownership.can_revoke_viewer(b, access)
    assert ownership.can_revoke_viewer(guest, access)  # the viewer may leave
    assert ownership.can_revoke_viewer(super_admin, access)
    a_row.status = OwnershipStatus.REVOKED
    a_row.save()
    assert not ownership.can_revoke_viewer(a, access)  # no longer an owner


@pytest.mark.django_db
def test_invitation_revocation_rights(world, make_user, super_admin):
    a, b, c = make_user(), make_user(), world["ceremony"]
    own(c, a)
    own(c, b)
    by_a = invitation(c, "+998901234567", role=AccessRole.VIEWER, by=a)
    by_studio = invitation(c, "+998901234568", by=world["studio_owner"])
    assert ownership.can_revoke_invitation(a, by_a) and not ownership.can_revoke_invitation(b, by_a)
    assert not ownership.can_revoke_invitation(world["studio_owner"], by_a)
    assert ownership.can_revoke_invitation(world["studio_owner"], by_studio)
    assert not ownership.can_revoke_invitation(world["uploader"], by_studio)
    assert not ownership.can_revoke_invitation(world["other_studio_owner"], by_studio)
    assert not ownership.can_revoke_invitation(a, by_studio)
    assert ownership.can_revoke_invitation(super_admin, by_a)
    by_a.status = InvitationStatus.ACCEPTED
    assert not ownership.can_revoke_invitation(a, by_a)


# ------------------------------------------------------------ owner approval
@pytest.mark.django_db
def test_owner_request_needs_every_current_owner(world, make_user):
    bride, groom, father, c = make_user(), make_user(), make_user(), world["ceremony"]
    own(c, bride, OwnerType.BRIDE)
    groom_row = own(c, groom, OwnerType.GROOM)
    assert set(ownership.approvers_for(c)) == {bride.pk, groom.pk}
    assert ownership.approvers_for(c, exclude_user_id=bride.pk) == [groom.pk]

    request = own(c, father, OwnerType.FAMILY_OWNER, status=OwnershipStatus.PENDING, invited_by=bride)
    approvals = {u.pk: CeremonyOwnershipApproval.objects.create(ownership=request, approver=u) for u in (bride, groom)}
    assert ownership.approval_outcome(request) == ApprovalDecision.PENDING
    assert ownership.can_decide_owner_request(groom, request)
    assert not ownership.can_decide_owner_request(father, request)  # cannot approve themself

    approvals[bride.pk].decision = ApprovalDecision.APPROVED
    approvals[bride.pk].save()
    assert ownership.approval_outcome(request) == ApprovalDecision.PENDING  # groom still has to decide

    approvals[groom.pk].decision = ApprovalDecision.REJECTED
    approvals[groom.pk].save()
    assert ownership.approval_outcome(request) == ApprovalDecision.REJECTED

    # A vote stops counting once the voter is no longer an owner.
    groom_row.status = OwnershipStatus.REVOKED
    groom_row.save()
    assert ownership.approval_outcome(request) == ApprovalDecision.APPROVED
    assert not ownership.can_decide_owner_request(groom, request)


@pytest.mark.django_db
@pytest.mark.parametrize("change", ["role", "inactive", "deleted"])
def test_owner_who_stops_being_a_client_no_longer_blocks_requests(world, make_user, change):
    groom, bride, c = make_user(), make_user(), world["ceremony"]
    own(c, groom, OwnerType.GROOM)
    request = own(c, bride, OwnerType.BRIDE, status=OwnershipStatus.PENDING)
    CeremonyOwnershipApproval.objects.create(ownership=request, approver=groom)
    assert ownership.approval_outcome(request) == ApprovalDecision.PENDING

    if change == "role":
        groom.role = Role.VENUE_OWNER
        groom.save()
    elif change == "inactive":
        groom.is_active = False
        groom.save()
    else:
        groom.soft_delete()
    # The groom can no longer decide, so their vote must not keep the request waiting.
    assert not ownership.can_decide_owner_request(groom, request)
    assert ownership.approvers_for(c) == []
    assert ownership.approval_outcome(request) == ApprovalDecision.APPROVED


@pytest.mark.django_db
@pytest.mark.parametrize("change", ["role", "inactive", "delete"])
def test_account_change_settles_requests_waiting_on_that_owner(world, make_user, super_admin, client_for, change):
    groom, bride, c = make_user(), make_user(), world["ceremony"]
    own(c, groom, OwnerType.GROOM)
    request = own(c, bride, OwnerType.BRIDE, status=OwnershipStatus.PENDING)
    CeremonyOwnershipApproval.objects.create(ownership=request, approver=groom)

    api, url = client_for(super_admin), f"/api/v1/users/{groom.pk}/"
    if change == "delete":
        res = api.delete(url)
    else:
        body = {"role": Role.VENUE_OWNER} if change == "role" else {"is_active": False}
        res = api.patch(url, body, format="json")
    assert res.status_code in (200, 204), res.data
    request.refresh_from_db()
    assert request.status == OwnershipStatus.ACCEPTED
    assert ownership.role_in(bride, c) == AccessRole.OWNER


@pytest.mark.django_db
def test_viewer_cannot_approve_owner_requests(world, make_user):
    owner, guest, newcomer, c = make_user(), make_user(), make_user(), world["ceremony"]
    own(c, owner)
    view(c, guest, granted_by=owner)
    request = own(c, newcomer, status=OwnershipStatus.PENDING)
    CeremonyOwnershipApproval.objects.create(ownership=request, approver=guest)  # forged row
    assert not ownership.can_decide_owner_request(guest, request)


# ------------------------------------------------------- identifier privacy
@pytest.mark.django_db
def test_identifiers_are_normalised_encrypted_and_domain_separated(world):
    a = ownership.seal_identifier(IdentifierType.PHONE, "90 123-45-67")
    b = ownership.seal_identifier(IdentifierType.PHONE, "+998 (90) 123 45 67")
    assert a["recipient_identifier_hash"] == b["recipient_identifier_hash"]
    assert a["recipient_hint"] == "+99890***4567"
    assert "901234567" not in a["recipient_identifier_encrypted"]

    pinfl = next_pinfl()
    p = ownership.seal_identifier(IdentifierType.PINFL, pinfl)
    assert pinfl not in p["recipient_identifier_encrypted"] and pinfl not in p["recipient_hint"]
    assert p["recipient_hint"].endswith(pinfl[-4:]) and p["recipient_hint"].count("*") == 10
    # Same digits as phone vs. JSHSHIR never collide.
    assert (
        ownership.phone_index("+998901234567")
        != ownership.seal_identifier(IdentifierType.PINFL, pinfl)["recipient_identifier_hash"]
    )

    inv = invitation(world["ceremony"], pinfl, identifier_type=IdentifierType.PINFL)
    stored = " ".join(str(v) for v in CeremonyInvitation.objects.filter(pk=inv.pk).values().get().values())
    assert pinfl not in stored


@pytest.mark.django_db
@pytest.mark.parametrize(("kind", "raw"), [("PHONE", "12345"), ("PINFL", "1234"), ("PINFL", "11111111111111")])
def test_malformed_identifiers_rejected(kind, raw):
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        ownership.seal_identifier(kind, raw)


@pytest.mark.django_db
def test_invitations_reach_only_the_matching_account(world, make_user):
    pinfl = next_pinfl()
    alice, bob, c = make_user(pinfl=pinfl), make_user(), world["ceremony"]
    by_phone = invitation(c, alice.phone_number)
    by_pinfl = invitation(c, pinfl, identifier_type=IdentifierType.PINFL, owner_type=OwnerType.FAMILY_OWNER)
    invitation(c, "+998990000001")  # someone without an account
    assert set(ownership.invitations_for(alice)) == {by_phone, by_pinfl}
    assert list(ownership.invitations_for(bob)) == []
    assert ownership.is_recipient(alice, by_pinfl) and not ownership.is_recipient(bob, by_pinfl)

    by_phone.expires_at = timezone.now() - timedelta(seconds=1)
    by_phone.save()
    by_pinfl.status = InvitationStatus.REVOKED
    by_pinfl.save()
    assert list(ownership.invitations_for(alice)) == []


@pytest.mark.django_db
def test_studio_account_with_matching_phone_sees_no_invitations(world):
    invitation(world["ceremony"], world["studio_owner"].phone_number)
    assert list(ownership.invitations_for(world["studio_owner"])) == []


# ---------------------------------------------------------- responding rules
@pytest.mark.django_db
@override_settings(CEREMONY_OWNER_REQUIRE_VERIFIED_PHONE=True, CEREMONY_INVITE_REQUIRE_VERIFIED_PHONE=False)
def test_unverified_phone_cannot_claim_ownership(world, make_user):
    user, c = make_user(), world["ceremony"]
    owner_inv = invitation(c, user.phone_number)
    assert ownership.response_refusal(user, owner_inv, accepting=True) == ownership.Refusal.PHONE_NOT_VERIFIED
    assert ownership.response_refusal(user, owner_inv, accepting=False) is None  # declining is always allowed

    inviter, other = make_user(), world["other"]
    own(other, inviter)
    viewer_inv = invitation(other, user.phone_number, role=AccessRole.VIEWER, by=inviter)
    assert ownership.response_refusal(user, viewer_inv, accepting=True) is None

    user.is_phone_verified = True
    assert ownership.response_refusal(user, owner_inv, accepting=True) is None


@pytest.mark.django_db
def test_response_refusals(world, make_user):
    user, other, c = make_user(is_phone_verified=True), make_user(is_phone_verified=True), world["ceremony"]
    inv = invitation(c, user.phone_number)
    assert ownership.response_refusal(other, inv, accepting=True) == ownership.Refusal.NOT_FOUND  # wrong user
    assert ownership.response_refusal(world["studio_owner"], inv, accepting=True) == ownership.Refusal.NOT_FOUND

    inv.expires_at = timezone.now() - timedelta(minutes=1)
    assert ownership.response_refusal(user, inv, accepting=True) == ownership.Refusal.EXPIRED
    inv.expires_at = ownership.default_expiry()

    own(c, user)
    assert ownership.response_refusal(user, inv, accepting=True) == ownership.Refusal.ALREADY_HAS_ACCESS
    inv.status = InvitationStatus.DECLINED
    assert ownership.response_refusal(user, inv, accepting=False) == ownership.Refusal.NOT_FOUND


# ---------------------------------------------------------- DB constraints
@pytest.mark.django_db
def test_database_constraints(world, make_user):
    user, other, c = make_user(), make_user(), world["ceremony"]
    invitation(c, user.phone_number)
    # duplicate pending invitation (any input format)
    assert violates(lambda: invitation(c, user.phone_number.replace("+998", "")))
    # VIEWER invitations come from owners only; OWNER invitations need an owner type
    assert violates(lambda: invitation(c, "+998901110001", role=AccessRole.VIEWER, inviter_kind=InviterKind.STUDIO))
    assert violates(lambda: invitation(c, "+998901110002", owner_type=""))
    assert violates(lambda: invitation(c, "+998901110003", status=InvitationStatus.ACCEPTED))  # no user
    # one open ownership per user, one bride per ceremony, accepted rows carry a timestamp
    own(c, user, OwnerType.BRIDE)
    assert violates(lambda: own(c, user, OwnerType.FAMILY_OWNER, status=OwnershipStatus.PENDING))
    assert violates(lambda: own(c, other, OwnerType.BRIDE, status=OwnershipStatus.PENDING))
    assert violates(
        lambda: CeremonyOwnership.objects.create(
            ceremony=c, user=other, owner_type=OwnerType.GROOM, status=OwnershipStatus.ACCEPTED
        )
    )
    # one active viewer access per user; history rows are fine
    view(c, other, status=ViewerStatus.REVOKED)
    view(c, other)
    assert violates(lambda: view(c, other))


# ------------------------------------------------------------- permissions
@pytest.mark.django_db
def test_drf_object_permissions(world, make_user):
    owner, guest, stranger, c = make_user(), make_user(), make_user(), world["ceremony"]
    own(c, owner)
    access = view(c, guest, granted_by=owner)
    factory = APIRequestFactory()

    def allowed(permission, user, obj):
        request = factory.get("/")
        request.user = user
        return permission.has_permission(request, None) and permission.has_object_permission(request, None, obj)

    assert allowed(IsCeremonyOwner(), owner, c) and not allowed(IsCeremonyOwner(), guest, c)
    assert allowed(IsCeremonyMember(), guest, c) and allowed(IsCeremonyMember(), guest, access)
    assert not allowed(IsCeremonyMember(), stranger, c)
    assert not allowed(IsCeremonyMember(), world["studio_owner"], c)
    assert not allowed(IsCeremonyMember(), guest, world["other"])
    assert IsCeremonyMember().access_grant(None).roles == frozenset({Role.USER.value})


# ---------------------------------------------------------------- backfill
@pytest.mark.django_db
def test_backfill_from_v1_participants_is_faithful_and_idempotent(world, make_user):
    c, studio_owner = world["ceremony"], world["studio_owner"]
    bride, guest = make_user(), make_user()
    now = timezone.now()
    rows = {
        "active": CeremonyParticipant.objects.create(
            ceremony=c, phone_number=bride.phone_number, user=bride, participant_type="BRIDE",
            access_status=AccessStatus.ACTIVE, invited_by=studio_owner, responded_at=now,
        ),
        "invited": CeremonyParticipant.objects.create(
            ceremony=c, phone_number="+998901230001", participant_type="GROOM", invited_by=studio_owner
        ),
        "declined": CeremonyParticipant.objects.create(
            ceremony=c, phone_number="+998901230002", participant_type="OTHER", access_status=AccessStatus.DECLINED
        ),
        "revoked": CeremonyParticipant.objects.create(
            ceremony=c, phone_number=guest.phone_number, user=guest, participant_type="OTHER",
            access_status=AccessStatus.REVOKED, responded_at=now,
        ),
    }  # fmt: skip
    assert backfill(django_apps) == 4
    assert backfill(django_apps) == 0  # idempotent

    inv = {k: CeremonyInvitation.objects.get(legacy_participant=p) for k, p in rows.items()}
    assert {k: i.status for k, i in inv.items()} == {
        "active": "ACCEPTED", "invited": "PENDING", "declined": "DECLINED", "revoked": "REVOKED"
    }  # fmt: skip
    assert all(i.requested_role == AccessRole.OWNER and i.inviter_kind == InviterKind.STUDIO for i in inv.values())
    assert inv["declined"].owner_type == OwnerType.OTHER_OWNER
    assert inv["invited"].expires_at > timezone.now()
    assert ownership.is_recipient(bride, inv["active"])
    assert "+998" not in inv["invited"].recipient_identifier_encrypted

    assert ownership.role_in(bride, c) == AccessRole.OWNER
    assert ownership.role_in(guest, c) is None
    assert CeremonyOwnership.objects.get(user=guest).status == OwnershipStatus.REVOKED
    assert CeremonyOwnership.objects.count() == 2
