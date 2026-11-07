"use client";

import { useState } from "react";

import type { Region, Venue, VenueType } from "@/lib/types";
import { REGION_LABELS, VENUE_TYPE_LABELS, type VenueWrite } from "@/lib/venues";

import { PhoneInput } from "@/components/phone-input";
import { Button, Field, Input, Select, Textarea } from "./ui";

export interface VenueFormValues {
  name: string;
  venue_type: VenueType;
  region: Region;
  district: string;
  address: string;
  phone_number: string;
  capacity_min: string;
  capacity_max: string;
  base_price: string;
  description: string;
}

export const EMPTY_VENUE: VenueFormValues = {
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
};

export const venueToForm = (v: Venue): VenueFormValues => ({
  name: v.name,
  venue_type: v.venue_type,
  region: v.region,
  district: v.district,
  address: v.address,
  phone_number: v.phone_number,
  capacity_min: String(v.capacity_min),
  capacity_max: String(v.capacity_max),
  base_price: String(Math.round(Number(v.base_price))),
  description: v.description,
});

/** Digits only, so "45 000 000" and "45000000" both work; the API takes a decimal string. */
const digits = (s: string) => s.replace(/\D/g, "");
const groupDigits = (s: string) => digits(s).replace(/\B(?=(\d{3})+(?!\d))/g, " ");

export function VenueForm({
  initial,
  errors: serverErrors,
  pending,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initial: VenueFormValues;
  errors: Record<string, string>;
  pending: boolean;
  submitLabel: string;
  onSubmit: (payload: VenueWrite) => void;
  onCancel?: () => void;
}) {
  const [values, setValues] = useState(initial);
  const [local, setLocal] = useState<Record<string, string>>({});
  const errors = { ...serverErrors, ...local };
  const set = (key: keyof VenueFormValues) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    const capMin = Number(digits(values.capacity_min) || 0);
    const capMax = Number(digits(values.capacity_max));
    if (!values.name.trim()) errs.name = "Nomini kiriting";
    if (!values.address.trim()) errs.address = "Manzilni kiriting";
    if (!capMax) errs.capacity_max = "Maksimal sig'imni kiriting";
    else if (capMin > capMax) errs.capacity_min = "Minimal sig'im maksimaldan katta";
    if (!digits(values.base_price)) errs.base_price = "Narxni kiriting";
    if (values.phone_number && !/^\+998\d{9}$/.test(values.phone_number)) errs.phone_number = "Raqam +998 dan keyin 9 ta raqam";
    setLocal(errs);
    if (Object.keys(errs).length) return;
    const payload: VenueWrite = {
      name: values.name.trim(),
      venue_type: values.venue_type,
      region: values.region,
      district: values.district.trim(),
      address: values.address.trim(),
      capacity_min: capMin,
      capacity_max: capMax,
      base_price: digits(values.base_price),
      description: values.description.trim(),
    };
    // Blank phone on create = "not set"; on edit an empty string clears it.
    if (values.phone_number.trim() || initial.phone_number) payload.phone_number = values.phone_number.trim();
    onSubmit(payload);
  };

  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-4">
      <Field label="Nomi" htmlFor="name" error={errors.name}>
        <Input id="name" value={values.name} onChange={set("name")} maxLength={150} placeholder="Masalan: Navro'z to'yxonasi" aria-invalid={Boolean(errors.name)} />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Turi" htmlFor="venue_type" error={errors.venue_type}>
          <Select id="venue_type" value={values.venue_type} onChange={set("venue_type")}>
            {Object.entries(VENUE_TYPE_LABELS).map(([k, label]) => (
              <option key={k} value={k}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Aloqa telefoni" htmlFor="phone_number" error={errors.phone_number} hint="Mijozlar shu raqamga qo'ng'iroq qiladi">
          <PhoneInput id="phone_number" value={values.phone_number} onChange={(phone_number) => setValues((v) => ({ ...v, phone_number }))} />
        </Field>
        <Field label="Hudud" htmlFor="region" error={errors.region}>
          <Select id="region" value={values.region} onChange={set("region")}>
            {Object.entries(REGION_LABELS).map(([k, label]) => (
              <option key={k} value={k}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Tuman" htmlFor="district" error={errors.district}>
          <Input id="district" value={values.district} onChange={set("district")} maxLength={100} placeholder="Masalan: Chilonzor" />
        </Field>
      </div>
      <Field label="Manzil" htmlFor="address" error={errors.address}>
        <Input id="address" value={values.address} onChange={set("address")} maxLength={255} placeholder="Ko'cha, uy, mo'ljal" aria-invalid={Boolean(errors.address)} />
      </Field>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Sig'im (min)" htmlFor="capacity_min" error={errors.capacity_min}>
          <Input id="capacity_min" inputMode="numeric" value={values.capacity_min} onChange={set("capacity_min")} className="tabular-nums" />
        </Field>
        <Field label="Sig'im (max)" htmlFor="capacity_max" error={errors.capacity_max}>
          <Input id="capacity_max" inputMode="numeric" value={values.capacity_max} onChange={set("capacity_max")} placeholder="600" className="tabular-nums" aria-invalid={Boolean(errors.capacity_max)} />
        </Field>
        <Field label="Asosiy narx (so'm)" htmlFor="base_price" error={errors.base_price}>
          <Input
            id="base_price"
            inputMode="numeric"
            value={groupDigits(values.base_price)}
            onChange={(e) => setValues((v) => ({ ...v, base_price: digits(e.target.value) }))}
            placeholder="45 000 000"
            className="tabular-nums"
            aria-invalid={Boolean(errors.base_price)}
          />
        </Field>
      </div>
      <Field label="Tavsif" htmlFor="description" error={errors.description} hint="Xizmatlar, menyu, avtoturargoh, bezak va h.k.">
        <Textarea id="description" value={values.description} onChange={set("description")} maxLength={4000} />
      </Field>
      <div className="flex gap-3">
        {onCancel && (
          <Button type="button" variant="outline" className="flex-1" onClick={onCancel}>
            Bekor qilish
          </Button>
        )}
        <Button type="submit" className="flex-1" loading={pending}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
