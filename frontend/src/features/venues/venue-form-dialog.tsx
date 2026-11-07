"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2Icon } from "lucide-react";
import { motion, useAnimationControls } from "motion/react";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Field, ImageUpload } from "@/components/common/form";
import { PhoneInput } from "@/components/common/phone-input";
import { MotionDialog } from "@/components/motion/motion-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useCan } from "@/features/auth/hooks";
import { usersResource } from "@/features/resources";
import { ApiError } from "@/lib/api/client";
import type { AdminVenue, PublicationStatus, VenueRegion, VenueType } from "@/lib/api/types";
import { optionalPhoneSchema } from "@/lib/phone";
import { shake } from "@/motion/tokens";

import { PUBLICATION, REGION_LABELS, VENUE_TYPE_LABELS, venuesResource } from "./api";

const digits = (v: string) => v.replace(/\D/g, "");
const groupDigits = (v: string) => digits(v).replace(/\B(?=(\d{3})+(?!\d))/g, " ");

function buildSchema(creating: boolean) {
  return z
    .object({
      owner_id: z.string(),
      name: z.string().trim().min(1, "Nomini kiriting").max(150),
      venue_type: z.string(),
      region: z.string(),
      district: z.string().trim().max(100),
      address: z.string().trim().min(1, "Manzilni kiriting").max(255),
      phone_number: optionalPhoneSchema,
      capacity_min: z.string(),
      capacity_max: z.string().refine((v) => Number(digits(v)) >= 1, "Maksimal sig'imni kiriting"),
      base_price: z.string().refine((v) => digits(v).length > 0, "Narxni kiriting"),
      description: z.string().max(4000),
      is_active: z.boolean(),
      publication_status: z.string(),
      cover_image: z.custom<File | null | undefined>(),
    })
    .superRefine((v, ctx) => {
      if (creating && !v.owner_id) ctx.addIssue({ code: "custom", path: ["owner_id"], message: "To'yxona egasini tanlang" });
      if (Number(digits(v.capacity_min) || 0) > Number(digits(v.capacity_max) || 0))
        ctx.addIssue({ code: "custom", path: ["capacity_min"], message: "Minimal sig'im maksimaldan katta" });
    });
}
type Values = z.input<ReturnType<typeof buildSchema>>;

const blank: Values = {
  owner_id: "",
  name: "",
  venue_type: "BANQUET_HALL",
  region: "TASHKENT_CITY",
  district: "",
  address: "",
  phone_number: "",
  capacity_min: "0",
  capacity_max: "",
  base_price: "",
  description: "",
  is_active: true,
  publication_status: "PRIVATE",
  cover_image: undefined,
};

export function VenueFormDialog({
  open,
  onOpenChange,
  venue,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  venue?: AdminVenue | null;
}) {
  const can = useCan();
  const creating = !venue;
  const create = venuesResource.useCreate();
  const update = venuesResource.useUpdate();
  const pending = create.isPending || update.isPending;
  const controls = useAnimationControls();
  const [ownerSearch, setOwnerSearch] = useState("");
  const owners = usersResource.useList(
    { role: "VENUE_OWNER", is_active: "true", page_size: 50, ordering: "first_name", search: ownerSearch || undefined },
    open && creating,
  );

  const form = useForm<Values>({ resolver: zodResolver(buildSchema(creating)), defaultValues: blank });
  const { errors } = form.formState;

  useEffect(() => {
    if (!open) return;
    form.reset(
      venue
        ? {
            owner_id: "",
            name: venue.name,
            venue_type: venue.venue_type,
            region: venue.region,
            district: venue.district,
            address: venue.address,
            phone_number: venue.phone_number,
            capacity_min: String(venue.capacity_min),
            capacity_max: String(venue.capacity_max),
            base_price: String(Math.round(Number(venue.base_price))),
            description: venue.description,
            is_active: venue.is_active,
            publication_status: venue.publication_status,
            cover_image: undefined,
          }
        : blank,
    );
  }, [open, venue, form]);

  const onSubmit = form.handleSubmit(
    (raw) => {
      const v = buildSchema(creating).parse(raw);
      const payload: Record<string, unknown> = {
        name: v.name,
        venue_type: v.venue_type,
        region: v.region,
        district: v.district,
        address: v.address,
        phone_number: v.phone_number,
        capacity_min: Number(digits(v.capacity_min) || 0),
        capacity_max: Number(digits(v.capacity_max)),
        base_price: digits(v.base_price),
        description: v.description.trim(),
        is_active: v.is_active,
      };
      if (creating) payload.owner_id = v.owner_id;
      if (can("venues.publish") && (creating ? v.publication_status !== "PRIVATE" : v.publication_status !== venue?.publication_status))
        payload.publication_status = v.publication_status;
      if (v.cover_image !== undefined) payload.cover_image = v.cover_image;

      const done = () => {
        toast.success(creating ? "To'yxona qo'shildi" : "O'zgarishlar saqlandi");
        onOpenChange(false);
      };
      const fail = (error: Error) => {
        if (error instanceof ApiError) {
          let mapped = false;
          for (const [key, message] of Object.entries(error.fieldErrors)) {
            if (key in v) {
              form.setError(key as keyof Values, { message });
              mapped = true;
            }
          }
          if (!mapped) toast.error(error.message);
        } else toast.error("Saqlashda xatolik yuz berdi");
        controls.start(shake);
      };
      if (venue) update.mutate({ id: venue.id, values: payload }, { onSuccess: done, onError: fail });
      else create.mutate(payload, { onSuccess: done, onError: fail });
    },
    () => controls.start(shake),
  );

  return (
    <MotionDialog
      open={open}
      onOpenChange={(next) => !pending && onOpenChange(next)}
      title={venue ? venue.name : "Yangi to'yxona"}
      description="To'yxona egasi — 'To'yxona' rolidagi foydalanuvchi. U o'z kabinetidan zallar, jamoa va jadvalni boshqaradi."
      size="lg"
    >
      <motion.form animate={controls} onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        <Controller
          control={form.control}
          name="cover_image"
          render={({ field }) => (
            <ImageUpload label="Muqova rasmi" currentUrl={venue?.cover_image} value={field.value} onChange={field.onChange} />
          )}
        />

        {creating && (
          <Field label="To'yxona egasi" htmlFor="venue-owner" error={errors.owner_id?.message} hint="Faqat 'To'yxona' rolidagi faol foydalanuvchilar">
            <Controller
              control={form.control}
              name="owner_id"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange} onOpenChange={(o) => !o && setOwnerSearch("")}>
                  <SelectTrigger id="venue-owner" className="w-full" aria-invalid={Boolean(errors.owner_id)}>
                    <SelectValue placeholder={owners.isPending ? "Yuklanmoqda…" : "Tanlang"} />
                  </SelectTrigger>
                  <SelectContent>
                    <div className="p-1.5">
                      <input
                        value={ownerSearch}
                        onChange={(e) => setOwnerSearch(e.target.value)}
                        onKeyDown={(e) => e.stopPropagation()}
                        placeholder="Qidirish…"
                        aria-label="Egani qidirish"
                        className="h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-brand"
                      />
                    </div>
                    {owners.error ? (
                      <p className="px-3 py-2 text-sm text-destructive">Ro&apos;yxat uchun &quot;Foydalanuvchilarni ko&apos;rish&quot; ruxsati kerak</p>
                    ) : (
                      owners.data?.results.length === 0 && (
                        <p className="px-3 py-2 text-sm text-muted-foreground">
                          &quot;To&apos;yxona&quot; rolidagi faol foydalanuvchi yo&apos;q. Avval Foydalanuvchilar bo&apos;limida yarating.
                        </p>
                      )
                    )}
                    {owners.data?.results.map((o) => (
                      <SelectItem key={o.id} value={o.id}>
                        {o.full_name} · <span className="text-muted-foreground tabular-nums">{o.phone_number}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </Field>
        )}

        <Field label="Nomi" htmlFor="venue-name" error={errors.name?.message}>
          <Input id="venue-name" placeholder="Masalan: Navro'z to'yxonasi" aria-invalid={Boolean(errors.name)} {...form.register("name")} />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Turi" htmlFor="venue-type">
            <Controller
              control={form.control}
              name="venue_type"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="venue-type" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(VENUE_TYPE_LABELS) as VenueType[]).map((k) => (
                      <SelectItem key={k} value={k}>
                        {VENUE_TYPE_LABELS[k]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </Field>
          <Field label="Aloqa telefoni" htmlFor="venue-phone" error={errors.phone_number?.message} hint="Mijozlar shu raqamga qo'ng'iroq qiladi">
            <Controller
              control={form.control}
              name="phone_number"
              render={({ field }) => (
                <PhoneInput id="venue-phone" value={field.value ?? ""} onChange={field.onChange} onBlur={field.onBlur} ref={field.ref} aria-invalid={Boolean(errors.phone_number)} />
              )}
            />
          </Field>
          <Field label="Hudud" htmlFor="venue-region">
            <Controller
              control={form.control}
              name="region"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="venue-region" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(REGION_LABELS) as VenueRegion[]).map((k) => (
                      <SelectItem key={k} value={k}>
                        {REGION_LABELS[k]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </Field>
          <Field label="Tuman" htmlFor="venue-district" error={errors.district?.message}>
            <Input id="venue-district" placeholder="Masalan: Chilonzor" {...form.register("district")} />
          </Field>
        </div>

        <Field label="Manzil" htmlFor="venue-address" error={errors.address?.message}>
          <Input id="venue-address" placeholder="Ko'cha, uy, mo'ljal" aria-invalid={Boolean(errors.address)} {...form.register("address")} />
        </Field>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Sig'im (min)" htmlFor="venue-cap-min" error={errors.capacity_min?.message}>
            <Input id="venue-cap-min" inputMode="numeric" className="tabular-nums" {...form.register("capacity_min")} />
          </Field>
          <Field label="Sig'im (max)" htmlFor="venue-cap-max" error={errors.capacity_max?.message}>
            <Input id="venue-cap-max" inputMode="numeric" placeholder="600" className="tabular-nums" aria-invalid={Boolean(errors.capacity_max)} {...form.register("capacity_max")} />
          </Field>
          <Field label="Asosiy narx (so'm)" htmlFor="venue-price" error={errors.base_price?.message}>
            <Controller
              control={form.control}
              name="base_price"
              render={({ field }) => (
                <Input
                  id="venue-price"
                  inputMode="numeric"
                  placeholder="45 000 000"
                  className="tabular-nums"
                  aria-invalid={Boolean(errors.base_price)}
                  value={groupDigits(field.value)}
                  onChange={(e) => field.onChange(digits(e.target.value))}
                />
              )}
            />
          </Field>
        </div>

        <Field label="Tavsif" htmlFor="venue-description" error={errors.description?.message}>
          <Textarea id="venue-description" rows={3} placeholder="Xizmatlar, menyu, avtoturargoh…" {...form.register("description")} />
        </Field>

        <div className="grid gap-3 sm:grid-cols-2">
          <Controller
            control={form.control}
            name="is_active"
            render={({ field }) => (
              <label className="flex items-center justify-between rounded-2xl bg-muted/60 px-4 py-3 text-sm font-semibold">
                Faol (bloklanmagan)
                <Switch checked={field.value} onCheckedChange={field.onChange} />
              </label>
            )}
          />
          {can("venues.publish") && (
            <Controller
              control={form.control}
              name="publication_status"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger aria-label="Ommaga chiqarish holati" className="h-auto w-full rounded-2xl py-3">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(PUBLICATION) as PublicationStatus[]).map((k) => (
                      <SelectItem key={k} value={k}>
                        {PUBLICATION[k].label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          )}
        </div>

        <div className="flex gap-3 pt-1">
          <Button type="button" variant="outline" className="h-11 flex-1" onClick={() => onOpenChange(false)} disabled={pending}>
            Bekor qilish
          </Button>
          <Button type="submit" className="h-11 flex-1" disabled={pending}>
            {pending && <Loader2Icon className="animate-spin" />}
            Saqlash
          </Button>
        </div>
      </motion.form>
    </MotionDialog>
  );
}
