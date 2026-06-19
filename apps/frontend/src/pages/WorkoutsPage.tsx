import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Clock3, Dumbbell, Flame, Plus, Square, Trash2, X } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../shared/api/client";
import type { Workout } from "../shared/api/types";
import { Badge } from "../shared/ui/badge";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { Field, Input, Textarea } from "../shared/ui/form";
import { PageHeader } from "../shared/ui/page";
import { SectionTitle } from "../shared/ui/section";
import { EmptyState, ErrorState, SkeletonGrid } from "../shared/ui/state";

const startSchema = z.object({ name: z.string().optional(), notes: z.string().optional() });
const setSchema = z.object({
  weight: z.coerce.number().min(0).optional(),
  repetitions: z.coerce.number().int().min(1).optional(),
});

function isWorkout(value: Workout | null): value is Workout {
  return value !== null;
}

export function WorkoutsPage({ activeOnly = false }: { activeOnly?: boolean }) {
  const queryClient = useQueryClient();
  const workouts = useQuery({
    queryKey: ["workouts", activeOnly],
    queryFn: async () =>
      activeOnly
        ? [await api.activeWorkout().then((r) => r.data)].filter(isWorkout)
        : api.workouts().then((r) => r.data),
  });
  const active = useQuery({ queryKey: ["active-workout"], queryFn: () => api.activeWorkout().then((r) => r.data) });
  const startForm = useForm<z.infer<typeof startSchema>>({ resolver: zodResolver(startSchema), mode: "onChange" });
  const start = useMutation({
    mutationFn: (values: z.infer<typeof startSchema>) => api.startWorkout(values),
    onSuccess: () => {
      startForm.reset();
      queryClient.invalidateQueries({ queryKey: ["workouts"] });
      queryClient.invalidateQueries({ queryKey: ["active-workout"] });
    },
  });
  const finish = useMutation({
    mutationFn: (id: string) => api.finishWorkout(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workouts"] });
      queryClient.invalidateQueries({ queryKey: ["active-workout"] });
    },
  });
  const cancel = useMutation({
    mutationFn: (id: string) => api.cancelWorkout(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workouts"] });
      queryClient.invalidateQueries({ queryKey: ["active-workout"] });
    },
  });

  return (
    <>
      <PageHeader title={activeOnly ? "Active Workout" : "Workouts"} description="История, активная тренировка и редактор подходов." />
      <div className="grid gap-4 xl:grid-cols-[1.3fr_.8fr]">
        <section className="grid gap-4">
          {active.data ? (
            <Card className="border-amber/50 bg-[#fffaf1]">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="grid h-11 w-11 place-items-center rounded-lg bg-[#f2e5ce] text-amber">
                    <Flame className="h-5 w-5" aria-hidden />
                  </div>
                  <div>
                    <Badge tone="warning">active</Badge>
                    <h2 className="mt-1 text-xl font-black">{active.data.name || "Активная тренировка"}</h2>
                    <p className="text-sm font-medium text-muted">Старт: {new Date(active.data.started_at).toLocaleString("ru-RU")}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button isLoading={finish.isPending} onClick={() => finish.mutate(active.data!.id)}><Check className="h-4 w-4" aria-hidden />Finish</Button>
                  <Button variant="danger" isLoading={cancel.isPending} onClick={() => cancel.mutate(active.data!.id)}><X className="h-4 w-4" aria-hidden />Cancel</Button>
                </div>
              </div>
              <div className="mt-4 grid gap-3">
                {active.data.exercises.map((exercise) => (
                  <WorkoutExerciseCard key={exercise.id} exercise={exercise} />
                ))}
                {active.data.exercises.length === 0 ? <EmptyState title="Упражнений пока нет" text="Backend создаёт упражнения из программы, если стартовать по routine day." /> : null}
              </div>
            </Card>
          ) : null}

          <SectionTitle eyebrow="History" title="Журнал тренировок" description="Последние сессии и их текущий статус." />
          {workouts.isLoading ? <SkeletonGrid count={4} /> : null}
          {workouts.isError ? <ErrorState error={workouts.error} onRetry={() => workouts.refetch()} /> : null}
          {workouts.data?.length === 0 ? <EmptyState title="Тренировок пока нет" /> : null}
          <div className="grid gap-3">
            {workouts.data?.map((workout) => (
              <Card key={workout.id} className="transition hover:shadow-lift">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="grid h-10 w-10 place-items-center rounded-md bg-mint text-action">
                      <Clock3 className="h-5 w-5" aria-hidden />
                    </div>
                    <div className="min-w-0">
                      <h2 className="truncate font-black">{workout.name || "Тренировка"}</h2>
                      <p className="text-sm font-medium text-muted">{new Date(workout.started_at).toLocaleString("ru-RU")}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap justify-end gap-2">
                    <Badge tone={workout.status === "finished" ? "success" : "neutral"}>{workout.status}</Badge>
                    <Badge>{workout.exercises.length} упр.</Badge>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </section>

        <Card>
          <SectionTitle eyebrow="Start" title="Новая тренировка" description="Начните свободную тренировку или продолжите активную." />
          <form className="grid gap-3" onSubmit={startForm.handleSubmit((values) => start.mutate(values))}>
            <Field label="Название"><Input placeholder="Верх тела" {...startForm.register("name")} /></Field>
            <Field label="Заметки"><Textarea {...startForm.register("notes")} /></Field>
            {start.isSuccess ? <p className="rounded-md bg-mint p-3 text-sm font-bold text-action">Тренировка начата.</p> : null}
            <Button isLoading={start.isPending}><Dumbbell className="h-4 w-4" aria-hidden />Начать</Button>
          </form>
        </Card>
      </div>
    </>
  );
}

function WorkoutExerciseCard({ exercise }: { exercise: { id: string; position: number; sets: Array<{ id: string; position: number; weight: string | null; repetitions: number | null; is_completed: boolean }> } }) {
  const queryClient = useQueryClient();
  const form = useForm<z.infer<typeof setSchema>>({ resolver: zodResolver(setSchema), mode: "onChange" });
  const add = useMutation({
    mutationFn: (values: z.infer<typeof setSchema>) =>
      api.addWorkoutSet(exercise.id, {
        position: exercise.sets.length + 1,
        set_type: "working",
        weight: values.weight ?? null,
        repetitions: values.repetitions ?? null,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["active-workout"] }),
  });
  const toggle = useMutation({
    mutationFn: ({ id, done }: { id: string; done: boolean }) => api.updateWorkoutSet(id, { is_completed: done }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["active-workout"] }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.deleteWorkoutSet(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["active-workout"] }),
  });
  return (
    <div className="rounded-lg border border-line bg-white p-3">
      <h3 className="font-black">Упражнение #{exercise.position}</h3>
      <div className="mt-2 grid gap-2">
        {exercise.sets.map((set) => (
          <div key={set.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-[#f5f3ec] p-2 text-sm font-medium">
            <span className="font-bold">#{set.position} · {set.weight ?? 0} кг × {set.repetitions ?? 0}</span>
            <div className="flex gap-1">
              <Button variant="ghost" aria-label="Переключить completed" onClick={() => toggle.mutate({ id: set.id, done: !set.is_completed })}>
                {set.is_completed ? <Check className="h-4 w-4" /> : <Square className="h-4 w-4" />}
              </Button>
              <Button variant="ghost" aria-label="Удалить подход" onClick={() => remove.mutate(set.id)}><Trash2 className="h-4 w-4" /></Button>
            </div>
          </div>
        ))}
      </div>
      <form className="mt-3 grid grid-cols-[1fr_1fr_auto] gap-2" onSubmit={form.handleSubmit((values) => add.mutate(values))}>
        <Input aria-label="Вес" type="number" step="0.5" placeholder="Кг" {...form.register("weight")} />
        <Input aria-label="Повторы" type="number" placeholder="Повт." {...form.register("repetitions")} />
        <Button aria-label="Добавить подход" isLoading={add.isPending}><Plus className="h-4 w-4" /></Button>
      </form>
    </div>
  );
}
