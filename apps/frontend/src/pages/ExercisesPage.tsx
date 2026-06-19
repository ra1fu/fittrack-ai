import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../shared/api/client";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { Field, Input, Select, Textarea } from "../shared/ui/form";
import { PageHeader } from "../shared/ui/page";
import { EmptyState, ErrorState, SkeletonGrid } from "../shared/ui/state";

const schema = z.object({
  name: z.string().min(2, "Введите название"),
  primary_muscle_group_id: z.string().min(1, "Выберите группу"),
  equipment_id: z.string().optional(),
  tracking_type: z.string().min(1),
  description: z.string().optional(),
  instructions: z.string().optional(),
});

export function ExercisesPage() {
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();
  const exercises = useQuery({
    queryKey: ["exercises", search],
    queryFn: () => api.exercises({ search, limit: 50 }).then((response) => response.data),
  });
  const muscles = useQuery({ queryKey: ["muscle-groups"], queryFn: () => api.muscleGroups().then((r) => r.data) });
  const equipment = useQuery({ queryKey: ["equipment"], queryFn: () => api.equipment().then((r) => r.data) });
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), mode: "onChange", defaultValues: { tracking_type: "weight_reps" } });
  const create = useMutation({
    mutationFn: (values: z.infer<typeof schema>) => api.createExercise({ ...values, equipment_id: values.equipment_id || null }),
    onSuccess: () => {
      form.reset({ tracking_type: "weight_reps" });
      queryClient.invalidateQueries({ queryKey: ["exercises"] });
    },
  });

  return (
    <>
      <PageHeader title="Exercises" description="Каталог упражнений с поиском и пользовательскими движениями." action={<Input placeholder="Поиск" value={search} onChange={(e) => setSearch(e.target.value)} />} />
      <div className="grid gap-4 xl:grid-cols-[1.3fr_.8fr]">
        <section>
          {exercises.isLoading ? <SkeletonGrid count={6} /> : null}
          {exercises.isError ? <ErrorState error={exercises.error} onRetry={() => exercises.refetch()} /> : null}
          {exercises.data?.length === 0 ? <EmptyState title="Ничего не найдено" /> : null}
          <div className="grid gap-3 sm:grid-cols-2">
            {exercises.data?.map((item) => (
              <Card key={item.id}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="font-bold">{item.name}</h2>
                    <p className="text-sm text-muted">{item.primary_muscle_group?.name ?? "Без группы"} · {item.equipment?.name ?? "Без оборудования"}</p>
                  </div>
                  <span className="rounded-md bg-[#eee9db] px-2 py-1 text-xs font-semibold">{item.tracking_type}</span>
                </div>
                {item.description ? <p className="mt-3 text-sm text-muted">{item.description}</p> : null}
              </Card>
            ))}
          </div>
        </section>
        <Card>
          <h2 className="mb-3 text-lg font-bold">Новое упражнение</h2>
          <form className="grid gap-3" onSubmit={form.handleSubmit((values) => create.mutate(values))}>
            <Field label="Название" error={form.formState.errors.name?.message}><Input {...form.register("name")} /></Field>
            <Field label="Мышечная группа" error={form.formState.errors.primary_muscle_group_id?.message}>
              <Select {...form.register("primary_muscle_group_id")}><option value="">Выберите</option>{muscles.data?.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</Select>
            </Field>
            <Field label="Оборудование">
              <Select {...form.register("equipment_id")}><option value="">Без оборудования</option>{equipment.data?.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}</Select>
            </Field>
            <Field label="Тип трекинга"><Select {...form.register("tracking_type")}><option value="weight_reps">Вес + повторы</option><option value="reps">Повторы</option><option value="duration">Время</option><option value="distance">Дистанция</option></Select></Field>
            <Field label="Описание"><Textarea {...form.register("description")} /></Field>
            <Button disabled={!form.formState.isValid} isLoading={create.isPending}><Plus className="h-4 w-4" aria-hidden />Создать</Button>
          </form>
        </Card>
      </div>
    </>
  );
}
