"use client";

import { CalendarCheck2Icon, ClockIcon, MapPinIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { formatEventDate, formatMoney } from "@/lib/format";
import { type BookingEventType, EVENT_TYPE_LABELS, hhmm, type SessionBrief, useRequestBooking } from "@/lib/venues";

import { Button, Field, Input, Modal, Select, Textarea } from "./ui";

export interface BookingTarget {
  venueName: string;
  address: string;
  hallName: string;
  capacity: number;
  price: string;
  session: SessionBrief;
  date: string;
}

/** "So'rov yuborish" dialog: the slot is only taken once the venue confirms. */
export function BookingModal({ target, onClose }: { target: BookingTarget | null; onClose: () => void }) {
  return (
    <Modal open={Boolean(target)} onClose={onClose} title="Bron so'rovi">
      {target && <BookingForm key={`${target.session.id}-${target.date}`} target={target} onDone={onClose} />}
    </Modal>
  );
}

function BookingForm({ target, onDone }: { target: BookingTarget; onDone: () => void }) {
  const request = useRequestBooking();
  const [eventType, setEventType] = useState<BookingEventType>("WEDDING");
  const [guests, setGuests] = useState("");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [sent, setSent] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    request.mutate(
      {
        session: target.session.id,
        date: target.date,
        event_type: eventType,
        guest_count: guests ? Number(guests) : null,
        note: note.trim(),
      },
      {
        onSuccess: () => {
          setSent(true);
          toast.success("So'rov yuborildi");
        },
        onError: (err) => {
          if (err instanceof ApiError) {
            setErrors(err.fieldErrors);
            toast.error(err.status === 409 ? "Afsus, bu smena hozirgina band bo'ldi." : err.message);
          } else toast.error("So'rov yuborilmadi");
        },
      },
    );
  };

  const summary = (
    <div className="flex flex-col gap-2 rounded-2xl border border-cyan-400/30 bg-cyan-500/[0.07] p-4 text-sm">
      <p className="text-base font-bold">
        {target.venueName} · {target.hallName}
      </p>
      <p className="flex items-center gap-1.5 text-muted-foreground">
        <MapPinIcon className="size-4" aria-hidden /> {target.address}
      </p>
      <p className="flex items-center gap-1.5">
        <CalendarCheck2Icon className="size-4 text-brand" aria-hidden />
        <b>{formatEventDate(target.date)}</b>
      </p>
      <p className="flex items-center gap-1.5">
        <ClockIcon className="size-4 text-brand" aria-hidden />
        <b>{target.session.name}</b> {hhmm(target.session.starts_at)}–{hhmm(target.session.ends_at)}
      </p>
      <p className="text-muted-foreground">
        Narx: <b className="text-foreground">{formatMoney(target.price)}</b> dan · sig&apos;im {target.capacity} kishi
      </p>
    </div>
  );

  if (sent) {
    return (
      <div className="flex flex-col gap-4">
        {summary}
        <p className="text-sm">
          So&apos;rovingiz to&apos;yxonaga yuborildi. To&apos;yxona tasdiqlagach smena siz uchun band bo&apos;ladi — holatini
          &quot;Bronlarim&quot; bo&apos;limida kuzating.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onDone}>
            Yopish
          </Button>
          <Link href="/bronlarim" className="inline-flex h-10 items-center rounded-xl px-4 text-sm font-semibold brand-gradient text-white">
            Bronlarim
          </Link>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      {summary}
      <Field label="Marosim turi" htmlFor="b-type" error={errors.event_type}>
        <Select id="b-type" value={eventType} onChange={(e) => setEventType(e.target.value as BookingEventType)}>
          {Object.entries(EVENT_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Mehmonlar soni (taxminan)" htmlFor="b-guests" error={errors.guest_count} hint={`Ko'pi bilan ${target.capacity} kishi`}>
        <Input
          id="b-guests"
          type="number"
          inputMode="numeric"
          min={1}
          max={target.capacity}
          value={guests}
          onChange={(e) => setGuests(e.target.value)}
          placeholder="300"
        />
      </Field>
      <Field label="Izoh (ixtiyoriy)" htmlFor="b-note" error={errors.note}>
        <Textarea id="b-note" maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Masalan: menyu bo'yicha qo'ng'iroq qiling" />
      </Field>
      {(errors.session || errors.date) && (
        <p role="alert" className="text-sm font-medium text-danger">
          {errors.session || errors.date}
        </p>
      )}
      <p className="text-xs text-muted-foreground">
        So&apos;rov smenani darhol band qilmaydi. To&apos;yxona siz bilan telefon orqali bog&apos;lanib, tasdiqlaydi.
      </p>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>
          Bekor qilish
        </Button>
        <Button type="submit" loading={request.isPending}>
          So&apos;rov yuborish
        </Button>
      </div>
    </form>
  );
}
