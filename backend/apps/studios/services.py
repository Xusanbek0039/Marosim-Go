import datetime

from django.db import transaction
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.audit.services import AuditAction, record
from apps.core.uploads import process_image

from . import reels
from .models import (
    MAX_PORTFOLIO_IMAGES,
    MAX_PORTFOLIO_REELS,
    PortfolioKind,
    Studio,
    StudioDayStatus,
    StudioImage,
    StudioMembership,
    StudioPortfolioComment,
    StudioPortfolioReaction,
)


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


# ------------------------------------------------------------------- galichka
class BadgeRequired(APIException):
    """A galichka-only feature (reels, reactions, comments, chat) of a studio without an active badge."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Bu imkoniyat faqat galichkasi faol studiyalarda ishlaydi."
    default_code = "badge_required"


def has_badge(studio: Studio) -> bool:
    from apps.subscriptions.services import business_verified

    return business_verified(studio=studio)


def require_badge(studio: Studio) -> None:
    if not has_badge(studio):
        raise BadgeRequired()


# ---------------------------------------------------------------- portfolio
PORTFOLIO_MAX_SIDE = 1920


def public_studios():
    """Studios shown to customers: active and not deleted (studios are created by the panel)."""
    return Studio.objects.filter(deleted_at__isnull=True, is_active=True)


def _next_position(studio: Studio) -> int:
    last = studio.images.order_by("-position").values_list("position", flat=True).first()
    return 0 if last is None else last + 1


@transaction.atomic
def add_portfolio_image(request, studio: Studio, upload) -> StudioImage:
    """Re-encode (WEBP, no EXIF) and append one portfolio image; the studio row is locked while counting."""
    studio = Studio.objects.select_for_update().get(pk=studio.pk)
    if studio.images.filter(kind=PortfolioKind.IMAGE).count() >= MAX_PORTFOLIO_IMAGES:
        raise ValidationError({"image": [f"Ko'pi bilan {MAX_PORTFOLIO_IMAGES} ta rasm yuklash mumkin."]})
    try:
        content = process_image(upload, max_side=PORTFOLIO_MAX_SIDE)
    except ValidationError as exc:
        detail = exc.detail if isinstance(exc.detail, list) else [exc.detail]
        raise ValidationError({"image": detail}) from None
    image = StudioImage.objects.create(studio=studio, image=content, position=_next_position(studio))
    record(request, AuditAction.CREATE, image, changes={"studio": str(studio.pk), "position": image.position})
    return image


@transaction.atomic
def add_portfolio_reel(request, studio: Studio, video, poster=None, caption: str = "") -> StudioImage:
    """Append one vertical video. Needs the studio's galichka (checked under the studio row lock)."""
    studio = Studio.objects.select_for_update().get(pk=studio.pk)
    require_badge(studio)
    if studio.images.filter(kind=PortfolioKind.VIDEO).count() >= MAX_PORTFOLIO_REELS:
        raise ValidationError({"video": [f"Ko'pi bilan {MAX_PORTFOLIO_REELS} ta video yuklash mumkin."]})
    data = reels.prepare(video, poster)
    item = StudioImage.objects.create(
        studio=studio, kind=PortfolioKind.VIDEO, caption=caption.strip(), position=_next_position(studio), **data
    )
    record(request, AuditAction.CREATE, item, changes={"studio": str(studio.pk), "kind": item.kind})
    return item


@transaction.atomic
def update_portfolio_item(request, item: StudioImage, caption: str) -> StudioImage:
    before = item.caption
    item.caption = caption.strip()
    item.save(update_fields=["caption", "updated_at"])
    record(request, AuditAction.UPDATE, item, changes={"caption": [before, item.caption]})
    return item


@transaction.atomic
def delete_portfolio_image(request, image: StudioImage) -> None:
    image_id, studio_id, files = image.pk, image.studio_id, [image.image, image.video]
    image.delete()
    record(
        request, AuditAction.DELETE, image, changes={"studio": str(studio_id)}, target_label=f"StudioImage {image_id}"
    )
    transaction.on_commit(lambda: [f.delete(save=False) for f in files if f])


# --------------------------------------------------- reactions and comments
def public_items(studio: Studio, verified: bool | None = None):
    """Portfolio items customers may see: photos always, reels only while the galichka is active."""
    items = studio.images.all()
    if verified is None:
        verified = has_badge(studio)
    return items if verified else items.filter(kind=PortfolioKind.IMAGE)


REACTION_NAMES = {StudioPortfolioReaction.LIKE: "like", StudioPortfolioReaction.DISLIKE: "dislike"}


def empty_engagement() -> dict:
    return {"like_count": 0, "dislike_count": 0, "comment_count": 0, "my_reaction": None}


def engagement_map(item_ids, user=None) -> dict:
    """``{item_id: {like_count, dislike_count, comment_count, my_reaction}}`` in two queries."""
    item_ids = list(item_ids)
    if not item_ids:
        return {}
    rows = (
        StudioImage.objects.filter(pk__in=item_ids)
        .annotate(
            like_count=Count("reactions", filter=Q(reactions__value=StudioPortfolioReaction.LIKE), distinct=True),
            dislike_count=Count(
                "reactions", filter=Q(reactions__value=StudioPortfolioReaction.DISLIKE), distinct=True
            ),
            comment_count=Count("comments", filter=Q(comments__is_hidden=False), distinct=True),
        )
        .values("pk", "like_count", "dislike_count", "comment_count")
    )
    mine = {}
    if user is not None and user.is_authenticated:
        mine = dict(
            StudioPortfolioReaction.objects.filter(item_id__in=item_ids, user=user).values_list("item_id", "value")
        )
    return {
        row["pk"]: {
            "like_count": row["like_count"],
            "dislike_count": row["dislike_count"],
            "comment_count": row["comment_count"],
            "my_reaction": REACTION_NAMES.get(mine.get(row["pk"])),
        }
        for row in rows
    }


@transaction.atomic
def set_reaction(item: StudioImage, user, value: str | None) -> dict:
    """``value``: "like" / "dislike" (upsert) or ``None`` (remove). Returns the item's fresh counts."""
    require_badge(item.studio)
    if value is None:
        StudioPortfolioReaction.objects.filter(item=item, user=user).delete()
    else:
        number = StudioPortfolioReaction.LIKE if value == "like" else StudioPortfolioReaction.DISLIKE
        StudioPortfolioReaction.objects.update_or_create(item=item, user=user, defaults={"value": number})
    return engagement_map([item.pk], user)[item.pk]


def visible_comments(item: StudioImage):
    return item.comments.filter(is_hidden=False).select_related("author")


@transaction.atomic
def add_comment(request, item: StudioImage, text: str) -> StudioPortfolioComment:
    require_badge(item.studio)
    return StudioPortfolioComment.objects.create(item=item, author=request.user, text=text.strip())


@transaction.atomic
def delete_comment(request, comment: StudioPortfolioComment, *, by_studio: bool) -> None:
    comment_id, item_id = comment.pk, comment.item_id
    comment.delete()
    record(
        request,
        AuditAction.DELETE,
        comment,
        changes={"item": str(item_id), "by_studio": by_studio},
        target_label=f"StudioPortfolioComment {comment_id}",
    )


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


def schedule(studio: Studio, start: datetime.date, end: datetime.date, *, with_notes: bool = False) -> dict:
    """Calendar data: ceremonies per day, days marked by hand and the weekly days off."""
    days = list(studio.day_statuses.filter(date__gte=start, date__lte=end))
    data = {
        "date_from": start,
        "date_to": end,
        "busy": busy_days(studio, start, end),
        "days": {d.date.isoformat(): d.status for d in days},
        "off_weekdays": sorted(set(studio.off_weekdays or [])),
    }
    if with_notes:
        data["notes"] = {d.date.isoformat(): d.note for d in days if d.note}
    return data


@transaction.atomic
def set_day_status(request, studio: Studio, date: datetime.date, status_value: str | None, note: str = "") -> None:
    """Mark (or with ``None`` clear) one day as BUSY / OFF on the studio's calendar."""
    if status_value is None:
        StudioDayStatus.objects.filter(studio=studio, date=date).delete()
    else:
        StudioDayStatus.objects.update_or_create(
            studio=studio, date=date, defaults={"status": status_value, "note": note.strip()}
        )
    record(request, AuditAction.UPDATE, studio, changes={"day": date.isoformat(), "status": status_value})


@transaction.atomic
def set_off_weekdays(request, studio: Studio, weekdays: list[int]) -> Studio:
    before = studio.off_weekdays
    studio.off_weekdays = sorted(set(weekdays))
    studio.save(update_fields=["off_weekdays", "updated_at"])
    record(request, AuditAction.UPDATE, studio, changes={"off_weekdays": [before, studio.off_weekdays]})
    return studio
