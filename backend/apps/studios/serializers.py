from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.accounts.serializers import PhoneNumberField, UserSummarySerializer
from apps.core.uploads import process_image
from apps.reviews.models import TargetKind
from apps.reviews.serializers import StatsSerializer, public_author_name
from apps.reviews.services import empty_stats, stats_map
from apps.subscriptions.badges import PaidBadgeSerializer

from . import services
from .models import PortfolioKind, PortfolioStorage, Studio, StudioDayStatus, StudioImage


def _absolute(context, url: str) -> str:
    request = context.get("request")
    return request.build_absolute_uri(url) if request is not None else url


class StudioImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(help_text="Rasm yoki reels muqovasi")
    video = serializers.SerializerMethodField()

    class Meta:
        model = StudioImage
        fields = ["id", "kind", "image", "video", "caption", "duration", "size_bytes", "position", "created_at"]
        read_only_fields = fields

    def _file_url(self, item, part: str) -> str:
        url = reverse("studio-portfolio-file", kwargs={"studio_id": item.studio_id, "item_id": item.pk, "part": part})
        return _absolute(self.context, url)

    def get_image(self, item) -> str | None:
        if item.storage == PortfolioStorage.DRIVE:
            return self._file_url(item, "poster" if item.kind == PortfolioKind.VIDEO else "main")
        return _absolute(self.context, item.image.url) if item.image else None

    def get_video(self, item) -> str | None:
        if item.kind != PortfolioKind.VIDEO:
            return None
        if item.storage == PortfolioStorage.DRIVE:
            return self._file_url(item, "main")
        return _absolute(self.context, item.video.url) if item.video else None


class PortfolioUsageSerializer(serializers.Serializer):
    used_bytes = serializers.IntegerField()
    quota_bytes = serializers.IntegerField()
    free_bytes = serializers.IntegerField()
    storage = serializers.ChoiceField(choices=PortfolioStorage.choices, help_text="Yangi fayllar qayerga yoziladi")


class StudioImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()


class ReelUploadSerializer(serializers.Serializer):
    video = serializers.FileField(help_text="Vertikal (9:16) MP4 / MOV / WEBM, 1–90 soniya")
    poster = serializers.ImageField(required=False, help_text="Muqova kadri (server ffmpeg bilan o'zi ham oladi)")
    caption = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class PortfolioItemUpdateSerializer(serializers.Serializer):
    caption = serializers.CharField(max_length=300, allow_blank=True)


class EngagementSerializer(serializers.Serializer):
    like_count = serializers.IntegerField()
    dislike_count = serializers.IntegerField()
    comment_count = serializers.IntegerField()
    my_reaction = serializers.ChoiceField(choices=["like", "dislike"], allow_null=True)


class PortfolioItemSerializer(StudioImageSerializer):
    """A portfolio item with its likes / dislikes / comment count (``context["engagement"]``)."""

    engagement = serializers.SerializerMethodField()

    class Meta(StudioImageSerializer.Meta):
        fields = [*StudioImageSerializer.Meta.fields, "engagement"]
        read_only_fields = fields

    @extend_schema_field(EngagementSerializer)
    def get_engagement(self, item) -> dict:
        engagement = self.context.get("engagement")
        if engagement is None:
            request = self.context.get("request")
            engagement = services.engagement_map([item.pk], getattr(request, "user", None))
        return engagement.get(item.pk, services.empty_engagement())


class ReactionWriteSerializer(serializers.Serializer):
    value = serializers.ChoiceField(choices=["like", "dislike"])


class CommentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    author_name = serializers.SerializerMethodField()
    text = serializers.CharField()
    created_at = serializers.DateTimeField()
    is_mine = serializers.SerializerMethodField()

    def get_author_name(self, comment) -> str:
        return public_author_name(comment.author)

    def get_is_mine(self, comment) -> bool:
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and comment.author_id == request.user.pk)


class CommentWriteSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=500)

    def validate_text(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Izoh bo'sh bo'lmasligi kerak.")
        return value


class StudioSerializer(PaidBadgeSerializer, serializers.ModelSerializer):
    responsible_user = UserSummarySerializer(read_only=True)
    responsible_user_id = serializers.PrimaryKeyRelatedField(
        source="responsible_user",
        queryset=User.objects.alive().filter(role=Role.STUDIO, is_active=True),
        write_only=True,
        error_messages={
            "does_not_exist": "Mas'ul shaxs topilmadi yoki u faol STUDIO rolidagi foydalanuvchi emas.",
        },
    )
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    images = StudioImageSerializer(many=True, read_only=True)
    phone_number = PhoneNumberField(required=False, allow_blank=True)
    portfolio_quota_mb = serializers.IntegerField(
        min_value=0, max_value=1024 * 1024, required=False, help_text="Portfolio uchun joy (MB), standart 1024"
    )
    portfolio_used_bytes = serializers.SerializerMethodField()

    class Meta:
        model = Studio
        fields = [
            "is_verified",
            "id",
            "name",
            "description",
            "profile_picture",
            "address",
            "phone_number",
            "images",
            "portfolio_quota_mb",
            "portfolio_used_bytes",
            "responsible_user",
            "responsible_user_id",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        value = " ".join(value.split())
        qs = Studio.objects.filter(deleted_at__isnull=True, name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu nomdagi studiya allaqachon mavjud.")
        return value

    def validate_description(self, value: str) -> str:
        return value.strip()

    def validate_address(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Manzil kiritilishi shart.")
        return value

    def validate_profile_picture(self, value):
        return process_image(value) if value else value

    def get_portfolio_used_bytes(self, studio) -> int:
        return sum(item.size_bytes for item in studio.images.all())


# ------------------------------------------------------------------ public
class PublicStudioSerializer(PaidBadgeSerializer, serializers.ModelSerializer):
    """What customers see about a studio: the business and its portfolio, never its staff or clients."""

    images = serializers.SerializerMethodField(help_text="Faqat rasmlar")
    reels = serializers.SerializerMethodField(help_text="Vertikal videolar — faqat galichka faol bo'lsa")
    chat_enabled = serializers.SerializerMethodField(help_text="Studiyaga yozish mumkinmi (galichka faol)")
    stats = serializers.SerializerMethodField()

    class Meta:
        model = Studio
        fields = [
            "is_verified",
            "id",
            "name",
            "description",
            "profile_picture",
            "address",
            "phone_number",
            "images",
            "reels",
            "chat_enabled",
            "stats",
        ]
        read_only_fields = fields

    def _items(self, studio, kind):
        return [item for item in studio.images.all() if item.kind == kind]

    @extend_schema_field(PortfolioItemSerializer(many=True))
    def get_images(self, studio) -> list:
        return PortfolioItemSerializer(self._items(studio, PortfolioKind.IMAGE), many=True, context=self.context).data

    @extend_schema_field(PortfolioItemSerializer(many=True))
    def get_reels(self, studio) -> list:
        if not self.get_is_verified(studio):
            return []
        return PortfolioItemSerializer(self._items(studio, PortfolioKind.VIDEO), many=True, context=self.context).data

    def get_chat_enabled(self, studio) -> bool:
        return self.get_is_verified(studio)

    @extend_schema_field(StatsSerializer)
    def get_stats(self, studio) -> dict:
        stats = self.context.get("stats")
        if stats is None:
            stats = stats_map(TargetKind.STUDIO, [studio.pk])
        return stats.get(studio.pk, empty_stats())


class StudioScheduleSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    busy = serializers.DictField(
        child=serializers.IntegerField(), help_text="{YYYY-MM-DD: shu kuni marosimlar soni} — bo'sh kunlar yo'q."
    )
    days = serializers.DictField(
        child=serializers.ChoiceField(choices=StudioDayStatus.Status.choices),
        help_text="{YYYY-MM-DD: BUSY | OFF} — studiya qo'lda belgilagan kunlar",
    )
    off_weekdays = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6), help_text="Haftalik dam olish kunlari (0 = Dushanba)"
    )


class StudioPanelScheduleSerializer(StudioScheduleSerializer):
    notes = serializers.DictField(child=serializers.CharField(), help_text="{YYYY-MM-DD: ichki izoh}")


class DayStatusWriteSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=StudioDayStatus.Status.choices, allow_null=True)
    note = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class OffWeekdaysSerializer(serializers.Serializer):
    off_weekdays = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), max_length=7)


class StudioCalendarEntrySerializer(serializers.Serializer):
    """Panel view of a studio's ceremonies in a date range."""

    id = serializers.UUIDField()
    title = serializers.CharField()
    event_type = serializers.CharField()
    event_date = serializers.DateField()
    status = serializers.CharField()


# --------------------------------------------------------------------- chat
class ChatMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    body = serializers.CharField()
    from_studio = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class ChatMessageWriteSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000)

    def validate_body(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Xabar bo'sh bo'lmasligi kerak.")
        return value


class ChatStudioSerializer(PaidBadgeSerializer, serializers.ModelSerializer):
    class Meta:
        model = Studio
        fields = ["is_verified", "id", "name", "profile_picture"]
        read_only_fields = fields


class _ConversationBase(serializers.Serializer):
    id = serializers.UUIDField()
    last_message_at = serializers.DateTimeField()
    unread = serializers.IntegerField()
    last_message = serializers.SerializerMethodField()

    @extend_schema_field(ChatMessageSerializer(allow_null=True))
    def get_last_message(self, conversation):
        message = self.context.get("last_messages", {}).get(conversation.pk)
        return ChatMessageSerializer(message).data if message else None


class UserConversationSerializer(_ConversationBase):
    studio = ChatStudioSerializer()


class ChatCustomerSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.SerializerMethodField()

    def get_name(self, user) -> str:
        return f"{user.first_name} {user.last_name}".strip() or "Foydalanuvchi"


class StudioConversationSerializer(_ConversationBase):
    customer = ChatCustomerSerializer(source="user")


class UserThreadSerializer(serializers.Serializer):
    studio = ChatStudioSerializer()
    can_write = serializers.BooleanField(help_text="Studiya galichkasi faol")
    messages = ChatMessageSerializer(many=True)


class StudioThreadSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    customer = ChatCustomerSerializer()
    can_write = serializers.BooleanField(help_text="Galichka faol va so'rovchi OWNER / MANAGER")
    messages = ChatMessageSerializer(many=True)
