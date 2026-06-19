import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../shared/api/client";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { Field, Input, Textarea } from "../shared/ui/form";
import { PageHeader } from "../shared/ui/page";
import { EmptyState, ErrorState, SkeletonGrid } from "../shared/ui/state";

const schema = z.object({ name: z.string().min(2), description: z.string().optional(), color: z.string().optional() });

export function RoutinesPage() {
  const queryClient = useQueryClient();
  const routines = useQuery({ queryKey: ["routines"], queryFn: () => api.routines().then((r) => r.data) });
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
        <section>
          {routines.isLoading ? <SkeletonGrid count={4} /> : null}
          {routines.isError ? <ErrorState error={routines.error} onRetry={() => routines.refetch()} /> : null}
          {routines.data?.length === 0 ? <EmptyState title="Программ пока нет" /> : null}
          <div className="grid gap-3">
            {routines.data?.map((routine) => (
              <Card key={routine.id}>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-bold">{routine.name}</h2>
                    <p className="text-sm text-muted">{routine.description || "Без описания"}</p>
                  </div>
                  <span className="rounded-md bg-[#e1f1e8] px-2 py-1 text-xs font-semibold text-action">{routine.days.length} дн.</span>
                </div>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {routine.days.map((day) => (
                    <div key={day.id} className="rounded-md border border-line p-2 text-sm">
                      <span className="font-semibold">{day.position}. {day.name}</span>
                      <span className="text-muted"> · {day.exercises.length} упр.</span>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </section>
        <Card>
          <h2 className="mb-3 text-lg font-bold">Новая программа</h2>
          <form className="grid gap-3" onSubmit={form.handleSubmit((values) => create.mutate(values))}>
            <Field label="Название"><Input {...form.register("name")} /></Field>
            <Field label="Цвет"><Input placeholder="#1f7a5a" {...form.register("color")} /></Field>
            <Field label="Описание"><Textarea {...form.register("description")} /></Field>
            <Button disabled={!form.formState.isValid} isLoading={create.isPending}><Plus className="h-4 w-4" aria-hidden />Создать</Button>
          </form>
        </Card>
      </div>
    </>
  );
}
