"use client";

import {
  BanIcon,
  BellRingIcon,
  CalendarDaysIcon,
  CheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ClockIcon,
  ListIcon,
  LockOpenIcon,
  PencilIcon,
  PhoneIcon,
  PlusIcon,
  Settings2Icon,
  UserIcon,
  UsersIcon,
  XIcon,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { formatEventDate, formatPhone } from "@/lib/format";
import {
  type Booking,
  type BookingEventType,
  type CalendarHall,
  EVENT_SHORT,
  EVENT_TYPE_LABELS,
  hhmm,
  type HallSession,
  isoDate,
  SLOT_TONE,
  useCalendar,
  useCreateEntry,
  useCreateSession,
  useDecide,
  usePendingRequests,
  useUpdateEntry,
  useUpdateSession,
} from "@/lib/schedule";
import type { Venue } from "@/lib/types";
import { can } from "@/lib/venues";

import { PhoneInput } from "./phone-input";
import { Badge, Button, Card, cn, EmptyState, ErrorState, Field, Input, Modal, Select, Skeleton, Textarea } from "./ui";

const WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];
const MONTHS = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"];

const apiMessage = (e: unknown, fallback: string) =>
  e instanceof ApiError ? (e.status === 409 ? "Bu smena allaqachon band." : e.message) : fallback;

/** Monday-first 6×7 (or 5×7) grid around the month. */
function monthGrid(y: number, m: number) {
  const first = new Date(y, m, 1);
  const start = new Date(y, m, 1 - ((first.getDay() + 6) % 7));
  const last = new Date(y, m + 1, 0);
  const end = new Date(y, m + 1, (7 - ((last.getDay() + 6) % 7) - 1) % 7);
  const days: Date[] = [];
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) days.push(new Date(d));
  return { days, from: isoDate(start), to: isoDate(end) };
}

type SlotState =
  | { kind: "FREE" }
  | { kind: "CONFIRMED" | "BLOCKED"; entry: Booking; requests: Booking[] }
  | { kind: "REQUESTED"; requests: Booking[] };

/** Index bookings by "sessionId|date" so cells and the day panel read the same state. */
function indexBookings(bookings: Booking[]) {
  const map = new Map<string, { entry?: Booking; requests: Booking[] }>();
  for (const b of bookings) {
    const key = `${b.session.id}|${b.date}`;
    const slot = map.get(key) ?? { requests: [] };
    if (b.status === "REQUESTED") slot.requests.push(b);
    else slot.entry = b;
    map.set(key, slot);
  }
  return (sessionId: string, date: string): SlotState => {
    const slot = map.get(`${sessionId}|${date}`);
    if (!slot) return { kind: "FREE" };
    if (slot.entry) return { kind: slot.entry.status as "CONFIRMED" | "BLOCKED", entry: slot.entry, requests: slot.requests };
    return { kind: "REQUESTED", requests: slot.requests };
  };
}

// =================================================================== tab
export function ScheduleTab({ venue }: { venue: Venue }) {
  const today = isoDate(new Date());
  const [cursor, setCursor] = useState(() => ({ y: new Date().getFullYear(), m: new Date().getMonth() }));
  const [view, setView] = useState<"month" | "list">("month");
  const [hallId, setHallId] = useState<string | null>(null);
  const [selected, setSelected] = useState(today);
  const [sessionsOpen, setSessionsOpen] = useState(false);
  const grid = useMemo(() => monthGrid(cursor.y, cursor.m), [cursor]);
  const calendar = useCalendar(venue.id, grid.from, grid.to);

  const shift = (d: number) =>
    setCursor(({ y, m }) => {
      const n = new Date(y, m + d, 1);
      return { y: n.getFullYear(), m: n.getMonth() };
    });
  const goToday = () => {
    setCursor({ y: new Date().getFullYear(), m: new Date().getMonth() });
    setSelected(today);
  };

  const halls = (calendar.data?.halls ?? []).filter((h) => h.is_active);
  const hall = halls.find((h) => h.id === hallId) ?? halls[0];
  const slotOf = useMemo(() => indexBookings(calendar.data?.bookings ?? []), [calendar.data]);

  return (
    <div className="flex flex-col gap-4">
      <PendingRequests venue={venue} onShow={(date) => {
        const [y, m] = date.split("-").map(Number);
        setCursor({ y, m: m - 1 });
        setSelected(date);
        setView("month");
      }} />

      <Card className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1">
            <button type="button" aria-label="Oldingi oy" onClick={() => shift(-1)} className="glass inline-flex size-9 items-center justify-center rounded-xl hover:bg-muted">
              <ChevronLeftIcon className="size-4" />
            </button>
            <p className="min-w-36 text-center text-base font-bold tabular-nums">
              {MONTHS[cursor.m]} {cursor.y}
            </p>
            <button type="button" aria-label="Keyingi oy" onClick={() => shift(1)} className="glass inline-flex size-9 items-center justify-center rounded-xl hover:bg-muted">
              <ChevronRightIcon className="size-4" />
            </button>
          </div>
          <Button size="sm" variant="ghost" onClick={goToday}>
            Bugun
          </Button>
          {halls.length > 1 && (
            <div className="glass flex flex-wrap gap-1 rounded-xl p-1" role="group" aria-label="Zal">
              {halls.map((h) => (
                <button
                  key={h.id}
                  type="button"
                  aria-pressed={hall?.id === h.id}
                  onClick={() => setHallId(h.id)}
                  className={cn("rounded-lg px-3 py-1.5 text-xs font-semibold", hall?.id === h.id ? "brand-gradient text-white" : "text-muted-foreground hover:text-foreground")}
                >
                  {h.name}
                </button>
              ))}
            </div>
          )}
          <div className="ml-auto flex items-center gap-2">
            <div className="glass flex gap-1 rounded-xl p-1" role="group" aria-label="Ko'rinish">
              {([
                ["month", "Oy", CalendarDaysIcon],
                ["list", "Ro'yxat", ListIcon],
              ] as const).map(([key, label, Icon]) => (
                <button
                  key={key}
                  type="button"
                  aria-pressed={view === key}
                  onClick={() => setView(key)}
                  className={cn("flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold", view === key ? "brand-gradient text-white" : "text-muted-foreground hover:text-foreground")}
                >
                  <Icon className="size-3.5" /> {label}
                </button>
              ))}
            </div>
            {can(venue, "MANAGE_SCHEDULE") && (
              <Button size="sm" variant="outline" onClick={() => setSessionsOpen(true)}>
                <Settings2Icon /> Smenalar
              </Button>
            )}
          </div>
        </div>

        <Legend />

        {calendar.isPending ? (
          <Skeleton className="h-96 rounded-2xl" />
        ) : calendar.error ? (
          <ErrorState error={calendar.error} onRetry={() => calendar.refetch()} />
        ) : !hall ? (
          <EmptyState title="Faol zal yo'q" description="Zallar bo'limida zal qo'shing yoki yoqing." />
        ) : view === "month" ? (
          <MonthGrid
            days={grid.days}
            month={cursor.m}
            hall={hall}
            today={today}
            selected={selected}
            onSelect={setSelected}
            slotOf={slotOf}
            loading={calendar.isFetching}
          />
        ) : (
          <ListView bookings={(calendar.data?.bookings ?? []).filter((b) => b.date.slice(5, 7) === String(cursor.m + 1).padStart(2, "0"))} />
        )}
      </Card>

      {view === "month" && hall && calendar.data && (
        <DayPanel venue={venue} date={selected} halls={halls} slotOf={slotOf} today={today} />
      )}

      {calendar.data && (
        <SessionsModal open={sessionsOpen} onClose={() => setSessionsOpen(false)} venueId={venue.id} halls={calendar.data.halls.filter((h) => h.is_active)} />
      )}
    </div>
  );
}

function Legend() {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
      {Object.entries(SLOT_TONE).map(([key, tone]) => (
        <span key={key} className="flex items-center gap-1.5">
          <i className={cn("size-2.5 rounded-full", tone.dot)} /> {tone.label}
        </span>
      ))}
    </div>
  );
}

// ============================================================ month grid
function MonthGrid({
  days,
  month,
  hall,
  today,
  selected,
  onSelect,
  slotOf,
  loading,
}: {
  days: Date[];
  month: number;
  hall: CalendarHall;
  today: string;
  selected: string;
  onSelect: (d: string) => void;
  slotOf: (sessionId: string, date: string) => SlotState;
  loading: boolean;
}) {
  const sessions = hall.sessions.filter((s) => s.is_active);
  return (
    <div className={cn("grid grid-cols-7 gap-1 transition-opacity sm:gap-1.5", loading && "opacity-60")}>
      {WEEKDAYS.map((w, i) => (
        <span key={w} className={cn("pb-1 text-center text-[11px] font-bold uppercase", i >= 5 ? "text-accent" : "text-muted-foreground")}>
          {w}
        </span>
      ))}
      {days.map((d) => {
        const iso = isoDate(d);
        const outside = d.getMonth() !== month;
        const past = iso < today;
        return (
          <button
            key={iso}
            type="button"
            onClick={() => onSelect(iso)}
            className={cn(
              "flex min-h-16 flex-col gap-1 rounded-xl border p-1 text-left transition sm:min-h-24 sm:p-1.5",
              selected === iso ? "border-brand ring-2 ring-brand/30" : "border-border hover:border-cyan-400/50",
              outside && "opacity-40",
              past && "bg-muted/40",
            )}
          >
            <span className={cn("text-xs font-bold tabular-nums", iso === today && "flex size-5 items-center justify-center rounded-full brand-gradient text-white")}>
              {d.getDate()}
            </span>
            {/* phones: dots; wider screens: labelled pills */}
            <span className="flex flex-wrap gap-0.5 sm:hidden">
              {sessions.map((s) => {
                const st = slotOf(s.id, iso);
                return <i key={s.id} className={cn("size-2 rounded-full", SLOT_TONE[st.kind].dot, past && st.kind === "FREE" && "opacity-30")} />;
              })}
            </span>
            <span className="hidden flex-col gap-0.5 sm:flex">
              {sessions.map((s) => {
                const st = slotOf(s.id, iso);
                const label =
                  st.kind === "CONFIRMED"
                    ? EVENT_SHORT[st.entry.event_type]
                    : st.kind === "BLOCKED"
                      ? "Yopiq"
                      : st.kind === "REQUESTED"
                        ? `${st.requests.length} so'rov`
                        : "";
                return (
                  <span
                    key={s.id}
                    title={`${s.name} ${hhmm(s.starts_at)}–${hhmm(s.ends_at)}`}
                    className={cn(
                      "truncate rounded-md px-1 py-px text-[10px] leading-4 font-semibold",
                      SLOT_TONE[st.kind].className,
                      past && st.kind === "FREE" && "opacity-40",
                    )}
                  >
                    {hhmm(s.starts_at)} {label || s.name}
                  </span>
                );
              })}
            </span>
          </button>
        );
      })}
    </div>
  );
}

// ============================================================== list view
function ListView({ bookings }: { bookings: Booking[] }) {
  const rows = bookings.filter((b) => b.status !== "REQUESTED");
  if (rows.length === 0) return <EmptyState title="Bu oyda yozuv yo'q" description="Kalendardan kunni tanlab, mijoz yoki yopiq smena qo'shing." />;
  return (
    <ul className="flex flex-col divide-y divide-border">
      {rows.map((b) => (
        <li key={b.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2.5 text-sm">
          <span className="w-32 font-bold">{formatEventDate(b.date)}</span>
          <span className="w-36 text-muted-foreground tabular-nums">
            {b.session.name} {hhmm(b.session.starts_at)}–{hhmm(b.session.ends_at)}
          </span>
          <span className="w-28">{b.hall.name}</span>
          <Badge tone={b.status === "BLOCKED" ? "neutral" : "brand"}>{b.status === "BLOCKED" ? "Yopiq" : EVENT_TYPE_LABELS[b.event_type]}</Badge>
          <span className="min-w-0 flex-1 truncate">
            {b.contact_name || b.requester?.full_name || ""}
            {b.guest_count ? ` · ${b.guest_count} kishi` : ""}
          </span>
          {(b.contact_phone || b.requester?.phone_number) && (
            <a href={`tel:${b.contact_phone || b.requester?.phone_number}`} className="font-semibold text-brand dark:text-cyan-300">
              {formatPhone(b.contact_phone || b.requester?.phone_number)}
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}

// ======================================================= pending requests
function PendingRequests({ venue, onShow }: { venue: Venue; onShow: (date: string) => void }) {
  const pending = usePendingRequests(venue.id);
  const rows = pending.data ?? [];
  if (rows.length === 0) return null;
  return (
    <Card className="flex flex-col gap-3 border-amber-400/40">
      <h3 className="flex items-center gap-2 text-base font-bold">
        <BellRingIcon className="size-5 text-amber-500" aria-hidden /> Yangi so&apos;rovlar
        <Badge tone="warning">{rows.length}</Badge>
      </h3>
      <ul className="flex flex-col gap-2">
        {rows.map((b) => (
          <li key={b.id} className="flex flex-wrap items-center gap-3 rounded-2xl bg-amber-500/[0.07] p-3">
            <button type="button" onClick={() => onShow(b.date)} className="min-w-0 flex-1 text-left">
              <p className="font-bold">
                {formatEventDate(b.date)} · {b.session.name} {hhmm(b.session.starts_at)}–{hhmm(b.session.ends_at)} · {b.hall.name}
              </p>
              <RequestDetails b={b} />
            </button>
            <RequestActions venue={venue} b={b} />
          </li>
        ))}
      </ul>
    </Card>
  );
}

function RequestDetails({ b }: { b: Booking }) {
  return (
    <p className="text-sm text-muted-foreground">
      {EVENT_TYPE_LABELS[b.event_type]}
      {b.guest_count ? ` · ${b.guest_count} mehmon` : ""} · {b.contact_name || b.requester?.full_name}
      {(b.contact_phone || b.requester?.phone_number) && <> · {formatPhone(b.contact_phone || b.requester?.phone_number)}</>}
      {b.note && <span className="block text-foreground/80">“{b.note}”</span>}
    </p>
  );
}

function RequestActions({ venue, b }: { venue: Venue; b: Booking }) {
  const decide = useDecide(venue.id);
  if (!can(venue, "MANAGE_BOOKINGS")) return null;
  const run = (action: "confirm" | "reject") => {
    if (action === "reject" && !window.confirm("So'rovni rad etasizmi?")) return;
    decide.mutate(
      { id: b.id, action },
      {
        onSuccess: () => toast.success(action === "confirm" ? "Tasdiqlandi — smena band" : "Rad etildi"),
        onError: (e) => toast.error(apiMessage(e, "Amal bajarilmadi")),
      },
    );
  };
  return (
    <div className="flex gap-2">
      <Button size="sm" variant="ghost" onClick={() => run("reject")} disabled={decide.isPending}>
        <XIcon /> Rad etish
      </Button>
      <Button size="sm" onClick={() => run("confirm")} loading={decide.isPending}>
        <CheckIcon /> Tasdiqlash
      </Button>
    </div>
  );
}

// ============================================================= day panel
function DayPanel({
  venue,
  date,
  halls,
  slotOf,
  today,
}: {
  venue: Venue;
  date: string;
  halls: CalendarHall[];
  slotOf: (sessionId: string, date: string) => SlotState;
  today: string;
}) {
  const [editor, setEditor] = useState<{ session: HallSession; hall: CalendarHall; entry?: Booking } | null>(null);
  const create = useCreateEntry(venue.id);
  const decide = useDecide(venue.id);
  const canBook = can(venue, "MANAGE_BOOKINGS");
  const canSchedule = can(venue, "MANAGE_SCHEDULE");

  const block = (session: HallSession) =>
    create.mutate(
      { session: session.id, date, status: "BLOCKED" },
      { onSuccess: () => toast.success("Smena yopildi"), onError: (e) => toast.error(apiMessage(e, "Yopilmadi")) },
    );
  const cancel = (entry: Booking) => {
    const q = entry.status === "BLOCKED" ? "Smenani qayta ochasizmi?" : "Bu marosimni bekor qilasizmi? Smena bo'shaydi.";
    if (!window.confirm(q)) return;
    decide.mutate(
      { id: entry.id, action: "cancel" },
      { onSuccess: () => toast.success("Smena bo'shatildi"), onError: (e) => toast.error(apiMessage(e, "Bajarilmadi")) },
    );
  };

  return (
    <Card className="flex flex-col gap-4">
      <h3 className="text-lg font-bold">
        {formatEventDate(date)}
        {date < today && <span className="ml-2 text-sm font-normal text-muted-foreground">(o&apos;tgan kun)</span>}
      </h3>
      {halls.map((hall) => (
        <div key={hall.id} className="flex flex-col gap-2">
          <p className="flex items-center gap-2 text-sm font-bold">
            {hall.name}
            <span className="flex items-center gap-1 text-xs font-normal text-muted-foreground">
              <UsersIcon className="size-3.5" aria-hidden /> {hall.capacity}
            </span>
          </p>
          <ul className="flex flex-col gap-2">
            {hall.sessions
              .filter((s) => s.is_active)
              .map((s) => {
                const st = slotOf(s.id, date);
                return (
                  <li key={s.id} className={cn("flex flex-wrap items-center gap-3 rounded-2xl p-3", SLOT_TONE[st.kind].className.split(" ")[0])}>
                    <div className="flex w-36 shrink-0 items-center gap-2">
                      <ClockIcon className="size-4 opacity-60" aria-hidden />
                      <div>
                        <p className="text-sm font-bold">{s.name}</p>
                        <p className="text-xs text-muted-foreground tabular-nums">
                          {hhmm(s.starts_at)}–{hhmm(s.ends_at)}
                        </p>
                      </div>
                    </div>
                    <div className="min-w-0 flex-1 text-sm">
                      {st.kind === "FREE" && <span className="font-semibold text-emerald-700 dark:text-emerald-300">Bo&apos;sh</span>}
                      {st.kind === "BLOCKED" && (
                        <span className="font-semibold">
                          Yopiq{st.entry.venue_note && <span className="font-normal text-muted-foreground"> · {st.entry.venue_note}</span>}
                        </span>
                      )}
                      {st.kind === "CONFIRMED" && (
                        <div>
                          <p className="font-bold">
                            {EVENT_TYPE_LABELS[st.entry.event_type]}
                            {st.entry.guest_count ? <span className="font-normal"> · {st.entry.guest_count} mehmon</span> : null}
                          </p>
                          <p className="flex flex-wrap items-center gap-x-3 text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <UserIcon className="size-3.5" aria-hidden />
                              {st.entry.contact_name || st.entry.requester?.full_name || "—"}
                            </span>
                            {(st.entry.contact_phone || st.entry.requester?.phone_number) && (
                              <a href={`tel:${st.entry.contact_phone || st.entry.requester?.phone_number}`} className="flex items-center gap-1 font-semibold text-brand dark:text-cyan-300">
                                <PhoneIcon className="size-3.5" aria-hidden />
                                {formatPhone(st.entry.contact_phone || st.entry.requester?.phone_number)}
                              </a>
                            )}
                            {st.entry.source === "USER" && <Badge tone="brand">Ilova orqali</Badge>}
                          </p>
                          {(st.entry.note || st.entry.venue_note) && (
                            <p className="text-xs text-foreground/75">{[st.entry.note, st.entry.venue_note].filter(Boolean).join(" · ")}</p>
                          )}
                        </div>
                      )}
                      {st.kind === "REQUESTED" && (
                        <ul className="flex flex-col gap-2">
                          {st.requests.map((r) => (
                            <li key={r.id} className="flex flex-wrap items-center gap-2">
                              <div className="min-w-0 flex-1">
                                <Badge tone="warning">So&apos;rov</Badge>
                                <RequestDetails b={r} />
                              </div>
                              <RequestActions venue={venue} b={r} />
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(st.kind === "FREE" || st.kind === "REQUESTED") && canBook && (
                        <Button size="sm" variant="outline" onClick={() => setEditor({ session: s, hall })}>
                          <PlusIcon /> Mijoz yozish
                        </Button>
                      )}
                      {(st.kind === "FREE" || st.kind === "REQUESTED") && canSchedule && (
                        <Button size="sm" variant="ghost" onClick={() => block(s)} disabled={create.isPending}>
                          <BanIcon /> Yopish
                        </Button>
                      )}
                      {st.kind === "CONFIRMED" && canBook && (
                        <>
                          <Button size="sm" variant="outline" onClick={() => setEditor({ session: s, hall, entry: st.entry })}>
                            <PencilIcon /> Tahrirlash
                          </Button>
                          <Button size="sm" variant="danger" onClick={() => cancel(st.entry)} disabled={decide.isPending}>
                            <XIcon /> Bekor qilish
                          </Button>
                        </>
                      )}
                      {st.kind === "BLOCKED" && canSchedule && (
                        <Button size="sm" variant="outline" onClick={() => cancel(st.entry)} disabled={decide.isPending}>
                          <LockOpenIcon /> Ochish
                        </Button>
                      )}
                    </div>
                  </li>
                );
              })}
          </ul>
        </div>
      ))}
      <EntryModal venueId={venue.id} date={date} target={editor} onClose={() => setEditor(null)} />
    </Card>
  );
}

// =========================================================== entry modal
function EntryModal({
  venueId,
  date,
  target,
  onClose,
}: {
  venueId: string;
  date: string;
  target: { session: HallSession; hall: CalendarHall; entry?: Booking } | null;
  onClose: () => void;
}) {
  return (
    <Modal open={Boolean(target)} onClose={onClose} title={target?.entry ? "Marosimni tahrirlash" : "Mijoz yozish"}>
      {target && <EntryForm key={target.entry?.id ?? target.session.id} venueId={venueId} date={date} target={target} onDone={onClose} />}
    </Modal>
  );
}

function EntryForm({
  venueId,
  date,
  target,
  onDone,
}: {
  venueId: string;
  date: string;
  target: { session: HallSession; hall: CalendarHall; entry?: Booking };
  onDone: () => void;
}) {
  const { entry, session, hall } = target;
  const create = useCreateEntry(venueId);
  const update = useUpdateEntry(venueId);
  const [eventType, setEventType] = useState<BookingEventType>(entry?.event_type ?? "WEDDING");
  const [name, setName] = useState(entry?.contact_name || entry?.requester?.full_name || "");
  const [phone, setPhone] = useState(entry?.contact_phone || "");
  const [guests, setGuests] = useState(entry?.guest_count ? String(entry.guest_count) : "");
  const [note, setNote] = useState(entry?.venue_note ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    const body = {
      event_type: eventType,
      contact_name: name.trim(),
      contact_phone: phone,
      guest_count: guests ? Number(guests) : null,
      venue_note: note.trim(),
    };
    const handlers = {
      onSuccess: () => {
        toast.success(entry ? "Saqlandi" : "Smena band qilindi");
        onDone();
      },
      onError: (err: unknown) => {
        if (err instanceof ApiError) setErrors(err.fieldErrors);
        toast.error(apiMessage(err, "Saqlanmadi"));
      },
    };
    if (entry) update.mutate({ id: entry.id, ...body }, handlers);
    else create.mutate({ session: session.id, date, status: "CONFIRMED", ...body }, handlers);
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <p className="rounded-2xl bg-muted p-3 text-sm">
        <b>{formatEventDate(entry?.date ?? date)}</b> · {session.name} {hhmm(session.starts_at)}–{hhmm(session.ends_at)} · {hall.name}
      </p>
      <Field label="Marosim turi" htmlFor="e-type" error={errors.event_type}>
        <Select id="e-type" value={eventType} onChange={(e) => setEventType(e.target.value as BookingEventType)}>
          {Object.entries(EVENT_TYPE_LABELS).map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </Select>
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Mijoz ismi" htmlFor="e-name" error={errors.contact_name}>
          <Input id="e-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Aliyevlar oilasi" maxLength={150} />
        </Field>
        <Field label="Telefon" htmlFor="e-phone" error={errors.contact_phone}>
          <PhoneInput id="e-phone" value={phone} onChange={setPhone} />
        </Field>
      </div>
      <Field label="Mehmonlar soni" htmlFor="e-guests" error={errors.guest_count} hint={`Zal sig'imi: ${hall.capacity}`}>
        <Input id="e-guests" type="number" inputMode="numeric" min={1} value={guests} onChange={(e) => setGuests(e.target.value)} />
      </Field>
      <Field label="Ichki izoh (mijozga ko'rinmaydi)" htmlFor="e-note" error={errors.venue_note}>
        <Textarea id="e-note" value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} placeholder="Menyu, oldindan to'lov, bezak…" />
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>
          Bekor qilish
        </Button>
        <Button type="submit" loading={create.isPending || update.isPending}>
          {entry ? "Saqlash" : "Band qilish"}
        </Button>
      </div>
    </form>
  );
}

// ========================================================= sessions modal
function SessionsModal({ open, onClose, venueId, halls }: { open: boolean; onClose: () => void; venueId: string; halls: CalendarHall[] }) {
  return (
    <Modal open={open} onClose={onClose} title="Smenalar (kun bo'linishi)">
      <div className="flex flex-col gap-5">
        <p className="text-sm text-muted-foreground">
          Har bir zal kuni shu smenalarga bo&apos;linadi. Mijozlar qidiruvda aynan shu smenalarni ko&apos;radi va band qiladi.
          Smenalar vaqt bo&apos;yicha kesishmasligi kerak.
        </p>
        {halls.map((h) => (
          <HallSessions key={h.id} venueId={venueId} hall={h} />
        ))}
      </div>
    </Modal>
  );
}

function HallSessions({ venueId, hall }: { venueId: string; hall: CalendarHall }) {
  const create = useCreateSession(venueId);
  const [draft, setDraft] = useState({ name: "", starts_at: "", ends_at: "" });
  const add = (e: React.FormEvent) => {
    e.preventDefault();
    create.mutate(
      { hallId: hall.id, ...draft },
      {
        onSuccess: () => {
          setDraft({ name: "", starts_at: "", ends_at: "" });
          toast.success("Smena qo'shildi");
        },
        onError: (err) => toast.error(apiMessage(err, "Qo'shilmadi")),
      },
    );
  };
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-bold">{hall.name}</p>
      <ul className="flex flex-col gap-2">
        {hall.sessions.map((s) => (
          <SessionRow key={`${s.id}-${s.name}-${s.starts_at}-${s.ends_at}-${s.is_active}`} venueId={venueId} hallId={hall.id} session={s} />
        ))}
      </ul>
      <form onSubmit={add} className="flex flex-wrap items-end gap-2">
        <Input aria-label="Yangi smena nomi" className="h-9 w-32 flex-1" placeholder="Nomi" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} required />
        <Input aria-label="Boshlanishi" className="h-9 w-28" type="time" value={draft.starts_at} onChange={(e) => setDraft({ ...draft, starts_at: e.target.value })} required />
        <Input aria-label="Tugashi" className="h-9 w-28" type="time" value={draft.ends_at} onChange={(e) => setDraft({ ...draft, ends_at: e.target.value })} required />
        <Button size="sm" type="submit" loading={create.isPending}>
          <PlusIcon /> Qo&apos;shish
        </Button>
      </form>
    </div>
  );
}

function SessionRow({ venueId, hallId, session }: { venueId: string; hallId: string; session: HallSession }) {
  const update = useUpdateSession(venueId);
  const [form, setForm] = useState({ name: session.name, starts_at: hhmm(session.starts_at), ends_at: hhmm(session.ends_at) });
  const dirty = form.name !== session.name || form.starts_at !== hhmm(session.starts_at) || form.ends_at !== hhmm(session.ends_at);
  const save = (body: Partial<HallSession>, ok: string) =>
    update.mutate({ hallId, id: session.id, ...body }, { onSuccess: () => toast.success(ok), onError: (e) => toast.error(apiMessage(e, "Saqlanmadi")) });
  return (
    <li className={cn("flex flex-wrap items-center gap-2", !session.is_active && "opacity-50")}>
      <Input aria-label="Smena nomi" className="h-9 w-32 flex-1" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      <Input aria-label="Boshlanishi" className="h-9 w-28" type="time" value={form.starts_at} onChange={(e) => setForm({ ...form, starts_at: e.target.value })} />
      <Input aria-label="Tugashi" className="h-9 w-28" type="time" value={form.ends_at} onChange={(e) => setForm({ ...form, ends_at: e.target.value })} />
      {dirty ? (
        <Button size="sm" onClick={() => save(form, "Saqlandi")} loading={update.isPending}>
          <CheckIcon /> Saqlash
        </Button>
      ) : (
        <Button size="sm" variant="ghost" onClick={() => save({ is_active: !session.is_active }, session.is_active ? "O'chirildi" : "Yoqildi")} disabled={update.isPending}>
          {session.is_active ? "O'chirish" : "Yoqish"}
        </Button>
      )}
    </li>
  );
}
