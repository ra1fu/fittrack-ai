import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Activity, Camera, CheckCircle2, Dumbbell, ShieldCheck, Sparkles } from "lucide-react";
import { ReactNode } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";
import { ApiError } from "../../shared/api/errors";
import { api } from "../../shared/api/client";
import { Button } from "../../shared/ui/button";
import { Card } from "../../shared/ui/card";
import { Field, Input } from "../../shared/ui/form";
import { useAuthStore } from "./store";

const schema = z.object({
  email: z.string().email("Введите корректный email"),
  password: z.string().min(8, "Минимум 8 символов"),
  accepted_terms: z.boolean().optional(),
  accepted_privacy: z.boolean().optional(),
});

type AuthValues = z.infer<typeof schema>;

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isValid },
  } = useForm<AuthValues>({
    resolver: zodResolver(schema),
    mode: "onChange",
    defaultValues: { email: "", password: "", accepted_terms: false, accepted_privacy: false },
  });

  const mutation = useMutation({
    mutationFn: async (values: AuthValues) => {
      if (mode === "login") return api.login({ email: values.email, password: values.password });
      await api.register({
        email: values.email,
        password: values.password,
        accepted_terms: Boolean(values.accepted_terms),
        accepted_privacy: Boolean(values.accepted_privacy),
      });
      return api.login({ email: values.email, password: values.password });
    },
    onSuccess: (response) => {
      setSession({ access: response.data.access, refresh: response.data.refresh }, response.data.user);
      navigate("/dashboard", { replace: true });
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        Object.entries(error.fields).forEach(([field, value]) => {
          setError(field as keyof AuthValues, {
            message: Array.isArray(value) ? value.join(", ") : String(value),
          });
        });
      }
    },
  });

  return (
    <main className="dashboard-grid grid min-h-screen bg-canvas px-4 py-8 lg:grid-cols-[1fr_520px] lg:px-8">
      <section className="hidden min-h-[calc(100vh-4rem)] items-center lg:flex">
        <div className="max-w-2xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-lg border border-line bg-white px-3 py-2 text-sm font-bold text-action shadow-soft">
            <Sparkles className="h-4 w-4" aria-hidden />
            AI-assisted daily fitness tracking
          </div>
          <h1 className="max-w-xl text-5xl font-black leading-tight text-ink">
            FitTrack AI
          </h1>
          <p className="mt-4 max-w-lg text-lg font-medium leading-8 text-muted">
            Питание, тренировки, программы и прогресс в одном спокойном рабочем интерфейсе.
          </p>
          <div className="mt-8 grid max-w-xl gap-3 sm:grid-cols-3">
            <Feature icon={<Camera className="h-5 w-5" />} title="Photo AI" text="Фото еды в редактируемый draft" />
            <Feature icon={<Activity className="h-5 w-5" />} title="Progress" text="Калории, БЖУ и тренды" />
            <Feature icon={<ShieldCheck className="h-5 w-5" />} title="Secure" text="JWT flow с refresh токеном" />
          </div>
        </div>
      </section>

      <section className="grid min-h-[calc(100vh-4rem)] place-items-center">
        <Card className="w-full max-w-md p-5 shadow-lift">
          <div className="mb-6 flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-lg bg-ink text-white shadow-soft">
              <Dumbbell className="h-6 w-6" aria-hidden />
            </div>
            <div>
              <h1 className="text-xl font-black">FitTrack AI</h1>
              <p className="text-sm font-medium text-muted">{mode === "login" ? "Вход в дневник" : "Создание аккаунта"}</p>
            </div>
          </div>

          <form className="grid gap-4" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
          <Field label="Email" error={errors.email?.message}>
            <Input autoComplete="email" type="email" {...register("email")} />
          </Field>
          <Field label="Пароль" error={errors.password?.message}>
            <Input autoComplete={mode === "login" ? "current-password" : "new-password"} type="password" {...register("password")} />
          </Field>

          {mode === "register" ? (
            <div className="grid gap-2 text-sm text-muted">
              <label className="flex min-h-11 items-center gap-3 rounded-md border border-line bg-[#fbfaf6] px-3">
                <input className="h-4 w-4 accent-action" type="checkbox" {...register("accepted_terms")} />
                Принимаю условия использования
              </label>
              <label className="flex min-h-11 items-center gap-3 rounded-md border border-line bg-[#fbfaf6] px-3">
                <input className="h-4 w-4 accent-action" type="checkbox" {...register("accepted_privacy")} />
                Принимаю политику конфиденциальности
              </label>
            </div>
          ) : null}

          {mutation.error ? (
            <div className="rounded-md border border-coral/30 bg-[#fff6f2] p-3 text-sm text-coral">
              {mutation.error instanceof Error ? mutation.error.message : "Ошибка авторизации"}
            </div>
          ) : null}

          <Button type="submit" isLoading={mutation.isPending} disabled={!isValid}>
            {mode === "login" ? "Войти" : "Зарегистрироваться"}
          </Button>
          </form>

          <p className="mt-4 text-center text-sm text-muted">
            {mode === "login" ? "Нет аккаунта?" : "Уже есть аккаунт?"}{" "}
            <Link className="font-bold text-action hover:text-[#116744]" to={mode === "login" ? "/register" : "/login"}>
              {mode === "login" ? "Регистрация" : "Войти"}
            </Link>
          </p>
          <div className="mt-5 flex items-center justify-center gap-2 rounded-md bg-mint px-3 py-2 text-xs font-bold text-action">
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            Данные синхронизируются с вашим backend API
          </div>
        </Card>
      </section>
    </main>
  );
}

function Feature({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-lg border border-line bg-white p-4 shadow-soft">
      <div className="mb-3 grid h-10 w-10 place-items-center rounded-md bg-mint text-action">{icon}</div>
      <p className="font-black text-ink">{title}</p>
      <p className="mt-1 text-sm leading-5 text-muted">{text}</p>
    </div>
  );
}
