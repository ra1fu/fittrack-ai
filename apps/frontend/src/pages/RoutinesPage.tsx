import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Dumbbell, Layers3, Plus, Save, Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../shared/api/client";
import type { Exercise, Routine, RoutineDay, RoutineExercise } from "../shared/api/types";
import { Badge } from "../shared/ui/badge";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { Field, Input, Select, Textarea } from "../shared/ui/form";
import { PageHeader } from "../shared/ui/page";
import { SectionTitle } from "../shared/ui/section";
import { EmptyState, ErrorState, SkeletonGrid } from "../shared/ui/state";

const schema = z.object({ name: z.string().min(2), description: z.string().optional(), color: z.string().optional() });

const weekdayOptions = [
  { value: "", label: "Без привязки" },
  { value: "1", label: "Понедельник" },
  { value: "2", label: "Вторник" },
  { value: "3", label: "Среда" },
  { value: "4", label: "Четверг" },
  { value: "5", label: "Пятница" },
  { value: "6", label: "Суббота" },
  { value: "7", label: "Воскресенье" },
];

function weekdayLabel(value: number | null) {
  return weekdayOptions.find((option) => option.value === String(value ?? ""))?.label ?? "Без привязки";
}

function nextPosition(items: Array<{ position: number }>) {
  return items.reduce((max, item) => Math.max(max, item.position), 0) + 1;
}

function optionalInt(value: string) {
  return value === "" ? null : Number(value);
}

function optionalDecimal(value: string) {
  return value === "" ? null : value;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function AddRoutineDayForm({ routine }: { routine: Routine }) {
  const queryClient = useQueryClient();
  const suggestedPosition = nextPosition(routine.days);
  const [values, setValues] = useState({
    name: `День ${suggestedPosition}`,
    position: String(suggestedPosition),
    planned_weekday: "",
  });
  const create = useMutation({
    mutationFn: () =>
      api.createRoutineDay(routine.id, {
        name: values.name.trim(),
        position: Number(values.position),
        planned_weekday: optionalInt(values.planned_weekday),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["routines"] });
      setValues({
        name: `День ${suggestedPosition + 1}`,
        position: String(suggestedPosition + 1),
        planned_weekday: "",
      });
    },
  });

  return (
    <form
      className="grid gap-2 rounded-md border border-dashed border-[#cfc8bb] bg-white/70 p-3"
      onSubmit={(event) => {
        event.preventDefault();
        create.mutate();
      }}
    >
      <div className="grid gap-2 md:grid-cols-[1fr_120px_180px]">
        <Field label="Новый день">
          <Input value={values.name} onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))} />
        </Field>
        <Field label="Позиция">
          <Input
            min="1"
            type="number"
            value={values.position}
            onChange={(event) => setValues((current) => ({ ...current, position: event.target.value }))}
          />
        </Field>
        <Field label="День недели">
          <Select
            value={values.planned_weekday}
            onChange={(event) => setValues((current) => ({ ...current, planned_weekday: event.target.value }))}
          >
            {weekdayOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </Select>
        </Field>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          disabled={!values.name.trim() || Number(values.position) < 1}
          isLoading={create.isPending}
          type="submit"
          variant="secondary"
        >
          <Plus className="h-4 w-4" aria-hidden />
          Добавить день
        </Button>
        {create.error ? (
          <span className="text-sm font-bold text-coral">
            {create.error instanceof Error ? create.error.message : "Не удалось добавить день"}
          </span>
        ) : null}
      </div>
    </form>
  );
}

function RoutineDayEditor({ day }: { day: RoutineDay }) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState({
    name: day.name,
    position: String(day.position),
    planned_weekday: String(day.planned_weekday ?? ""),
  });
  const update = useMutation({
    mutationFn: () =>
      api.updateRoutineDay(day.id, {
        name: values.name.trim(),
        position: Number(values.position),
        planned_weekday: optionalInt(values.planned_weekday),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["routines"] }),
  });
  const remove = useMutation({
    mutationFn: () => api.deleteRoutineDay(day.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["routines"] }),
  });

  return (
    <form
      className="grid gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        update.mutate();
      }}
    >
      <div className="grid gap-2 md:grid-cols-[1fr_120px_180px_auto]">
        <Field label="Название дня">
          <Input value={values.name} onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))} />
        </Field>
        <Field label="Позиция">
          <Input
            min="1"
            type="number"
            value={values.position}
            onChange={(event) => setValues((current) => ({ ...current, position: event.target.value }))}
          />
        </Field>
        <Field label="День недели">
          <Select
            value={values.planned_weekday}
            onChange={(event) => setValues((current) => ({ ...current, planned_weekday: event.target.value }))}
          >
            {weekdayOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </Select>
        </Field>
        <div className="flex items-end gap-2">
          <Button
            disabled={!values.name.trim() || Number(values.position) < 1}
            isLoading={update.isPending}
            type="submit"
            variant="secondary"
          >
            <Save className="h-4 w-4" aria-hidden />
            День
          </Button>
          <Button aria-label="Удалить день" isLoading={remove.isPending} onClick={() => remove.mutate()} type="button" variant="danger">
            <Trash2 className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      </div>
      {update.error || remove.error ? (
        <p className="text-sm font-bold text-coral">
          {errorMessage(update.error ?? remove.error, "Не удалось изменить день")}
        </p>
      ) : null}
    </form>
  );
}

function AddRoutineExerciseForm({ day, exercises }: { day: RoutineDay; exercises: Exercise[] }) {
  const queryClient = useQueryClient();
  const suggestedPosition = nextPosition(day.exercises);
  const [values, setValues] = useState({
    exercise_id: "",
    position: String(suggestedPosition),
    planned_sets: "3",
    rep_min: "8",
    rep_max: "12",
    target_weight: "",
    rest_seconds: "90",
    notes: "",
  });
  const create = useMutation({
    mutationFn: () =>
      api.createRoutineExercise(day.id, {
        exercise_id: values.exercise_id,
        position: Number(values.position),
        planned_sets: Number(values.planned_sets),
        rep_min: optionalInt(values.rep_min),
        rep_max: optionalInt(values.rep_max),
        target_weight: optionalDecimal(values.target_weight),
        rest_seconds: optionalInt(values.rest_seconds),
        notes: values.notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["routines"] });
      setValues({
        exercise_id: "",
        position: String(suggestedPosition + 1),
        planned_sets: "3",
        rep_min: "8",
        rep_max: "12",
        target_weight: "",
        rest_seconds: "90",
        notes: "",
      });
    },
  });

  return (
    <form
      className="grid gap-2 rounded-md bg-[#fbfaf6] p-3"
      onSubmit={(event) => {
        event.preventDefault();
        create.mutate();
      }}
    >
      <div className="grid gap-2 lg:grid-cols-[1.4fr_90px_90px_90px_110px_110px]">
        <Field label="Упражнение">
          <Select value={values.exercise_id} onChange={(event) => setValues((current) => ({ ...current, exercise_id: event.target.value }))}>
            <option value="">Выберите из каталога</option>
            {exercises.map((exercise) => <option key={exercise.id} value={exercise.id}>{exercise.name}</option>)}
          </Select>
        </Field>
        <Field label="Позиция">
          <Input
            min="1"
            type="number"
            value={values.position}
            onChange={(event) => setValues((current) => ({ ...current, position: event.target.value }))}
          />
        </Field>
        <Field label="Подходы">
          <Input
            min="1"
            max="20"
            type="number"
            value={values.planned_sets}
            onChange={(event) => setValues((current) => ({ ...current, planned_sets: event.target.value }))}
          />
        </Field>
        <Field label="Повт. от">
          <Input
            min="1"
            type="number"
            value={values.rep_min}
            onChange={(event) => setValues((current) => ({ ...current, rep_min: event.target.value }))}
          />
        </Field>
        <Field label="Повт. до">
          <Input
            min="1"
            type="number"
            value={values.rep_max}
            onChange={(event) => setValues((current) => ({ ...current, rep_max: event.target.value }))}
          />
        </Field>
        <Field label="Вес, кг">
          <Input
            min="0"
            step="0.25"
            type="number"
            value={values.target_weight}
            onChange={(event) => setValues((current) => ({ ...current, target_weight: event.target.value }))}
          />
        </Field>
      </div>
      <div className="grid gap-2 md:grid-cols-[140px_1fr_auto]">
        <Field label="Отдых, сек">
          <Input
            min="0"
            type="number"
            value={values.rest_seconds}
            onChange={(event) => setValues((current) => ({ ...current, rest_seconds: event.target.value }))}
          />
        </Field>
        <Field label="Заметка">
          <Input value={values.notes} onChange={(event) => setValues((current) => ({ ...current, notes: event.target.value }))} />
        </Field>
        <div className="flex items-end">
          <Button
            disabled={!values.exercise_id || Number(values.position) < 1 || Number(values.planned_sets) < 1}
            isLoading={create.isPending}
            type="submit"
            variant="secondary"
          >
            <Plus className="h-4 w-4" aria-hidden />
            Добавить
          </Button>
        </div>
      </div>
      {create.error ? (
        <p className="text-sm font-bold text-coral">
          {create.error instanceof Error ? create.error.message : "Не удалось добавить упражнение"}
        </p>
      ) : null}
    </form>
  );
}

function RoutineExerciseEditor({
  exercise,
  exerciseName,
}: {
  exercise: RoutineExercise;
  exerciseName: string;
}) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState({
    position: String(exercise.position),
    planned_sets: String(exercise.planned_sets),
    rep_min: String(exercise.rep_min ?? ""),
    rep_max: String(exercise.rep_max ?? ""),
    target_weight: String(exercise.target_weight ?? ""),
    rest_seconds: String(exercise.rest_seconds ?? ""),
    notes: exercise.notes ?? "",
  });
  const update = useMutation({
    mutationFn: () =>
      api.updateRoutineExercise(exercise.id, {
        exercise_id: exercise.exercise_id,
        position: Number(values.position),
        planned_sets: Number(values.planned_sets),
        rep_min: optionalInt(values.rep_min),
        rep_max: optionalInt(values.rep_max),
        target_weight: optionalDecimal(values.target_weight),
        rest_seconds: optionalInt(values.rest_seconds),
        notes: values.notes,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["routines"] }),
  });
  const remove = useMutation({
    mutationFn: () => api.deleteRoutineExercise(exercise.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["routines"] }),
  });

  return (
    <form
      className="grid gap-2 rounded-md border border-line bg-white p-3"
      onSubmit={(event) => {
        event.preventDefault();
        update.mutate();
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-mint text-action">
            <Dumbbell className="h-4 w-4" aria-hidden />
          </div>
          <p className="truncate font-black">{exercise.position}. {exerciseName}</p>
        </div>
        <Badge>{exercise.planned_sets} подхода</Badge>
      </div>
      <div className="grid gap-2 lg:grid-cols-[90px_90px_90px_90px_110px_110px_auto]">
        <Field label="Позиция">
          <Input
            min="1"
            type="number"
            value={values.position}
            onChange={(event) => setValues((current) => ({ ...current, position: event.target.value }))}
          />
        </Field>
        <Field label="Подходы">
          <Input
            min="1"
            max="20"
            type="number"
            value={values.planned_sets}
            onChange={(event) => setValues((current) => ({ ...current, planned_sets: event.target.value }))}
          />
        </Field>
        <Field label="Повт. от">
          <Input
            min="1"
            type="number"
            value={values.rep_min}
            onChange={(event) => setValues((current) => ({ ...current, rep_min: event.target.value }))}
          />
        </Field>
        <Field label="Повт. до">
          <Input
            min="1"
            type="number"
            value={values.rep_max}
            onChange={(event) => setValues((current) => ({ ...current, rep_max: event.target.value }))}
          />
        </Field>
        <Field label="Вес, кг">
          <Input
            min="0"
            step="0.25"
            type="number"
            value={values.target_weight}
            onChange={(event) => setValues((current) => ({ ...current, target_weight: event.target.value }))}
          />
        </Field>
        <Field label="Отдых, сек">
          <Input
            min="0"
            type="number"
            value={values.rest_seconds}
            onChange={(event) => setValues((current) => ({ ...current, rest_seconds: event.target.value }))}
          />
        </Field>
        <div className="flex items-end gap-2">
          <Button
            aria-label="Сохранить упражнение"
            disabled={Number(values.position) < 1 || Number(values.planned_sets) < 1}
            isLoading={update.isPending}
            type="submit"
            variant="secondary"
          >
            <Save className="h-4 w-4" aria-hidden />
          </Button>
          <Button aria-label="Удалить упражнение" isLoading={remove.isPending} onClick={() => remove.mutate()} type="button" variant="danger">
            <Trash2 className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      </div>
      <Field label="Заметка">
        <Input value={values.notes} onChange={(event) => setValues((current) => ({ ...current, notes: event.target.value }))} />
      </Field>
      {update.error || remove.error ? (
        <p className="text-sm font-bold text-coral">
          {errorMessage(update.error ?? remove.error, "Не удалось изменить упражнение")}
        </p>
      ) : null}
    </form>
  );
}

function RoutineBuilderCard({ routine, exercises }: { routine: Routine; exercises: Exercise[] }) {
  const exerciseNameById = new Map(exercises.map((exercise) => [exercise.id, exercise.name]));
  const days = [...routine.days].sort((a, b) => a.position - b.position);

  return (
    <Card className="transition hover:shadow-lift">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-black">{routine.name}</h2>
          <p className="text-sm font-medium text-muted">{routine.description || "Без описания"}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone="success">{routine.days.length} дн.</Badge>
          <Badge>{routine.is_active ? "active" : "paused"}</Badge>
        </div>
      </div>
      <div className="mt-4 grid gap-3">
        {days.length === 0 ? (
          <div className="rounded-md border border-dashed border-[#cfc8bb] bg-white/70 p-4 text-sm font-bold text-muted">
            В программе пока нет дней. Добавьте первый день ниже.
          </div>
        ) : null}
        {days.map((day) => (
          <div key={day.id} className="grid gap-3 rounded-lg border border-line bg-[#f6f3ec] p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="grid h-9 w-9 place-items-center rounded-md bg-white text-action">
                  <CalendarDays className="h-4 w-4" aria-hidden />
                </div>
                <div>
                  <p className="font-black">{day.position}. {day.name}</p>
                  <p className="text-xs font-bold text-muted">{weekdayLabel(day.planned_weekday)} · {day.exercises.length} упр.</p>
                </div>
              </div>
            </div>
            <RoutineDayEditor day={day} />
            <div className="grid gap-2">
              {[...day.exercises].sort((a, b) => a.position - b.position).map((exercise) => (
                <RoutineExerciseEditor
                  key={exercise.id}
                  exercise={exercise}
                  exerciseName={exerciseNameById.get(exercise.exercise_id) ?? "Упражнение из каталога"}
                />
              ))}
            </div>
            <AddRoutineExerciseForm day={day} exercises={exercises} />
          </div>
        ))}
        <AddRoutineDayForm routine={routine} />
      </div>
    </Card>
  );
}

export function RoutinesPage() {
  const queryClient = useQueryClient();
  const routines = useQuery({ queryKey: ["routines"], queryFn: () => api.routines().then((r) => r.data) });
  const exercises = useQuery({
    queryKey: ["exercises", "routine-builder"],
    queryFn: () => api.exercises({ limit: 100 }).then((response) => response.data),
  });
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), mode: "onChange" });
  const create = useMutation({
    mutationFn: (values: z.infer<typeof schema>) => api.createRoutine(values),
    onSuccess: () => {
      form.reset();
      queryClient.invalidateQueries({ queryKey: ["routines"] });
    },
  });
  return (
    <>
      <PageHeader title="Routines" description="Программы тренировок, дни и плановые упражнения." />
      <div className="grid gap-4 lg:grid-cols-[1.2fr_.8fr]">
        <section className="grid content-start gap-3">
          <Card className="bg-ink text-white">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-black uppercase text-[#9fd5ba]">Training plans</p>
                <h2 className="text-2xl font-black">Программы</h2>
                <p className="mt-1 text-sm font-medium text-white/65">Структурируйте неделю по дням и упражнениям.</p>
              </div>
              <Layers3 className="h-8 w-8 text-[#9fd5ba]" aria-hidden />
            </div>
          </Card>
          {routines.isLoading ? <SkeletonGrid count={4} /> : null}
          {routines.isError ? <ErrorState error={routines.error} onRetry={() => routines.refetch()} /> : null}
          {routines.data?.length === 0 ? <EmptyState title="Программ пока нет" /> : null}
          <div className="grid gap-3">
            {routines.data?.map((routine) => (
              <RoutineBuilderCard key={routine.id} routine={routine} exercises={exercises.data ?? []} />
            ))}
          </div>
        </section>
        <Card>
          <SectionTitle eyebrow="Create" title="Новая программа" description="Задайте основу, дни и упражнения можно будет расширять." />
          <form className="grid gap-3" onSubmit={form.handleSubmit((values) => create.mutate(values))}>
            <Field label="Название"><Input {...form.register("name")} /></Field>
            <Field label="Цвет"><Input placeholder="#1f7a5a" {...form.register("color")} /></Field>
            <Field label="Описание"><Textarea {...form.register("description")} /></Field>
            {create.isSuccess ? <p className="rounded-md bg-mint p-3 text-sm font-bold text-action">Программа создана.</p> : null}
            <Button disabled={!form.formState.isValid} isLoading={create.isPending}><Plus className="h-4 w-4" aria-hidden />Создать</Button>
          </form>
        </Card>
      </div>
    </>
  );
}
