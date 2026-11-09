"""Who sees and answers which help ticket (see ``models`` for the routing rules)."""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Role
from apps.core.exceptions import Conflict

from .models import SupportMessage, SupportTicket, TicketAudience, TicketStatus

AUTHOR_ROLES = (Role.USER, Role.STUDIO, Role.VENUE_OWNER, Role.ADMIN)


def _studio_of(user):
    from apps.studios.models import StudioMembership

    row = (
        StudioMembership.objects.filter(user=user, is_active=True, studio__deleted_at__isnull=True)
        .order_by("created_at")
        .first()
    )
    return row.studio_id if row else None


def _venue_of(user):
    from apps.venues.models import VenueMembership

    row = VenueMembership.objects.filter(user=user, is_active=True).order_by("created_at").first()
    return row.venue_id if row else None


# --------------------------------------------------------------- scopes
def staff_tickets(user):
    """Tickets a staff member may read in the queue."""
    qs = SupportTicket.objects.all()
    if user.role == Role.SUPER_ADMIN or user.has_admin_permission("support.monitor"):
        return qs
    return qs.filter(audience=TicketAudience.STAFF)


def can_answer(user, ticket: SupportTicket) -> bool:
    if ticket.author_id == user.pk:
        return False
    if user.role == Role.SUPER_ADMIN:
        return True
    return (
        user.role == Role.ADMIN
        and ticket.audience == TicketAudience.STAFF
        and user.has_admin_permission("support.view")
    )


# --------------------------------------------------------------- author
def open_ticket(request, subject: str, body: str) -> SupportTicket:
    user = request.user
    if user.role not in AUTHOR_ROLES:
        raise PermissionDenied("Super Admin yordam xati yubormaydi.")
    now = timezone.now()
    with transaction.atomic():
        ticket = SupportTicket.objects.create(
            author=user,
            author_role=user.role,
            audience=TicketAudience.SUPER_ADMIN if user.role == Role.ADMIN else TicketAudience.STAFF,
            studio_id=_studio_of(user) if user.role == Role.STUDIO else None,
            venue_id=_venue_of(user) if user.role == Role.VENUE_OWNER else None,
            subject=subject.strip(),
            last_message_at=now,
        )
        SupportMessage.objects.create(ticket=ticket, author=user, author_role=user.role, body=body.strip())
    return ticket


def author_reply(request, ticket: SupportTicket, body: str) -> SupportMessage:
    """The author adds details; a closed ticket is reopened."""
    now = timezone.now()
    with transaction.atomic():
        msg = SupportMessage.objects.create(
            ticket=ticket, author=request.user, author_role=request.user.role, body=body.strip()
        )
        SupportTicket.objects.filter(pk=ticket.pk).update(
            status=TicketStatus.OPEN, last_message_at=now, closed_at=None, closed_by=None, updated_at=now
        )
    return msg


# --------------------------------------------------------------- staff
def staff_reply(request, ticket: SupportTicket, body: str) -> SupportMessage:
    user = request.user
    if not can_answer(user, ticket):
        raise PermissionDenied(
            "Adminlarning xatlariga faqat Super Admin javob beradi."
            if ticket.audience == TicketAudience.SUPER_ADMIN
            else "Bu xatga javob berish huquqingiz yo'q."
        )
    if ticket.status == TicketStatus.CLOSED:
        raise Conflict("Xat yopilgan. Muallif yangi xabar yozsa, u qayta ochiladi.")
    now = timezone.now()
    with transaction.atomic():
        msg = SupportMessage.objects.create(
            ticket=ticket, author=user, author_role=user.role, is_staff_reply=True, body=body.strip()
        )
        SupportTicket.objects.filter(pk=ticket.pk).update(status=TicketStatus.ANSWERED, last_message_at=now, updated_at=now)
        SupportTicket.objects.filter(pk=ticket.pk, handled_by__isnull=True).update(handled_by=user)
    return msg


def close(request, ticket: SupportTicket) -> SupportTicket:
    user = request.user
    if ticket.author_id != user.pk and not can_answer(user, ticket):
        raise PermissionDenied("Bu xatni yopish huquqingiz yo'q.")
    if ticket.status == TicketStatus.CLOSED:
        raise Conflict("Xat allaqachon yopilgan.")
    now = timezone.now()
    SupportTicket.objects.filter(pk=ticket.pk).update(
        status=TicketStatus.CLOSED, closed_at=now, closed_by=user, updated_at=now
    )
    ticket.refresh_from_db()
    return ticket
