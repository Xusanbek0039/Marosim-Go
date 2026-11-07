from .models import Studio, StudioMembership


def sync_owner_membership(studio: Studio, previous_owner_id=None) -> StudioMembership:
    """Mirror ``Studio.responsible_user`` as the studio's active OWNER membership.

    On an owner change the previous owner's membership is deactivated (not demoted): handing a
    studio over must not silently leave the old owner with access to its ceremonies.
    """
    if previous_owner_id and previous_owner_id != studio.responsible_user_id:
        StudioMembership.objects.filter(studio=studio, user_id=previous_owner_id).update(is_active=False)
    membership, _ = StudioMembership.objects.update_or_create(
        studio=studio,
        user_id=studio.responsible_user_id,
        defaults={"role": StudioMembership.Role.OWNER, "is_active": True},
    )
    return membership


def active_memberships(user):
    """Memberships that grant studio-side access right now."""
    return StudioMembership.objects.filter(
        user=user,
        is_active=True,
        studio__is_active=True,
        studio__deleted_at__isnull=True,
    ).select_related("studio")
