import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../shared/api/client";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { Field, Input, Select } from "../shared/ui/form";
import { PageHeader } from "../shared/ui/page";
import { ErrorState, SkeletonGrid } from "../shared/ui/state";

const profileSchema = z.object({
  display_name: z.string().optional(),
  birth_date: z.string().optional(),
  sex: z.string().optional(),
  height_cm: z.coerce.number().min(1).optional(),
  experience_level: z.string().optional(),
  timezone: z.string().optional(),
});

export function ProfilePage() {
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: () => api.me().then((r) => r.data) });
  const goals = useQuery({ queryKey: ["goals"], queryFn: () => api.goals().then((r) => r.data) });
  const form = useForm<z.infer<typeof profileSchema>>({ resolver: zodResolver(profileSchema), mode: "onChange" });
  const save = useMutation({
    mutationFn: (values: z.infer<typeof profileSchema>) => api.updateMe(values),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });
  const createGoal = useMutation({
    mutationFn: () => api.createGoal({ goal_type: "maintenance", calorie_target: 2200, protein_target_g: 130, fat_target_g: 70, carbs_target_g: 250, workouts_per_week: 3 }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
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
            <h2 className="mb-3 text-lg font-bold">Данные профиля</h2>
            <form className="grid gap-3" onSubmit={form.handleSubmit((values) => save.mutate(values))}>
              <Field label="Имя"><Input {...form.register("display_name")} /></Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Дата рождения"><Input type="date" {...form.register("birth_date")} /></Field>
                <Field label="Рост, см"><Input type="number" step="0.1" {...form.register("height_cm")} /></Field>
                <Field label="Пол"><Select {...form.register("sex")}><option value="">Не указан</option><option value="male">Мужской</option><option value="female">Женский</option><option value="other">Другое</option></Select></Field>
                <Field label="Опыт"><Select {...form.register("experience_level")}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></Select></Field>
              </div>
              <Field label="Timezone"><Input placeholder="Asia/Almaty" {...form.register("timezone")} /></Field>
              <Button isLoading={save.isPending}><Save className="h-4 w-4" aria-hidden />Сохранить</Button>
            </form>
          </Card>
          <Card>
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-lg font-bold">Цели</h2>
              <Button variant="secondary" isLoading={createGoal.isPending} onClick={() => createGoal.mutate()}>Добавить</Button>
            </div>
            <div className="grid gap-2">
              {goals.data?.map((goal) => (
                <div key={String(goal.id)} className="rounded-md border border-line p-3 text-sm">
                  <p className="font-semibold">{String(goal.goal_type)}</p>
                  <p className="text-muted">{String(goal.calorie_target)} ккал · {String(goal.workouts_per_week)} трен./нед.</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      ) : null}
    </>
  );
}
