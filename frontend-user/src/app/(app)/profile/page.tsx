"use client";

import { PaidBadge } from "@/components/paid-badge";

import { CheckCircle2Icon, ShieldAlertIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageTitle } from "@/components/shell";
import { Avatar, Badge, Button, Card, Field, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useMe, useUpdateProfile } from "@/lib/auth";
import { formatDateTime, formatPhone } from "@/lib/format";
import type { Me } from "@/lib/types";

function ProfileForm({ me }: { me: Me }) {
  const update = useUpdateProfile();
  const [values, setValues] = useState({ first_name: me.first_name, last_name: me.last_name, address: me.address });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const set = (key: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));

  return (
    <form
      noValidate
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        setErrors({});
        update.mutate(values, {
          onSuccess: () => toast.success("Profil saqlandi"),
          onError: (err) => {
            if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors);
            else toast.error("Saqlab bo'lmadi");
          },
        });
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Ism" htmlFor="first_name" error={errors.first_name}>
          <Input id="first_name" value={values.first_name} onChange={set("first_name")} maxLength={100} />
        </Field>
        <Field label="Familiya" htmlFor="last_name" error={errors.last_name}>
          <Input id="last_name" value={values.last_name} onChange={set("last_name")} maxLength={100} />
        </Field>
      </div>
      <Field label="Manzil" htmlFor="address" error={errors.address}>
        <Input id="address" value={values.address} onChange={set("address")} maxLength={255} placeholder="Masalan: Toshkent" />
      </Field>
      <Button type="submit" loading={update.isPending} className="self-start">
        Saqlash
      </Button>
    </form>
  );
}

export default function ProfilePage() {
  const { data: me } = useMe();
  if (!me) return null;
  return (
    <>
      <PageTitle title="Profil" subtitle="Shaxsiy ma'lumotlaringiz" />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        <Card className="flex flex-col gap-4">
          <div className="flex items-center gap-4">
            <Avatar first={me.first_name} last={me.last_name} src={me.profile_picture} className="size-16 text-lg" />
            <div className="min-w-0">
              <p className="truncate text-lg font-bold">{me.full_name || "Ism kiritilmagan"} <PaidBadge verified={me.is_verified} /></p>
              <p className="text-sm text-muted-foreground tabular-nums">{formatPhone(me.phone_number)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            {me.is_phone_verified ? (
              <Badge tone="success">
                <CheckCircle2Icon className="mr-1 size-3.5" /> Telefon tasdiqlangan
              </Badge>
            ) : (
              <Badge tone="warning">
                <ShieldAlertIcon className="mr-1 size-3.5" /> Telefon hali tasdiqlanmagan
              </Badge>
            )}
          </div>
          <dl className="rounded-2xl border border-glass-border bg-muted/40 px-4 text-sm">
            {[
              ["JSHSHIR", me.pinfl_masked ?? "—"],
              ["Oxirgi kirish", formatDateTime(me.last_login)],
              ["Hisob yaratilgan", formatDateTime(me.created_at)],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4 border-b border-border/70 py-3 last:border-b-0">
                <dt className="text-muted-foreground">{k}</dt>
                <dd className="font-medium tabular-nums">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card>
          <h2 className="mb-4 text-lg font-bold">Ma&apos;lumotlarni tahrirlash</h2>
          <ProfileForm me={me} />
          <p className="mt-4 text-xs text-muted-foreground">
            Telefon raqamni o&apos;zgartirish keyinchalik SMS tasdiqlash orqali qo&apos;shiladi.
          </p>
        </Card>
      </div>
    </>
  );
}
