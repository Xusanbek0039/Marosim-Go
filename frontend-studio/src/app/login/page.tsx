"use client";

import { EyeIcon, EyeOffIcon, LockKeyholeIcon } from "lucide-react";
import { motion, useAnimationControls } from "motion/react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";

import { AuthFrame } from "@/components/auth-frame";
import { PhoneInput } from "@/components/phone-input";
import { Button, Field, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { APP } from "@/lib/app-config";
import { safeNext, useLogin, WrongAppError } from "@/lib/auth";

const shake = { x: [0, -8, 8, -6, 6, 0], transition: { duration: 0.4 } };

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const login = useLogin();
  const controls = useAnimationControls();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!phone.trim() || !password) {
      setError("Telefon raqam va parolni kiriting.");
      controls.start(shake);
      return;
    }
    login.mutate(
      { phone_number: phone, password },
      {
        onSuccess: (user) => {
          toast.success(user.first_name ? `Xush kelibsiz, ${user.first_name}!` : "Xush kelibsiz!");
          router.replace(safeNext(params.get("next")));
        },
        onError: (err) => {
          setError(err instanceof WrongAppError ? APP.wrongAppMessage : err instanceof ApiError ? err.message : "Kirishda xatolik.");
          setPassword("");
          controls.start(shake);
        },
      },
    );
  };

  return (
    <motion.form animate={controls} onSubmit={submit} noValidate className="flex flex-col gap-4">
      <Field label="Telefon raqam" htmlFor="phone_number">
        <PhoneInput id="phone_number" autoComplete="username" autoFocus value={phone} onChange={setPhone} />
      </Field>
      <Field label="Parol" htmlFor="password">
        <div className="relative">
          <LockKeyholeIcon className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="password"
            type={show ? "text" : "password"}
            autoComplete="current-password"
            className="pr-11 pl-10"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            aria-label={show ? "Parolni yashirish" : "Parolni ko'rsatish"}
            className="absolute top-1/2 right-2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted"
          >
            {show ? <EyeOffIcon className="size-4" /> : <EyeIcon className="size-4" />}
          </button>
        </div>
      </Field>
      {error && (
        <p role="alert" className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm font-medium text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
      <Button type="submit" size="lg" loading={login.isPending} className="w-full">
        Kirish
      </Button>
      {APP.allowRegister && (
        <p className="text-center text-sm text-muted-foreground">
          Hisobingiz yo&apos;qmi?{" "}
          <Link href="/register" className="font-semibold text-brand hover:underline dark:text-cyan-300">
            Ro&apos;yxatdan o&apos;ting
          </Link>
        </p>
      )}
    </motion.form>
  );
}

export default function LoginPage() {
  return (
    <AuthFrame subtitle={APP.tagline}>
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </AuthFrame>
  );
}
