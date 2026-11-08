"use client";

import { CalendarCheck2Icon, PhoneIcon, XIcon } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { PageTitle } from "@/components/shell";
import { Badge, Button, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatEventDate, formatMoney, formatPhone } from "@/lib/format";
import { BOOKING_STATUS, EVENT_TYPE_LABELS, hhmm, type MyBooking, todayIso, useCancelBooking, useMyBookings } from "@/lib/venues";

export default function MyBookingsPage() {
  const bookings = useMyBookings();
  const today = todayIso();

  return (
    <>
      <PageTitle
        title="Bronlarim"
        subtitle="To'yxonalarga yuborgan so'rovlaringiz va tasdiqlangan bronlar"
        actions={
          <Link href="/toyxonalar" className="inline-flex h-10 items-center rounded-xl px-4 text-sm font-semibold brand-gradient text-white">
            Bo&apos;sh joy qidirish
          </Link>
        }
      />
      {bookings.isPending ? (
        <Skeleton className="h-40 rounded-3xl" />
      ) : bookings.error ? (
        <Card>
          <ErrorState error={bookings.error} onRetry={() => bookings.refetch()} />
        </Card>
      ) : bookings.data.length === 0 ? (
        <Card>
          <EmptyState
            title="Hali bron yo'q"
            description="To'yxonalar bo'limida sanangizni tanlang va bo'sh smenaga so'rov yuboring."
          />
        </Card>
      ) : (
        <ul className="flex flex-col gap-3">
          {bookings.data.map((b) => (
            <BookingRow key={b.id} booking={b} upcoming={b.date >= today} />
          ))}
        </ul>
      )}
    </>
  );
}

function BookingRow({ booking: b, upcoming }: { booking: MyBooking; upcoming: boolean }) {
  const cancel = useCancelBooking();
  const status = BOOKING_STATUS[b.status];
  const cancellable = upcoming && (b.status === "REQUESTED" || b.status === "CONFIRMED");
  const onCancel = () => {
    const question =
      b.status === "CONFIRMED" ? "Tasdiqlangan bronni bekor qilasizmi? Smena boshqalarga bo'shaydi." : "So'rovni bekor qilasizmi?";
    if (!window.confirm(question)) return;
    cancel.mutate(b.id, {
      onSuccess: () => toast.success("Bekor qilindi"),
      onError: (e) => toast.error(e instanceof ApiError ? e.message : "Bekor qilinmadi"),
    });
  };
  return (
    <li className="glass flex flex-wrap items-center gap-4 rounded-3xl p-5">
      <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl brand-gradient text-white">
        <CalendarCheck2Icon className="size-5" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Link href={`/toyxonalar/${b.venue.id}?date=${b.date}`} className="text-base font-bold hover:underline">
            {b.venue.name}
          </Link>
          <Badge tone={status.tone}>{status.label}</Badge>
        </div>
        <p className="text-sm">
          <b>{formatEventDate(b.date)}</b> · {b.session.name} {hhmm(b.session.starts_at)}–{hhmm(b.session.ends_at)} · {b.hall.name}
        </p>
        <p className="text-sm text-muted-foreground">
          {EVENT_TYPE_LABELS[b.event_type]}
          {b.guest_count ? ` · ${b.guest_count} mehmon` : ""}
          {b.quoted_price ? ` · ${formatMoney(b.quoted_price)} dan` : ""}
        </p>
        {status.hint && <p className="mt-1 text-xs text-muted-foreground">{status.hint}</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        {b.venue.phone_number && (
          <a href={`tel:${b.venue.phone_number}`} className="glass inline-flex h-9 items-center gap-1.5 rounded-xl px-3 text-[13px] font-semibold">
            <PhoneIcon className="size-4" aria-hidden /> {formatPhone(b.venue.phone_number)}
          </a>
        )}
        {cancellable && (
          <Button size="sm" variant="danger" onClick={onCancel} loading={cancel.isPending}>
            <XIcon /> Bekor qilish
          </Button>
        )}
      </div>
    </li>
  );
}
