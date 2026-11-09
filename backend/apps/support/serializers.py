from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import SupportMessage, SupportTicket

STAFF_LABEL = "MarosimGo yordam xizmati"


class TicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    body = serializers.CharField(max_length=5000)


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=5000)


class _PersonSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(source="full_name", allow_null=True)
    phone_number = serializers.CharField(allow_null=True)
    role = serializers.CharField()


class _PlaceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class MessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = ["id", "author_name", "author_role", "is_staff_reply", "is_mine", "body", "created_at"]
        read_only_fields = fields

    def get_author_name(self, obj) -> str:
        # Authors see "the support team", not which admin answered; staff see the name.
        if obj.is_staff_reply and not self.context.get("staff_view"):
            return STAFF_LABEL
        return obj.author.full_name or "—"

    def get_is_mine(self, obj) -> bool:
        return obj.author_id == self.context["request"].user.pk


class TicketSerializer(serializers.ModelSerializer):
    """List row: who wrote, from which studio / venue, who handled it."""

    author = _PersonSerializer(read_only=True)
    studio = _PlaceSerializer(read_only=True, allow_null=True)
    venue = _PlaceSerializer(read_only=True, allow_null=True)
    handled_by_name = serializers.SerializerMethodField()
    closed_by_name = serializers.SerializerMethodField()
    message_count = serializers.IntegerField(read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "subject",
            "status",
            "audience",
            "author",
            "author_role",
            "studio",
            "venue",
            "handled_by_name",
            "closed_by_name",
            "message_count",
            "last_message",
            "last_message_at",
            "closed_at",
            "created_at",
        ]
        read_only_fields = fields

    def _staff_name(self, user) -> str | None:
        if user is None:
            return None
        return (user.full_name or "—") if self.context.get("staff_view") else STAFF_LABEL

    def get_handled_by_name(self, obj) -> str | None:
        return self._staff_name(obj.handled_by)

    def get_closed_by_name(self, obj) -> str | None:
        if obj.closed_by_id == obj.author_id:
            return obj.author.full_name or "—"
        return self._staff_name(obj.closed_by)

    def get_last_message(self, obj) -> str:
        last = getattr(obj, "last_body", None)
        return (last or "")[:160]


class TicketDetailSerializer(TicketSerializer):
    messages = serializers.SerializerMethodField()
    can_reply = serializers.SerializerMethodField()

    class Meta(TicketSerializer.Meta):
        fields = [*TicketSerializer.Meta.fields, "messages", "can_reply"]
        read_only_fields = fields

    @extend_schema_field(MessageSerializer(many=True))
    def get_messages(self, obj):
        rows = obj.messages.select_related("author")
        return MessageSerializer(rows, many=True, context=self.context).data

    def get_can_reply(self, obj) -> bool:
        from .services import can_answer

        user = self.context["request"].user
        if not self.context.get("staff_view"):
            return obj.author_id == user.pk
        return can_answer(user, obj) and obj.status != "CLOSED"


class SupportSummarySerializer(serializers.Serializer):
    open = serializers.IntegerField(help_text="Javob kutayotgan xatlar (sizga ko'rinadiganlar).")
    answered = serializers.IntegerField()
    closed = serializers.IntegerField()
