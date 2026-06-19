import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Dumbbell, Plus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../shared/api/client";
import { Badge } from "../shared/ui/badge";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { Field, Input, Select, Textarea } from "../shared/ui/form";
import { PageHeader } from "../shared/ui/page";
import { SectionTitle } from "../shared/ui/section";
import { EmptyState, ErrorState, SkeletonGrid } from "../shared/ui/state";

const schema = z.object({
  name: z.string().min(2, "Введите название"),
  primary_muscle_group_id: z.string().min(1, "Выберите группу"),
  equipment_id: z.string().optional(),
  tracking_type: z.string().min(1),
  description: z.string().optional(),
  instructions: z.string().optional(),
});

const trackingOptions = [
  ["weight_reps", "Вес + повторы"],
  ["reps_only", "Повторы"],
  ["time", "Время"],
  ["distance_time", "Дистанция + время"],
  ["bodyweight_added", "Свой вес + доп. вес"],
  ["bodyweight_assisted", "Свой вес с поддержкой"],
  ["calories", "Калории"],
  ["custom", "Другое"],
] as const;

export function ExercisesPage() {
  const [search, setSearch] = useState("");
  const [muscleGroup, setMuscleGroup] = useState("");
  const [equipmentFilter, setEquipmentFilter] = useState("");
  const [trackingType, setTrackingType] = useState("");
  const queryClient = useQueryClient();
  const exercises = useQuery({
    queryKey: ["exercises", search, muscleGroup, equipmentFilter, trackingType],
    queryFn: () =>
      api.exercises({
        search,
        muscle_group: muscleGroup,
        equipment: equipmentFilter,
        tracking_type: trackingType,
        limit: 50,
      }).then((response) => response.data),
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
      <PageHeader title="Exercises" description="Каталог упражнений с поиском, фильтрами и пользовательскими движениями." />
      <div className="grid gap-4 xl:grid-cols-[1.3fr_.8fr]">
        <section className="grid content-start gap-3">
          <Card className="bg-ink text-white">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-black uppercase text-[#9fd5ba]">Exercise library</p>
                <h2 className="text-2xl font-black">Каталог движений</h2>
                <p className="mt-1 text-sm font-medium text-white/65">Быстрый поиск, фильтры backend и создание своих упражнений.</p>
              </div>
              <div className="grid h-12 w-12 place-items-center rounded-lg bg-white/10 text-[#9fd5ba]">
                <Activity className="h-6 w-6" aria-hidden />
              </div>
            </div>
          </Card>
          <Card>
            <div className="grid gap-3 md:grid-cols-4">
              <Field label="Поиск">
                <Input placeholder="Жим, присед..." value={search} onChange={(e) => setSearch(e.target.value)} />
              </Field>
              <Field label="Мышцы">
                <Select value={muscleGroup} onChange={(event) => setMuscleGroup(event.target.value)}>
                  <option value="">Все группы</option>
                  {muscles.data?.map((m) => <option key={m.id} value={m.code}>{m.name}</option>)}
                </Select>
              </Field>
              <Field label="Оборудование">
                <Select value={equipmentFilter} onChange={(event) => setEquipmentFilter(event.target.value)}>
                  <option value="">Любое</option>
                  {equipment.data?.map((e) => <option key={e.id} value={e.code}>{e.name}</option>)}
                </Select>
              </Field>
              <Field label="Тип">
                <Select value={trackingType} onChange={(event) => setTrackingType(event.target.value)}>
                  <option value="">Любой</option>
                  {trackingOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </Select>
              </Field>
            </div>
          </Card>
          {exercises.isLoading ? <SkeletonGrid count={6} /> : null}
          {exercises.isError ? <ErrorState error={exercises.error} onRetry={() => exercises.refetch()} /> : null}
          {exercises.data?.length === 0 ? <EmptyState title="Ничего не найдено" /> : null}
          <div className="grid gap-3 sm:grid-cols-2">
            {exercises.data?.map((item) => (
              <Card key={item.id} className="transition hover:-translate-y-0.5 hover:shadow-lift">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 gap-3">
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-mint text-action">
                      <Dumbbell className="h-5 w-5" aria-hidden />
                    </div>
                    <div className="min-w-0">
                      <h2 className="truncate font-black">{item.name}</h2>
                      <p className="text-sm font-medium text-muted">{item.primary_muscle_group?.name ?? "Без группы"} · {item.equipment?.name ?? "Без оборудования"}</p>
                    </div>
                  </div>
                  <Badge>{item.tracking_type}</Badge>
                </div>
                {item.description ? <p className="mt-3 text-sm font-medium leading-6 text-muted">{item.description}</p> : null}
              </Card>
            ))}
          </div>
        </section>
        <Card>
          <SectionTitle eyebrow="Create" title="Новое упражнение" description="Добавьте своё движение, если его нет в системном каталоге." />
          <form className="grid gap-3" onSubmit={form.handleSubmit((values) => create.mutate(values))}>
            <Field label="Название" error={form.formState.errors.name?.message}><Input {...form.register("name")} /></Field>
            <Field label="Мышечная группа" error={form.formState.errors.primary_muscle_group_id?.message}>
              <Select {...form.register("primary_muscle_group_id")}><option value="">Выберите</option>{muscles.data?.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</Select>
            </Field>
            <Field label="Оборудование">
              <Select {...form.register("equipment_id")}><option value="">Без оборудования</option>{equipment.data?.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}</Select>
            </Field>
            <Field label="Тип трекинга">
              <Select {...form.register("tracking_type")}>
                {trackingOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </Select>
            </Field>
            <Field label="Описание"><Textarea {...form.register("description")} /></Field>
            {create.isSuccess ? <p className="rounded-md bg-mint p-3 text-sm font-bold text-action">Упражнение добавлено в каталог.</p> : null}
            <Button disabled={!form.formState.isValid} isLoading={create.isPending}><Plus className="h-4 w-4" aria-hidden />Создать</Button>
          </form>
        </Card>
      </div>
    </>
  );
}
