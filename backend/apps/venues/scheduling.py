"""Hall sessions, availability and bookings — every write path and rule lives here.

Model (user decision 2026-11-08): a hall's day is split into fixed sessions; a booking takes one
session on one date. A slot is *free* when no CONFIRMED / BLOCKED booking holds it.

Double-booking guard, two layers:
1. Every state change that may occupy a slot locks the hall row (``SELECT … FOR UPDATE`` on
   PostgreSQL) and re-checks the slot inside the transaction.
2. The partial unique index ``venues_booking_one_per_slot`` rejects a second occupying booking even
   if layer 1 were bypassed; the IntegrityError becomes ``409 Conflict``.

Public side sees only venues that are ``is_active`` and ``publication_status=APPROVED`` and halls /
sessions that are active — and only *whether* a slot is free, never who holds it.
"""

import datetime

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.audit.services import AuditAction, record

from .models import (
    DEFAULT_SESSIONS,
    OCCUPYING_STATUSES,
    OPEN_STATUSES,
    BookingSource,
    BookingStatus,
    HallBooking,
    HallSession,
    PublicationStatus,
    Venue,
    VenueHall,
)

#: How far ahead a slot may be requested / shown.
MAX_DAYS_AHEAD = 730
#: Widest calendar window one request may load (a month view plus overflow weeks).
MAX_RANGE_DAYS = 62
#: Open (REQUESTED) requests one couple may have at a time — anti-spam.
MAX_OPEN_REQUESTS_PER_USER = 10

BOOKING_AUDITED_FIELDS = ["hall", "session", "date", "status", "source", "event_type", "guest_count"]


class SlotTaken(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Bu smena shu kunga allaqachon band."
    default_code = "slot_taken"


def today() -> datetime.date:
    return timezone.localdate()  # TIME_ZONE = Asia/Tashkent


# ----------------------------------------------------------------- sessions
def create_default_sessions(hall: VenueHall) -> None:
    HallSession.objects.bulk_create(
        HallSession(
            hall=hall,
            name=name,
            starts_at=datetime.time.fromisoformat(start),
            ends_at=datetime.time.fromisoformat(end),
        )
        for name, start, end in DEFAULT_SESSIONS
    )


def validate_session_window(hall: VenueHall, starts_at, ends_at, exclude_pk=None) -> None:
    """Sessions of one hall must not overlap (otherwise one evening could be sold twice)."""
    if ends_at <= starts_at:
        raise ValidationError({"ends_at": ["Tugash vaqti boshlanishidan keyin bo'lishi kerak."]})
    clash = HallSession.objects.filter(hall=hall, is_active=True, starts_at__lt=ends_at, ends_at__gt=starts_at)
    if exclude_pk is not None:
        clash = clash.exclude(pk=exclude_pk)
    other = clash.first()
    if other is not None:
        raise ValidationError(
            {
                "starts_at": [
                    f'"{other.name}" smenasi bilan vaqt kesishadi ({other.starts_at:%H:%M}–{other.ends_at:%H:%M}).'
                ]
            }
        )


# ------------------------------------------------------------------- ranges
def parse_date(value, field: str = "date") -> datetime.date:
    try:
        return datetime.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise ValidationError({field: ["Sana YYYY-MM-DD formatida bo'lishi kerak."]}) from None


def parse_range(params) -> tuple[datetime.date, datetime.date]:
    start = parse_date(params.get("from"), "from")
    end = parse_date(params.get("to"), "to")
    if end < start:
        raise ValidationError({"to": ["'to' sanasi 'from' dan oldin bo'lmasligi kerak."]})
    if (end - start).days >= MAX_RANGE_DAYS:
        raise ValidationError({"to": [f"Oraliq {MAX_RANGE_DAYS} kundan oshmasligi kerak."]})
    return start, end


# ------------------------------------------------------------------- public
def public_venues():
    return Venue.objects.filter(deleted_at__isnull=True, is_active=True, publication_status=PublicationStatus.APPROVED)


def public_halls(venue: Venue):
    return venue.halls.filter(deleted_at__isnull=True, is_active=True)


def taken_slots(hall_ids, start: datetime.date, end: datetime.date) -> set[tuple]:
    """``{(session_id, date)}`` held by an occupying booking in ``[start, end]``."""
    rows = HallBooking.objects.filter(
        hall_id__in=hall_ids, date__gte=start, date__lte=end, status__in=OCCUPYING_STATUSES
    ).values_list("session_id", "date")
    return set(rows)


def search(date: datetime.date, *, region: str = "", guests: int | None = None, q: str = ""):
    """Public venues with at least one free session on ``date``, each hall annotated with its sessions.

    Returns a list of ``(venue, [(hall, [(session, is_free)])])``; venues without a free slot are dropped.
    """
    venues = public_venues().prefetch_related("images")
    if region:
        venues = venues.filter(region=region)
    if q:
        venues = venues.filter(Q(name__icontains=q) | Q(address__icontains=q) | Q(district__icontains=q))
    halls = VenueHall.objects.filter(venue__in=venues, deleted_at__isnull=True, is_active=True)
    if guests:
        halls = halls.filter(capacity__gte=guests)
    halls = list(halls.select_related("venue").order_by("created_at"))
    sessions = HallSession.objects.filter(hall__in=halls, is_active=True).order_by("starts_at")
    by_hall: dict = {}
    for s in sessions:
        by_hall.setdefault(s.hall_id, []).append(s)
    taken = taken_slots([h.pk for h in halls], date, date)

    result: dict = {}
    for hall in halls:
        slots = [(s, (s.pk, date) not in taken) for s in by_hall.get(hall.pk, [])]
        if any(free for _, free in slots):
            result.setdefault(hall.venue_id, (hall.venue, []))[1].append((hall, slots))
    return sorted(result.values(), key=lambda pair: (pair[0].base_price, pair[0].name))


def venue_availability(venue: Venue, start: datetime.date, end: datetime.date) -> dict:
    """``{hall_id: {iso_date: [free session ids]}}`` for a public calendar."""
    halls = list(public_halls(venue))
    sessions = list(HallSession.objects.filter(hall__in=halls, is_active=True).order_by("starts_at"))
    taken = taken_slots([h.pk for h in halls], start, end)
    out: dict = {str(h.pk): {} for h in halls}
    day = start
    while day <= end:
        for s in sessions:
            if day >= today() and (s.pk, day) not in taken:
                out[str(s.hall_id)].setdefault(day.isoformat(), []).append(str(s.pk))
        day += datetime.timedelta(days=1)
    return out


# ------------------------------------------------------------------ writes
def _lock_hall(hall: VenueHall) -> VenueHall:
    return VenueHall.objects.select_for_update().get(pk=hall.pk)


def _slot_is_taken(session: HallSession, date: datetime.date, exclude_pk=None) -> bool:
    qs = HallBooking.objects.filter(session=session, date=date, status__in=OCCUPYING_STATUSES)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def _check_date(date: datetime.date, *, allow_past: bool = False) -> None:
    if not allow_past and date < today():
        raise ValidationError({"date": ["O'tgan sana uchun bron qilib bo'lmaydi."]})
    if date > today() + datetime.timedelta(days=MAX_DAYS_AHEAD):
        raise ValidationError({"date": ["Sana juda uzoq (ko'pi bilan 2 yil oldindan)."]})


def _save_occupying(booking: HallBooking) -> HallBooking:
    """Save inside a savepoint so a lost race surfaces as 409 and the outer transaction survives."""
    try:
        with transaction.atomic():
            booking.save()
    except IntegrityError:
        raise SlotTaken() from None
    return booking


def _reject_competing_requests(request, booking: HallBooking) -> None:
    rivals = HallBooking.objects.filter(
        session=booking.session, date=booking.date, status=BookingStatus.REQUESTED
    ).exclude(pk=booking.pk)
    now = timezone.now()
    for rival in rivals:
        rival.status, rival.decided_at = BookingStatus.REJECTED, now
        rival.decided_by = getattr(request, "user", None) if request else None
        rival.venue_note = rival.venue_note or "Bu smena boshqa mijozga tasdiqlandi."
        rival.save(update_fields=["status", "decided_at", "decided_by", "venue_note", "updated_at"])
        record(request, AuditAction.UPDATE, rival, changes={"status": ["REQUESTED", "REJECTED"], "auto": True})


@transaction.atomic
def request_booking(request, user, session: HallSession, date: datetime.date, **details) -> HallBooking:
    """A couple asks for a slot (status REQUESTED). The slot must be free and the venue public."""
    hall = session.hall
    venue = hall.venue
    public = public_venues().filter(pk=venue.pk).exists()
    if not (public and hall.is_active and hall.deleted_at is None and session.is_active):
        raise ValidationError({"session": ["Bu smena hozir bron uchun ochiq emas."]})
    _check_date(date)
    guests = details.get("guest_count")
    if guests and guests > hall.capacity:
        raise ValidationError({"guest_count": [f"Bu zal ko'pi bilan {hall.capacity} kishiga mo'ljallangan."]})
    _lock_hall(hall)
    if _slot_is_taken(session, date):
        raise SlotTaken()
    if HallBooking.objects.filter(session=session, date=date, requester=user, status=BookingStatus.REQUESTED).exists():
        raise ValidationError({"session": ["Siz bu smenaga allaqachon so'rov yuborgansiz."]})
    open_count = HallBooking.objects.filter(requester=user, status=BookingStatus.REQUESTED, date__gte=today()).count()
    if open_count >= MAX_OPEN_REQUESTS_PER_USER:
        raise ValidationError({"session": [f"Bir vaqtda ko'pi bilan {MAX_OPEN_REQUESTS_PER_USER} ta ochiq so'rov."]})
    booking = HallBooking.objects.create(
        hall=hall,
        session=session,
        date=date,
        status=BookingStatus.REQUESTED,
        source=BookingSource.USER,
        requester=user,
        contact_name=details.get("contact_name") or user.full_name,
        contact_phone=details.get("contact_phone") or user.phone_number or "",
        event_type=details.get("event_type") or HallBooking._meta.get_field("event_type").default,
        guest_count=guests,
        note=details.get("note", ""),
        quoted_price=hall.effective_base_price,
    )
    record(request, AuditAction.CREATE, booking, changes={"session": str(session.pk), "date": date.isoformat()})
    return booking


@transaction.atomic
def venue_create_entry(request, session: HallSession, date: datetime.date, *, status: str, **details) -> HallBooking:
    """The venue writes its own event (CONFIRMED) or closes a slot (BLOCKED)."""
    if status not in OCCUPYING_STATUSES:
        raise ValidationError({"status": ["Faqat CONFIRMED yoki BLOCKED."]})
    if not session.is_active:
        raise ValidationError({"session": ["Smena nofaol."]})
    _check_date(date, allow_past=True)
    _lock_hall(session.hall)
    if _slot_is_taken(session, date):
        raise SlotTaken()
    booking = HallBooking(
        hall=session.hall,
        session=session,
        date=date,
        status=status,
        source=BookingSource.VENUE,
        event_type=details.get("event_type") or HallBooking._meta.get_field("event_type").default,
        guest_count=details.get("guest_count"),
        contact_name=details.get("contact_name", ""),
        contact_phone=details.get("contact_phone", ""),
        venue_note=details.get("venue_note", ""),
        quoted_price=session.hall.effective_base_price if status == BookingStatus.CONFIRMED else None,
        decided_by=getattr(request, "user", None),
        decided_at=timezone.now(),
    )
    _save_occupying(booking)
    if status == BookingStatus.CONFIRMED:
        _reject_competing_requests(request, booking)
    record(
        request,
        AuditAction.CREATE,
        booking,
        changes={"session": str(session.pk), "date": date.isoformat(), "status": status},
    )
    return booking


@transaction.atomic
def confirm(request, booking: HallBooking) -> HallBooking:
    _lock_hall(booking.hall)
    booking.refresh_from_db()
    if booking.status != BookingStatus.REQUESTED:
        raise ValidationError({"status": ["Faqat kutilayotgan so'rovni tasdiqlash mumkin."]})
    if _slot_is_taken(booking.session, booking.date):
        raise SlotTaken()
    booking.status, booking.decided_by, booking.decided_at = BookingStatus.CONFIRMED, request.user, timezone.now()
    _save_occupying(booking)
    _reject_competing_requests(request, booking)
    record(request, AuditAction.UPDATE, booking, changes={"status": ["REQUESTED", "CONFIRMED"]})
    return booking


@transaction.atomic
def reject(request, booking: HallBooking, venue_note: str = "") -> HallBooking:
    booking = HallBooking.objects.select_for_update().get(pk=booking.pk)
    if booking.status != BookingStatus.REQUESTED:
        raise ValidationError({"status": ["Faqat kutilayotgan so'rovni rad etish mumkin."]})
    booking.status, booking.decided_by, booking.decided_at = BookingStatus.REJECTED, request.user, timezone.now()
    if venue_note:
        booking.venue_note = venue_note
    booking.save(update_fields=["status", "decided_by", "decided_at", "venue_note", "updated_at"])
    record(request, AuditAction.UPDATE, booking, changes={"status": ["REQUESTED", "REJECTED"]})
    return booking


@transaction.atomic
def cancel(request, booking: HallBooking, *, by_requester: bool) -> HallBooking:
    """Free the slot. The couple may cancel their own open request / booking; the venue any open entry."""
    booking = HallBooking.objects.select_for_update().get(pk=booking.pk)
    if booking.status not in OPEN_STATUSES:
        raise ValidationError({"status": ["Bu yozuv allaqachon yopilgan."]})
    if by_requester and booking.date < today():
        raise ValidationError({"status": ["O'tgan marosimni bekor qilib bo'lmaydi."]})
    before = booking.status
    booking.status, booking.decided_at = BookingStatus.CANCELLED, timezone.now()
    if not by_requester:
        booking.decided_by = request.user
    booking.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])
    record(
        request, AuditAction.UPDATE, booking, changes={"status": [before, "CANCELLED"], "by_requester": by_requester}
    )
    return booking


def owner_bookings(venue: Venue):
    return HallBooking.objects.filter(hall__venue=venue).select_related("hall", "session", "requester")


def my_bookings(user):
    return HallBooking.objects.filter(requester=user).select_related("hall__venue", "session")
