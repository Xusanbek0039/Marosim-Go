"""Review / like rules and the rating numbers shown on public cards."""

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.services import AuditAction, record

from .models import Like, Review, TargetKind

#: Newest visible reviews returned with a business profile.
PUBLIC_REVIEW_LIMIT = 50


def _field(kind: str) -> str:
    return "venue" if kind == TargetKind.VENUE else "studio"


def visible_reviews(kind: str, target):
    return (
        Review.objects.filter(**{_field(kind): target}, is_hidden=False)
        .select_related("author")
        .order_by("-created_at")
    )


def empty_stats() -> dict:
    return {"rating_avg": None, "rating_count": 0, "like_count": 0}


def stats_map(kind: str, ids) -> dict:
    """``{target_id: {rating_avg, rating_count, like_count}}`` for many businesses in two queries."""
    field = _field(kind)
    ids = list(ids)
    out = {pk: empty_stats() for pk in ids}
    ratings = (
        Review.objects.filter(**{f"{field}_id__in": ids}, is_hidden=False)
        .values(f"{field}_id")
        .annotate(avg=Avg("rating"), n=Count("id"))
    )
    for row in ratings:
        out[row[f"{field}_id"]].update(rating_avg=round(float(row["avg"]), 1), rating_count=row["n"])
    likes = Like.objects.filter(**{f"{field}_id__in": ids}).values(f"{field}_id").annotate(n=Count("id"))
    for row in likes:
        out[row[f"{field}_id"]]["like_count"] = row["n"]
    return out


def summary(kind: str, target, user) -> dict:
    """Stats of one business plus what the caller did (liked / own review)."""
    data = stats_map(kind, [target.pk])[target.pk]
    field = _field(kind)
    mine = None
    liked = False
    if user is not None and user.is_authenticated:
        liked = Like.objects.filter(**{field: target}, user=user).exists()
        mine = Review.objects.filter(**{field: target}, author=user).first()
    return {**data, "liked": liked, "my_review": mine}


def can_review(user) -> bool:
    """Only customer accounts rate businesses (staff and businesses must not inflate ratings)."""
    return bool(user and user.is_authenticated and user.is_active and user.role == Role.USER)


@transaction.atomic
def upsert_review(request, kind: str, target, *, rating: int, text: str) -> Review:
    field = _field(kind)
    review = Review.objects.select_for_update().filter(**{field: target}, author=request.user).first()
    if review is None:
        try:
            with transaction.atomic():
                review = Review.objects.create(**{field: target}, author=request.user, rating=rating, text=text)
        except IntegrityError:  # a parallel request created it first
            review = Review.objects.get(**{field: target}, author=request.user)
        else:
            record(request, AuditAction.CREATE, review, changes={"rating": rating, field: str(target.pk)})
            return review
    review.rating, review.text = rating, text
    review.save(update_fields=["rating", "text", "updated_at"])
    record(request, AuditAction.UPDATE, review, changes={"rating": rating})
    return review


@transaction.atomic
def delete_own_review(request, kind: str, target) -> None:
    review = Review.objects.filter(**{_field(kind): target}, author=request.user).first()
    if review is not None:
        review.delete()
        record(request, AuditAction.DELETE, review, target_label=f"Review {review.pk}")


def set_like(kind: str, target, user, liked: bool) -> int:
    field = _field(kind)
    if liked:
        try:
            with transaction.atomic():
                Like.objects.get_or_create(**{field: target}, user=user)
        except IntegrityError:  # double click: already liked
            pass
    else:
        Like.objects.filter(**{field: target}, user=user).delete()
    return Like.objects.filter(**{field: target}).count()


@transaction.atomic
def moderate(request, review: Review, *, is_hidden: bool) -> Review:
    if review.is_hidden != is_hidden:
        review.is_hidden = is_hidden
        review.moderated_by, review.moderated_at = request.user, timezone.now()
        review.save(update_fields=["is_hidden", "moderated_by", "moderated_at", "updated_at"])
        record(request, AuditAction.UPDATE, review, changes={"is_hidden": is_hidden})
    return review
