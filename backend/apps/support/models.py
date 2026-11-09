"""Help requests ("Yordam") sent from every panel.

Routing (user decision 2026-11-09): one shared queue.

* USER / STUDIO / VENUE_OWNER tickets go to the staff queue: every ADMIN with ``support.view`` (and the
  SUPER_ADMIN) sees and answers them.
* ADMIN tickets go to the SUPER_ADMIN only. An ADMIN with ``support.monitor`` may *read* them (and the
  whole history: who wrote, from which studio / venue, who answered) but never answer them.

The studio / venue the author belonged to is captured when the ticket is opened, so the history
stays readable after memberships change.
"""

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class TicketStatus(models.TextChoices):
    OPEN = "OPEN", "Javob kutilmoqda"
    ANSWERED = "ANSWERED", "Javob berildi"
    CLOSED = "CLOSED", "Yopilgan"


class TicketAudience(models.TextChoices):
    #: From USER / STUDIO / VENUE_OWNER: answered by admins with ``support.view``.
    STAFF = "STAFF", "Adminlarga"
    #: From an ADMIN: answered by the Super Admin only.
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin'ga"


class SupportTicket(BaseModel):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="support_tickets")
    #: Author's role when the ticket was opened.
    author_role = models.CharField(max_length=20)
    audience = models.CharField(max_length=12, choices=TicketAudience.choices)
    studio = models.ForeignKey(
        "studios.Studio", null=True, blank=True, on_delete=models.SET_NULL, related_name="support_tickets"
    )
    venue = models.ForeignKey(
        "venues.Venue", null=True, blank=True, on_delete=models.SET_NULL, related_name="support_tickets"
    )
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=TicketStatus.choices, default=TicketStatus.OPEN)
    #: First staff member who answered (for the Super Admin's overview).
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    last_message_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-last_message_at"]
        indexes = [
            models.Index(fields=["audience", "status", "last_message_at"]),
            models.Index(fields=["author", "last_message_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.subject} ({self.status})"


class SupportMessage(BaseModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    author_role = models.CharField(max_length=20)
    #: Written by staff (ADMIN / SUPER_ADMIN) answering the ticket, not by its author.
    is_staff_reply = models.BooleanField(default=False)
    body = models.TextField(max_length=5000)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"message {self.pk} on {self.ticket_id}"


class ApplicationKind(models.TextChoices):
    STUDIO = "STUDIO", "Video studiya"
    VENUE = "VENUE", "To'yxona"


class ApplicationStatus(models.TextChoices):
    NEW = "NEW", "Yangi"
    IN_REVIEW = "IN_REVIEW", "Ko'rib chiqilmoqda"
    APPROVED = "APPROVED", "Qabul qilindi"
    REJECTED = "REJECTED", "Rad etildi"


class PartnerApplication(BaseModel):
    """A studio or venue that wants to join, sent from the marosimgo.uz landing page (no account yet).

    Staff with ``support.view`` see them on the "Yordam" page, call back and create the account by hand.
    """

    kind = models.CharField(max_length=10, choices=ApplicationKind.choices)
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    business_name = models.CharField(max_length=200)
    region = models.CharField(max_length=20, blank=True)
    message = models.TextField(max_length=2000, blank=True)
    status = models.CharField(max_length=12, choices=ApplicationStatus.choices, default=ApplicationStatus.NEW)
    staff_note = models.CharField(max_length=1000, blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    handled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.kind} {self.business_name} ({self.status})"
