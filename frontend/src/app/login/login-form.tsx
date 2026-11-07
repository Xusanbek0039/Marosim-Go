"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { EyeIcon, EyeOffIcon, Loader2Icon, LockKeyholeIcon, PhoneIcon } from "lucide-react";
import { motion, useAnimationControls } from "motion/react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { LogoMark, Wordmark } from "@/components/brand/logo";
import { Field } from "@/components/common/form";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { isPanelRole, useLogin, useLogout } from "@/features/auth/hooks";
import { ApiError } from "@/lib/api/client";
import { phoneSchema } from "@/lib/phone";
import { fadeUp, listContainer, shake } from "@/motion/tokens";

const schema = z.object({
  phone_number: phoneSchema,
  password: z.string().min(1, "Parolni kiriting"),
});
type Values = z.infer<typeof schema>;

/** Only same-site relative paths are accepted as a post-login redirect (no open redirect). */
function safeNext(raw: string | null) {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.startsWith("/\\")) return "/dashboard";
  return raw;
}

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const login = useLogin();
  const logout = useLogout();
  const controls = useAnimationControls();
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { phone_number: "", password: "" } });
  const { errors } = form.formState;

  const onInvalid = () => controls.start(shake);

  const onSubmit = form.handleSubmit((values) => {
    setFormError(null);
    login.mutate(values, {
      onSuccess: ({ user }) => {
        if (!isPanelRole(user.role)) {
          logout.mutate();
          setFormError("Bu panel faqat administratorlar uchun.");
          controls.start(shake);
          return;
        }
        toast.success(`Xush kelibsiz, ${user.first_name}!`);
        router.replace(safeNext(params.get("next")));
      },
      onError: (error) => {
        setFormError(error instanceof ApiError ? error.message : "Kirishda xatolik yuz berdi.");
        form.resetField("password");
        controls.start(shake);
      },
    });
  }, onInvalid);

  return (
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden p-4">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -top-40 -left-40 size-[520px] rounded-full bg-blue-600/25 blur-3xl"
        animate={{ x: [0, 40, 0], y: [0, 30, 0] }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -right-32 -bottom-40 size-[460px] rounded-full bg-cyan-500/20 blur-3xl"
        animate={{ x: [0, -30, 0], y: [0, -40, 0] }}
        transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
      />

      <motion.div animate={controls} className="relative w-full max-w-[440px]">
        <motion.form
          onSubmit={onSubmit}
          noValidate
          variants={listContainer(0.07)}
          initial="initial"
          animate="animate"
          className="glass-strong flex flex-col gap-5 rounded-[32px] p-7 shadow-[0_0_90px_-30px_rgb(6_182_212/0.55)] sm:p-9"
        >
          <motion.div variants={fadeUp} className="flex flex-col items-center gap-4 pb-2 text-center">
            <LogoMark className="h-16" />
            <Wordmark className="h-7" />
            <p className="text-sm text-muted-foreground">Super Admin boshqaruv paneliga kirish</p>
          </motion.div>

          <motion.div variants={fadeUp}>
            <Field label="Telefon raqam" htmlFor="phone_number" error={errors.phone_number?.message}>
              <div className="relative">
                <PhoneIcon className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="phone_number"
                  type="tel"
                  inputMode="tel"
                  autoComplete="username"
                  autoFocus
                  placeholder="+998 90 123 45 67"
                  className="pl-10 tabular-nums"
                  aria-invalid={Boolean(errors.phone_number)}
                  {...form.register("phone_number")}
                />
              </div>
            </Field>
          </motion.div>

          <motion.div variants={fadeUp}>
            <Field label="Parol" htmlFor="password" error={errors.password?.message}>
              <div className="relative">
                <LockKeyholeIcon className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••••"
                  className="pr-11 pl-10"
                  aria-invalid={Boolean(errors.password)}
                  {...form.register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute top-1/2 right-2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-label={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                >
                  {showPassword ? <EyeOffIcon className="size-4" /> : <EyeIcon className="size-4" />}
                </button>
              </div>
            </Field>
          </motion.div>

          {formError && (
            <motion.p
              role="alert"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm font-medium text-red-700 dark:text-red-300"
            >
              {formError}
            </motion.p>
          )}

          <motion.div variants={fadeUp}>
            <Button type="submit" size="lg" className="h-12 w-full text-[15px]" disabled={login.isPending}>
              {login.isPending && <Loader2Icon className="animate-spin" />}
              Kirish
            </Button>
          </motion.div>
        </motion.form>
      </motion.div>
    </div>
  );
}
