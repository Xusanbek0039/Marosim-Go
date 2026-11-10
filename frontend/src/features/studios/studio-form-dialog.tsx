"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2Icon } from "lucide-react";
import { motion, useAnimationControls } from "motion/react";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Field, ImageUpload } from "@/components/common/form";
import { MotionDialog } from "@/components/motion/motion-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { studiosResource, usersResource } from "@/features/resources";
import { ApiError } from "@/lib/api/client";
import type { Studio } from "@/lib/api/types";
import { shake } from "@/motion/tokens";

const schema = z.object({
  name: z.string().trim().min(1, "Studiya nomini kiriting").max(150),
  address: z.string().trim().min(1, "Manzil kiritilishi shart").max(255),
  phone_number: z.string().trim().max(32),
  description: z.string().trim().max(2000),
  responsible_user_id: z.string().min(1, "Mas'ul shaxsni tanlang"),
  is_active: z.boolean(),
  portfolio_quota_gb: z.number({ message: "Raqam kiriting" }).min(0, "Manfiy bo'lmaydi").max(1000, "Juda katta"),
  profile_picture: z.custom<File | null | undefined>(),
});
type Values = z.infer<typeof schema>;

export function StudioFormDialog({
  open,
  onOpenChange,
  studio,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  studio?: Studio | null;
}) {
  const create = studiosResource.useCreate();
  const update = studiosResource.useUpdate();
  const pending = create.isPending || update.isPending;
  const controls = useAnimationControls();
  const [ownerSearch, setOwnerSearch] = useState("");

  // Candidates: active accounts with the STUDIO role (validated again server-side).
  const owners = usersResource.useList(
    { role: "STUDIO", is_active: "true", page_size: 50, ordering: "first_name", search: ownerSearch || undefined },
    open,
  );
  const ownerOptions = [...(owners.data?.results ?? [])];
  if (studio && !ownerOptions.some((o) => o.id === studio.responsible_user.id)) {
    ownerOptions.unshift({ ...studio.responsible_user, address: "", is_phone_verified: false, last_login: null, updated_at: "" });
  }

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", address: "", phone_number: "", description: "", responsible_user_id: "", is_active: true, portfolio_quota_gb: 1, profile_picture: undefined },
  });
  const { errors } = form.formState;

  useEffect(() => {
    if (!open) return;
    form.reset(
      studio
        ? {
            name: studio.name,
            address: studio.address,
            phone_number: studio.phone_number ?? "",
            description: studio.description ?? "",
            responsible_user_id: studio.responsible_user.id,
            is_active: studio.is_active,
            portfolio_quota_gb: Math.round(((studio.portfolio_quota_mb ?? 1024) / 1024) * 100) / 100,
            profile_picture: undefined,
          }
        : { name: "", address: "", phone_number: "", description: "", responsible_user_id: "", is_active: true, portfolio_quota_gb: 1, profile_picture: undefined },
    );
  }, [open, studio, form]);

  const onSubmit = form.handleSubmit(
    (values) => {
      const payload: Record<string, unknown> = {
        name: values.name,
        address: values.address,
        phone_number: values.phone_number,
        description: values.description,
        responsible_user_id: values.responsible_user_id,
        is_active: values.is_active,
        portfolio_quota_mb: Math.round(values.portfolio_quota_gb * 1024),
      };
      if (values.profile_picture !== undefined) payload.profile_picture = values.profile_picture;
      const done = () => {
        toast.success(studio ? "Studiya yangilandi" : "Studiya qo'shildi");
        onOpenChange(false);
      };
      const fail = (error: Error) => {
        if (error instanceof ApiError) {
          let mapped = false;
          for (const [key, message] of Object.entries(error.fieldErrors)) {
            if (key in values) {
              form.setError(key as keyof Values, { message });
              mapped = true;
            }
          }
          if (!mapped) toast.error(error.message);
        } else toast.error("Saqlashda xatolik yuz berdi");
        controls.start(shake);
      };
      if (studio) update.mutate({ id: studio.id, values: payload }, { onSuccess: done, onError: fail });
      else create.mutate(payload, { onSuccess: done, onError: fail });
    },
    () => controls.start(shake),
  );

  return (
    <MotionDialog
      open={open}
      onOpenChange={(next) => !pending && onOpenChange(next)}
      title={studio ? studio.name : "Yangi studiya"}
      description="Studiya — tashkilot. JSHSHIR uning mas'ul shaxsiga tegishli."
    >
      <motion.form animate={controls} onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        <Controller
          control={form.control}
          name="profile_picture"
          render={({ field }) => (
            <ImageUpload label="Logo / profil rasmi" currentUrl={studio?.profile_picture} value={field.value} onChange={field.onChange} />
          )}
        />
        <Field label="Studiya nomi" htmlFor="studio-name" error={errors.name?.message}>
          <Input id="studio-name" aria-invalid={Boolean(errors.name)} {...form.register("name")} />
        </Field>
        <Field label="Manzil" htmlFor="studio-address" error={errors.address?.message}>
          <Input
            id="studio-address"
            placeholder="Masalan: Toshkent, Yunusobod 4-mavze"
            aria-invalid={Boolean(errors.address)}
            {...form.register("address")}
          />
        </Field>
        <Field label="Telefon (mijozlar uchun)" htmlFor="studio-phone" error={errors.phone_number?.message}>
          <Input id="studio-phone" inputMode="tel" placeholder="+998 90 123 45 67" aria-invalid={Boolean(errors.phone_number)} {...form.register("phone_number")} />
        </Field>
        <Field label="Portfolio joyi, GB (Google Drive, standart 1 GB)" htmlFor="studio-quota" error={errors.portfolio_quota_gb?.message}>
          <Input id="studio-quota" type="number" step="0.5" min={0} aria-invalid={Boolean(errors.portfolio_quota_gb)} {...form.register("portfolio_quota_gb", { valueAsNumber: true })} />
        </Field>
        <Field label="Tavsif (ommaviy profilda ko'rinadi)" htmlFor="studio-description" error={errors.description?.message}>
          <textarea
            id="studio-description"
            rows={3}
            maxLength={2000}
            className="w-full rounded-xl border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:border-brand"
            {...form.register("description")}
          />
        </Field>
        <Field
          label="Mas'ul shaxs"
          htmlFor="studio-owner"
          error={errors.responsible_user_id?.message}
          hint="Faqat 'Studiya' rolidagi faol foydalanuvchilar"
        >
          <Controller
            control={form.control}
            name="responsible_user_id"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange} onOpenChange={(o) => !o && setOwnerSearch("")}>
                <SelectTrigger id="studio-owner" className="w-full" aria-invalid={Boolean(errors.responsible_user_id)}>
                  <SelectValue placeholder={owners.isPending ? "Yuklanmoqda…" : "Tanlang"} />
                </SelectTrigger>
                <SelectContent>
                  <div className="p-1.5">
                    <input
                      value={ownerSearch}
                      onChange={(e) => setOwnerSearch(e.target.value)}
                      onKeyDown={(e) => e.stopPropagation()}
                      placeholder="Qidirish…"
                      aria-label="Mas'ul shaxsni qidirish"
                      className="h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-brand"
                    />
                  </div>
                  {owners.error ? (
                    <p className="px-3 py-2 text-sm text-destructive">
                      Ro&apos;yxatni olish uchun &quot;Foydalanuvchilarni ko&apos;rish&quot; ruxsati kerak
                    </p>
                  ) : (
                    ownerOptions.length === 0 && (
                      <p className="px-3 py-2 text-sm text-muted-foreground">STUDIO rolidagi faol foydalanuvchi topilmadi</p>
                    )
                  )}
                  {ownerOptions.map((o) => (
                    <SelectItem key={o.id} value={o.id}>
                      {o.full_name} · <span className="text-muted-foreground tabular-nums">{o.pinfl_masked}</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </Field>
        <Controller
          control={form.control}
          name="is_active"
          render={({ field }) => (
            <label className="flex items-center justify-between rounded-2xl bg-muted/60 px-4 py-3 text-sm font-semibold">
              Faol holatda
              <Switch checked={field.value} onCheckedChange={field.onChange} />
            </label>
          )}
        />
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
