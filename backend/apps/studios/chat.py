"""Customer ↔ studio chat.

A customer (USER) opens a conversation from the studio's public profile; any active member of the
studio reads it, OWNER / MANAGER answer. Writing on either side needs the studio's galichka —
without it the history stays readable but frozen. Customers see the studio, never its staff;
studios see the customer's name (no phone number, no PINFL).
"""

from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone

from .models import Studio, StudioChatMessage, StudioConversation
from .services import require_badge

#: Messages returned per conversation page (newest last).
PAGE_SIZE = 200


def user_conversations(user):
    return (
        StudioConversation.objects.filter(user=user, studio__deleted_at__isnull=True)
        .select_related("studio")
        .annotate(
            unread=Count(
                "messages",
                filter=Q(messages__from_studio=True)
                & (Q(user_read_at__isnull=True) | Q(messages__created_at__gt=F("user_read_at"))),
            )
        )
    )


def studio_conversations(studio: Studio):
    return (
        StudioConversation.objects.filter(studio=studio)
        .select_related("user")
        .annotate(
            unread=Count(
                "messages",
                filter=Q(messages__from_studio=False)
                & (Q(studio_read_at__isnull=True) | Q(messages__created_at__gt=F("studio_read_at"))),
            )
        )
    )


def last_messages(conversations) -> dict:
    """``{conversation_id: last message}`` for a list of conversations."""
    ids = [c.pk for c in conversations]
    out = {}
    for message in StudioChatMessage.objects.filter(conversation_id__in=ids).order_by("conversation_id", "-created_at"):
        out.setdefault(message.conversation_id, message)
    return out


def messages(conversation: StudioConversation):
    qs = conversation.messages.order_by("-created_at")[:PAGE_SIZE]
    return list(reversed(qs))


def mark_read(conversation: StudioConversation, *, by_studio: bool) -> None:
    field = "studio_read_at" if by_studio else "user_read_at"
    StudioConversation.objects.filter(pk=conversation.pk).update(**{field: timezone.now()})


@transaction.atomic
def send_from_user(user, studio: Studio, body: str) -> StudioChatMessage:
    require_badge(studio)
    now = timezone.now()
    conversation, _ = StudioConversation.objects.get_or_create(
        studio=studio, user=user, defaults={"last_message_at": now}
    )
    return _append(conversation, user, body, from_studio=False, now=now)


@transaction.atomic
def send_from_studio(member, conversation: StudioConversation, body: str) -> StudioChatMessage:
    require_badge(conversation.studio)
    return _append(conversation, member, body, from_studio=True, now=timezone.now())


def _append(conversation, author, body: str, *, from_studio: bool, now) -> StudioChatMessage:
    message = StudioChatMessage.objects.create(
        conversation=conversation, author=author, from_studio=from_studio, body=body.strip()
    )
    read_field = "studio_read_at" if from_studio else "user_read_at"
    StudioConversation.objects.filter(pk=conversation.pk).update(last_message_at=now, **{read_field: now})
    return message
