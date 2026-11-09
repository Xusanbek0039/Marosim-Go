from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Review


def public_author_name(user) -> str:
    """E.g. "Aziz K." — never the full surname, phone or any other personal data."""
    first = (user.first_name or "").strip()
    last = (user.last_name or "").strip()
    if not first and not last:
        return "Foydalanuvchi"
    return f"{first} {last[:1]}.".strip() if last else first


class PublicReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "author_name", "rating", "text", "created_at", "updated_at"]
        read_only_fields = fields

    def get_author_name(self, review) -> str:
        return public_author_name(review.author)


class StatsSerializer(serializers.Serializer):
    rating_avg = serializers.FloatField(allow_null=True, help_text="1.0–5.0, yashirilgan sharhlarsiz")
    rating_count = serializers.IntegerField()
    like_count = serializers.IntegerField()


class ReviewSummarySerializer(StatsSerializer):
    liked = serializers.BooleanField(help_text="So'rovchi like bosganmi (mehmon uchun false)")
    my_review = PublicReviewSerializer(allow_null=True)


class ReviewPageSerializer(serializers.Serializer):
    summary = ReviewSummarySerializer()
    results = PublicReviewSerializer(many=True)


class ReviewWriteSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")

    def validate_text(self, value: str) -> str:
        return value.strip()


class LikeResultSerializer(serializers.Serializer):
    liked = serializers.BooleanField()
    like_count = serializers.IntegerField()


class _TargetSerializer(serializers.Serializer):
    kind = serializers.CharField()
    id = serializers.UUIDField()
    name = serializers.CharField()


class _AuthorSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    phone_number = serializers.CharField(allow_null=True)


class AdminReviewSerializer(serializers.ModelSerializer):
    """Panel view: incl. the author's account so moderators can act on abuse."""

    target = serializers.SerializerMethodField()
    author = _AuthorSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "target", "author", "rating", "text", "is_hidden", "moderated_at", "created_at", "updated_at"]
        read_only_fields = ["id", "target", "author", "rating", "text", "moderated_at", "created_at", "updated_at"]

    @extend_schema_field(_TargetSerializer)
    def get_target(self, review) -> dict:
        obj = review.venue or review.studio
        return _TargetSerializer({"kind": review.kind, "id": obj.pk, "name": obj.name}).data
