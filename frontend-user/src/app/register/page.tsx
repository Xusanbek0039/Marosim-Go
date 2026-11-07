"use client";

import { LockKeyholeIcon, PhoneIcon } from "lucide-react";
import { motion, useAnimationControls } from "motion/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { AuthFrame } from "@/components/auth-frame";
import { Button, Field, Input } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useLogin } from "@/lib/auth";

const shake = { x: [0, -8, 8, -6, 6, 0], transition: { duration: 0.4 } };

export default function RegisterPage() {
  const router = useRouter();
  const login = useLogin();
  const controls = useAnimationControls();
  const [values, setValues] = useState({ phone_number: "", password: "", password_confirm: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);
  const set = (key: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (!values.phone_number.trim()) local.phone_number = "Telefon raqamni kiriting";
    if (values.password.length < 10) local.password = "Parol kamida 10 ta belgidan iborat bo'lsin";
    if (values.password !== values.password_confirm) local.password_confirm = "Parollar mos kelmadi";
    setErrors(local);
    if (Object.keys(local).length) {
      controls.start(shake);
      return;
    }
    setPending(true);
    try {
      // Web sign-up creates the account only; we then sign in to get the httpOnly session.
      await api.post("/auth/register/", values, { noRefresh: true });
      await login.mutateAsync({ phone_number: values.phone_number, password: values.password });
      toast.success("Hisob yaratildi. Xush kelibsiz!");
      router.replace("/profile");
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors);
      else toast.error(err instanceof ApiError ? err.message : "Ro'yxatdan o'tib bo'lmadi");
      controls.start(shake);
    } finally {
      setPending(false);
    }
  };

  return (
    <AuthFrame subtitle="Yangi hisob yaratish">
      <motion.form animate={controls} onSubmit={submit} noValidate className="flex flex-col gap-4">
        <Field label="Telefon raqam" htmlFor="phone_number" error={errors.phone_number} hint="Masalan: +998 90 123 45 67">
          <div className="relative">
            <PhoneIcon className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="phone_number"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              autoFocus
              className="pl-10 tabular-nums"
              aria-invalid={Boolean(errors.phone_number)}
              value={values.phone_number}
              onChange={set("phone_number")}
            />
          </div>
        </Field>
        <Field label="Parol" htmlFor="password" error={errors.password} hint="Kamida 10 ta belgi">
          <div className="relative">
            <LockKeyholeIcon className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              className="pl-10"
              aria-invalid={Boolean(errors.password)}
              value={values.password}
              onChange={set("password")}
            />
          </div>
        </Field>
        <Field label="Parolni tasdiqlang" htmlFor="password_confirm" error={errors.password_confirm}>
          <Input
            id="password_confirm"
            type="password"
            autoComplete="new-password"
            aria-invalid={Boolean(errors.password_confirm)}
            value={values.password_confirm}
            onChange={set("password_confirm")}
          />
        </Field>
        <Button type="submit" size="lg" loading={pending} className="w-full">
          Ro&apos;yxatdan o&apos;tish
        </Button>
        <p className="text-center text-sm text-muted-foreground">
          Hisobingiz bormi?{" "}
          <Link href="/login" className="font-semibold text-brand hover:underline dark:text-cyan-300">
            Kirish
          </Link>
        </p>
      </motion.form>
    </AuthFrame>
  );
}
