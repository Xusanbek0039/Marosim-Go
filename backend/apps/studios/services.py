import datetime

from django.db import transaction
from django.db.models import Count
from rest_framework.exceptions import ValidationError

from apps.audit.services import AuditAction, record
from apps.core.uploads import process_image

from .models import MAX_PORTFOLIO_IMAGES, Studio, StudioImage, StudioMembership


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


# ---------------------------------------------------------------- portfolio
PORTFOLIO_MAX_SIDE = 1920


def public_studios():
    """Studios shown to customers: active and not deleted (studios are created by the panel)."""
    return Studio.objects.filter(deleted_at__isnull=True, is_active=True)


@transaction.atomic
def add_portfolio_image(request, studio: Studio, upload) -> StudioImage:
    """Re-encode (WEBP, no EXIF) and append one portfolio image; the studio row is locked while counting."""
    studio = Studio.objects.select_for_update().get(pk=studio.pk)
    count = studio.images.count()
    if count >= MAX_PORTFOLIO_IMAGES:
        raise ValidationError({"image": [f"Ko'pi bilan {MAX_PORTFOLIO_IMAGES} ta rasm yuklash mumkin."]})
    try:
        content = process_image(upload, max_side=PORTFOLIO_MAX_SIDE)
    except ValidationError as exc:
        detail = exc.detail if isinstance(exc.detail, list) else [exc.detail]
        raise ValidationError({"image": detail}) from None
    last = studio.images.order_by("-position").values_list("position", flat=True).first()
    image = StudioImage.objects.create(studio=studio, image=content, position=(last or 0) + 1 if count else 0)
    record(request, AuditAction.CREATE, image, changes={"studio": str(studio.pk), "position": image.position})
    return image


@transaction.atomic
def delete_portfolio_image(request, image: StudioImage) -> None:
    image_id, studio_id, file = image.pk, image.studio_id, image.image
    image.delete()
    record(
        request, AuditAction.DELETE, image, changes={"studio": str(studio_id)}, target_label=f"StudioImage {image_id}"
    )
    transaction.on_commit(lambda: file.delete(save=False))


# ----------------------------------------------------------------- schedule
def busy_days(studio: Studio, start: datetime.date, end: datetime.date) -> dict[str, int]:
    """``{YYYY-MM-DD: ceremonies that day}`` — the studio's public schedule (no titles, no customers)."""
    from apps.ceremonies.models import Ceremony  # ceremonies → studios: import lazily, never at module level

    rows = (
        Ceremony.objects.filter(studio=studio, event_date__gte=start, event_date__lte=end)
        .values("event_date")
        .annotate(n=Count("id"))
    )
    return {row["event_date"].isoformat(): row["n"] for row in rows}
