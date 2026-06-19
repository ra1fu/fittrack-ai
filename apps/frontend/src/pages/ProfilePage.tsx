import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Save, Target, UserRound } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../shared/api/client";
import type { UserGoal } from "../shared/api/types";
import { todayIso } from "../shared/lib/utils";
import { Badge } from "../shared/ui/badge";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { Field, Input, Select } from "../shared/ui/form";
import { PageHeader } from "../shared/ui/page";
import { SectionTitle } from "../shared/ui/section";
import { ErrorState, SkeletonGrid } from "../shared/ui/state";

const profileSchema = z.object({
  display_name: z.string().optional(),
  birth_date: z.string().optional(),
  sex: z.string().optional(),
  height_cm: z.coerce.number().min(1).optional(),
  experience_level: z.string().optional(),
  timezone: z.string().optional(),
});

const optionalNumber = (min = 0) =>
  z.preprocess(
    (value) => (value === "" || value === null ? undefined : value),
    z.coerce.number().min(min).optional(),
  );

const goalSchema = z.object({
  goal_type: z.string().min(1),
  calorie_target: optionalNumber(1),
  protein_target_g: optionalNumber(0),
  fat_target_g: optionalNumber(0),
  carbs_target_g: optionalNumber(0),
  workouts_per_week: optionalNumber(0),
  target_weight_min: optionalNumber(1),
  target_weight_max: optionalNumber(1),
  active_from: z.string().min(1, "Укажите дату начала"),
  active_to: z.string().optional(),
});

type GoalFormValues = z.infer<typeof goalSchema>;

const goalTypeOptions = [
  ["maintenance", "Поддержание"],
  ["strength", "Сила"],
  ["muscle_gain", "Набор мышц"],
  ["gradual_weight_loss", "Снижение веса"],
  ["regularity", "Регулярность"],
  ["custom", "Своя цель"],
] as const;

function cleanGoalPayload(values: GoalFormValues) {
  return {
    ...values,
    calorie_target: values.calorie_target ?? null,
    protein_target_g: values.protein_target_g ?? null,
    fat_target_g: values.fat_target_g ?? null,
    carbs_target_g: values.carbs_target_g ?? null,
    workouts_per_week: values.workouts_per_week ?? null,
    target_weight_min: values.target_weight_min ?? null,
    target_weight_max: values.target_weight_max ?? null,
    active_to: values.active_to || null,
  };
}

function goalDefaults(goal?: UserGoal): GoalFormValues {
  return {
    goal_type: goal?.goal_type ?? "maintenance",
    calorie_target: goal?.calorie_target ?? undefined,
    protein_target_g: goal?.protein_target_g ? Number(goal.protein_target_g) : undefined,
    fat_target_g: goal?.fat_target_g ? Number(goal.fat_target_g) : undefined,
    carbs_target_g: goal?.carbs_target_g ? Number(goal.carbs_target_g) : undefined,
    workouts_per_week: goal?.workouts_per_week ?? undefined,
    target_weight_min: goal?.target_weight_min ? Number(goal.target_weight_min) : undefined,
    target_weight_max: goal?.target_weight_max ? Number(goal.target_weight_max) : undefined,
    active_from: goal?.active_from ?? todayIso(),
    active_to: goal?.active_to ?? "",
  };
}

export function ProfilePage() {
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: () => api.me().then((r) => r.data) });
  const goals = useQuery({ queryKey: ["goals"], queryFn: () => api.goals().then((r) => r.data) });
  const form = useForm<z.infer<typeof profileSchema>>({ resolver: zodResolver(profileSchema), mode: "onChange" });
  const save = useMutation({
    mutationFn: (values: z.infer<typeof profileSchema>) => api.updateMe(values),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });
  useEffect(() => {
    if (me.data?.profile) form.reset(me.data.profile as z.infer<typeof profileSchema>);
  }, [form, me.data]);

  return (
    <>
      <PageHeader title="Profile" description="Профиль, единицы измерения и цели питания." />
      {me.isLoading ? <SkeletonGrid count={2} /> : null}
      {me.isError ? <ErrorState error={me.error} onRetry={() => me.refetch()} /> : null}
      {me.data ? (
        <div className="grid gap-4 lg:grid-cols-[1fr_.8fr]">
          <Card>
            <SectionTitle
              eyebrow="Account"
              title="Данные профиля"
              description="Эти параметры помогают точнее считать цели и недельную активность."
              action={<UserRound className="h-5 w-5 text-action" aria-hidden />}
            />
            <form className="grid gap-3" onSubmit={form.handleSubmit((values) => save.mutate(values))}>
              <Field label="Имя"><Input {...form.register("display_name")} /></Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Дата рождения"><Input type="date" {...form.register("birth_date")} /></Field>
                <Field label="Рост, см"><Input type="number" step="0.1" {...form.register("height_cm")} /></Field>
                <Field label="Пол"><Select {...form.register("sex")}><option value="">Не указан</option><option value="male">Мужской</option><option value="female">Женский</option><option value="other">Другое</option></Select></Field>
                <Field label="Опыт"><Select {...form.register("experience_level")}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></Select></Field>
              </div>
              <Field label="Timezone"><Input placeholder="Asia/Almaty" {...form.register("timezone")} /></Field>
              {save.isSuccess ? <p className="rounded-md bg-mint p-3 text-sm font-bold text-action">Профиль сохранён.</p> : null}
              <Button isLoading={save.isPending}><Save className="h-4 w-4" aria-hidden />Сохранить</Button>
            </form>
          </Card>
          <Card>
            <SectionTitle
              eyebrow="Targets"
              title="Цели"
              description="Калории, БЖУ, тренировки и целевой вес с периодом активности."
              action={<Target className="h-5 w-5 text-action" aria-hidden />}
            />
            <CreateGoalForm />
            <div className="mt-4 grid gap-3">
              {goals.data?.map((goal) => (
                <GoalEditor key={goal.id} goal={goal} />
              ))}
              {goals.data?.length === 0 ? (
                <div className="rounded-md border border-dashed border-line p-4 text-sm font-medium text-muted">
                  Целей пока нет. Добавьте базовую цель для Dashboard.
                </div>
              ) : null}
            </div>
          </Card>
        </div>
      ) : null}
    </>
  );
}

function GoalFields({ form }: { form: ReturnType<typeof useForm<GoalFormValues>> }) {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Тип цели" error={form.formState.errors.goal_type?.message}>
          <Select {...form.register("goal_type")}>
            {goalTypeOptions.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </Select>
        </Field>
        <Field label="Калории / день">
          <Input min="1" type="number" {...form.register("calorie_target")} />
        </Field>
        <Field label="Белки, г">
          <Input min="0" step="0.1" type="number" {...form.register("protein_target_g")} />
        </Field>
        <Field label="Жиры, г">
          <Input min="0" step="0.1" type="number" {...form.register("fat_target_g")} />
        </Field>
        <Field label="Углеводы, г">
          <Input min="0" step="0.1" type="number" {...form.register("carbs_target_g")} />
        </Field>
        <Field label="Тренировок / нед.">
          <Input min="0" max="14" type="number" {...form.register("workouts_per_week")} />
        </Field>
        <Field label="Вес от, кг">
          <Input min="1" step="0.1" type="number" {...form.register("target_weight_min")} />
        </Field>
        <Field label="Вес до, кг">
          <Input min="1" step="0.1" type="number" {...form.register("target_weight_max")} />
        </Field>
        <Field label="Активна с" error={form.formState.errors.active_from?.message}>
          <Input type="date" {...form.register("active_from")} />
        </Field>
        <Field label="Активна до">
          <Input type="date" {...form.register("active_to")} />
        </Field>
      </div>
    </>
  );
}

function CreateGoalForm() {
  const queryClient = useQueryClient();
  const form = useForm<GoalFormValues>({
    resolver: zodResolver(goalSchema),
    mode: "onChange",
    defaultValues: goalDefaults(),
  });
  const create = useMutation({
    mutationFn: (values: GoalFormValues) => api.createGoal(cleanGoalPayload(values)),
    onSuccess: () => {
      form.reset(goalDefaults());
      queryClient.invalidateQueries({ queryKey: ["goals"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  return (
    <form
      className="grid gap-3 rounded-lg border border-line bg-[#fbfaf6] p-3"
      onSubmit={form.handleSubmit((values) => create.mutate(values))}
    >
      <GoalFields form={form} />
      {create.error ? (
        <p className="text-sm font-bold text-coral">
          {create.error instanceof Error ? create.error.message : "Не удалось создать цель"}
        </p>
      ) : null}
      {create.isSuccess ? <p className="text-sm font-bold text-action">Цель создана.</p> : null}
      <Button disabled={!form.formState.isValid} isLoading={create.isPending} type="submit">
        <Plus className="h-4 w-4" aria-hidden />
        Добавить цель
      </Button>
    </form>
  );
}

function GoalEditor({ goal }: { goal: UserGoal }) {
  const queryClient = useQueryClient();
  const form = useForm<GoalFormValues>({
    resolver: zodResolver(goalSchema),
    mode: "onChange",
    defaultValues: goalDefaults(goal),
  });
  const update = useMutation({
    mutationFn: (values: GoalFormValues) => api.updateGoal(goal.id, cleanGoalPayload(values)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["goals"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  useEffect(() => {
    form.reset(goalDefaults(goal));
  }, [form, goal]);

  return (
    <form
      className="grid gap-3 rounded-md border border-line bg-white p-3 text-sm"
      onSubmit={form.handleSubmit((values) => update.mutate(values))}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-black">{goalTypeOptions.find(([value]) => value === goal.goal_type)?.[1] ?? goal.goal_type}</p>
          <p className="text-xs font-bold text-muted">
            {goal.active_from} - {goal.active_to ?? "без окончания"}
          </p>
        </div>
        <Badge tone="success">goal</Badge>
      </div>
      <GoalFields form={form} />
      {update.error ? (
        <p className="text-sm font-bold text-coral">
          {update.error instanceof Error ? update.error.message : "Не удалось сохранить цель"}
        </p>
      ) : null}
      {update.isSuccess ? <p className="text-sm font-bold text-action">Цель сохранена.</p> : null}
      <Button disabled={!form.formState.isValid} isLoading={update.isPending} type="submit" variant="secondary">
        <Save className="h-4 w-4" aria-hidden />
        Сохранить цель
      </Button>
    </form>
  );
}
