"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2Icon } from "lucide-react";
import { motion, useAnimationControls } from "motion/react";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Field, ImageUpload } from "@/components/common/form";
import { MotionDialog } from "@/components/motion/motion-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { adminsResource, usersResource } from "@/features/resources";
import { ApiError } from "@/lib/api/client";
import type { Admin, ManagedUser, PermissionCode } from "@/lib/api/types";
import { PHONE_HINT, optionalPhoneSchema, phoneSchema } from "@/lib/phone";
import { shake } from "@/motion/tokens";

import { PermissionsEditor } from "./permissions-editor";

export type PersonKind = "user" | "admin";

const pinfl = z
  .string()
  .transform((v) => v.replace(/[\s-]/g, ""))
  .refine((v) => v === "" || /^\d{14}$/.test(v), "JSHSHIR 14 ta raqamdan iborat bo'lishi kerak");

function buildSchema(mode: "create" | "edit") {
  return z
    .object({
      first_name: z.string().trim().min(1, "Ismni kiriting").max(100),
      last_name: z.string().trim().min(1, "Familiyani kiriting").max(100),
      phone_number: mode === "create" ? phoneSchema : optionalPhoneSchema,
      email: z.union([z.literal(""), z.string().trim().email("Email noto'g'ri")]),
      pinfl,
      password: z.string().max(128),
      address: z.string().trim().max(255),
      role: z.enum(["USER", "STUDIO", "ADMIN"]),
      is_active: z.boolean(),
      permissions: z.array(z.string()),
      profile_picture: z.custom<File | null | undefined>(),
    })
    .superRefine((v, ctx) => {
      if (mode === "create" && !v.pinfl) ctx.addIssue({ code: "custom", path: ["pinfl"], message: "JSHSHIRni kiriting" });
      if (mode === "create" && !v.password)
        ctx.addIssue({ code: "custom", path: ["password"], message: "Parolni kiriting" });
      if (v.password && v.password.length < 10)
        ctx.addIssue({ code: "custom", path: ["password"], message: "Parol kamida 10 ta belgidan iborat bo'lsin" });
    });
}
type FormValues = z.input<ReturnType<typeof buildSchema>>;

interface PersonFormDialogProps {
  kind: PersonKind;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  person?: ManagedUser | Admin | null;
}

export function PersonFormDialog({ kind, open, onOpenChange, person }: PersonFormDialogProps) {
  const mode = person ? "edit" : "create";
  const resource = kind === "admin" ? adminsResource : usersResource;
  const create = resource.useCreate();
  const update = resource.useUpdate();
  const pending = create.isPending || update.isPending;
  const controls = useAnimationControls();

  const form = useForm<FormValues>({
    resolver: zodResolver(buildSchema(mode)),
    defaultValues: blank(kind),
  });
  const { errors } = form.formState;

  useEffect(() => {
    if (!open) return;
    form.reset(
      person
        ? {
            first_name: person.first_name,
            last_name: person.last_name,
            phone_number: person.phone_number ?? "",
            email: person.email ?? "",
            pinfl: "",
            password: "",
            address: person.address ?? "",
            role: person.role === "STUDIO" ? "STUDIO" : person.role === "ADMIN" ? "ADMIN" : "USER",
            is_active: person.is_active,
            permissions: "permissions" in person ? person.permissions : [],
            profile_picture: undefined,
          }
        : blank(kind),
    );
  }, [open, person, kind, form]);

  const onSubmit = form.handleSubmit(
    (raw) => {
      const values = buildSchema(mode).parse(raw);
      const payload: Record<string, unknown> = {
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        address: values.address,
        is_active: values.is_active,
      };
      if (kind === "user") payload.role = values.role;
      if (kind === "admin") payload.permissions = values.permissions;
      if (values.phone_number && values.phone_number !== person?.phone_number) payload.phone_number = values.phone_number;
      if (values.pinfl) payload.pinfl = values.pinfl;
      if (values.password) payload.password = values.password;
      if (values.profile_picture !== undefined) payload.profile_picture = values.profile_picture;

      const done = () => {
        toast.success(mode === "create" ? "Muvaffaqiyatli qo'shildi" : "O'zgarishlar saqlandi");
        onOpenChange(false);
      };
      const fail = (error: Error) => {
        if (error instanceof ApiError) {
          const fields = error.fieldErrors;
          let mapped = false;
          for (const [key, message] of Object.entries(fields)) {
            if (key in values) {
              form.setError(key as keyof FormValues, { message });
              mapped = true;
            }
          }
          if (!mapped) toast.error(error.message);
        } else toast.error("Saqlashda xatolik yuz berdi");
        controls.start(shake);
      };

      if (person) update.mutate({ id: person.id, values: payload }, { onSuccess: done, onError: fail });
      else create.mutate(payload, { onSuccess: done, onError: fail });
    },
    () => controls.start(shake),
  );

  const title =
    mode === "create"
      ? kind === "admin"
        ? "Yangi admin"
        : "Yangi foydalanuvchi"
      : `${person?.first_name} ${person?.last_name}`;

  return (
    <MotionDialog
      open={open}
      onOpenChange={(next) => !pending && onOpenChange(next)}
      title={title}
      description={mode === "edit" ? "Ma'lumotlarni tahrirlash" : "Barcha majburiy maydonlarni to'ldiring"}
      size={kind === "admin" ? "lg" : "md"}
    >
      <motion.form animate={controls} onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        <Controller
          control={form.control}
          name="profile_picture"
          render={({ field }) => (
            <ImageUpload
              label="Profil rasmi"
              rounded="full"
              currentUrl={person?.profile_picture}
              value={field.value}
              onChange={field.onChange}
              error={errors.profile_picture?.message as string | undefined}
            />
          )}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Ism" htmlFor="first_name" error={errors.first_name?.message}>
            <Input id="first_name" aria-invalid={Boolean(errors.first_name)} {...form.register("first_name")} />
          </Field>
          <Field label="Familiya" htmlFor="last_name" error={errors.last_name?.message}>
            <Input id="last_name" aria-invalid={Boolean(errors.last_name)} {...form.register("last_name")} />
          </Field>
          <Field
            label="Telefon raqam (login)"
            htmlFor="phone_number"
            error={errors.phone_number?.message}
            hint={
              mode === "edit"
                ? person?.phone_number
                  ? "O'zgarsa barcha sessiyalar yopiladi va raqam tasdiqlanmagan deb belgilanadi"
                  : "Bu hisobda telefon yo'q — telefonsiz tizimga kira olmaydi"
                : PHONE_HINT
            }
          >
            <Input
              id="phone_number"
              type="tel"
              inputMode="tel"
              autoComplete="off"
              placeholder="+998 90 123 45 67"
              className="tabular-nums"
              aria-invalid={Boolean(errors.phone_number)}
              {...form.register("phone_number")}
            />
          </Field>
          <Field label="Email (ixtiyoriy)" htmlFor="email" error={errors.email?.message}>
            <Input id="email" type="email" autoComplete="off" aria-invalid={Boolean(errors.email)} {...form.register("email")} />
          </Field>
          <Field
            label="JSHSHIR"
            htmlFor="pinfl"
            error={errors.pinfl?.message}
            hint={mode === "edit" ? `Joriy: ${person?.pinfl_masked ?? "—"} · o'zgartirish uchun yangisini kiriting` : "14 ta raqam"}
          >
            <Input
              id="pinfl"
              inputMode="numeric"
              autoComplete="off"
              maxLength={20}
              placeholder="14 ta raqam"
              aria-invalid={Boolean(errors.pinfl)}
              className="tracking-[0.12em] tabular-nums"
              {...form.register("pinfl")}
            />
          </Field>
          <Field
            label={mode === "create" ? "Parol" : "Yangi parol"}
            htmlFor="password"
            error={errors.password?.message}
            hint={mode === "edit" ? "Bo'sh qoldirilsa o'zgarmaydi; o'zgarsa barcha sessiyalar yopiladi" : "Kamida 10 ta belgi"}
          >
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              aria-invalid={Boolean(errors.password)}
              {...form.register("password")}
            />
          </Field>
          {kind === "user" && (
            <Field label="Rol" htmlFor="role">
              <Controller
                control={form.control}
                name="role"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="role" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="USER">Foydalanuvchi</SelectItem>
                      <SelectItem value="STUDIO">Studiya mas&apos;uli</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </Field>
          )}
          <Field label="Manzil" htmlFor="address" error={errors.address?.message} className={kind === "admin" ? "sm:col-span-2" : ""}>
            <Input id="address" placeholder="Masalan: Toshkent, Chilonzor" {...form.register("address")} />
          </Field>
        </div>

        {kind === "admin" && (
          <div className="flex flex-col gap-2">
            <p className="text-[13px] font-semibold text-foreground/85">Ruxsatlar</p>
            <Controller
              control={form.control}
              name="permissions"
              render={({ field }) => (
                <PermissionsEditor value={field.value as PermissionCode[]} onChange={field.onChange} />
              )}
            />
          </div>
        )}

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

function blank(kind: PersonKind): FormValues {
  return {
    first_name: "",
    last_name: "",
    phone_number: "",
    email: "",
    pinfl: "",
    password: "",
    address: "",
    role: kind === "admin" ? "ADMIN" : "USER",
    is_active: true,
    permissions: kind === "admin" ? ["dashboard.view"] : [],
    profile_picture: undefined,
  };
}
