import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Layers3, Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../shared/api/client";
import { Badge } from "../shared/ui/badge";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { Field, Input, Textarea } from "../shared/ui/form";
import { PageHeader } from "../shared/ui/page";
import { SectionTitle } from "../shared/ui/section";
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
              <Card key={routine.id} className="transition hover:shadow-lift">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="truncate text-lg font-black">{routine.name}</h2>
                    <p className="text-sm font-medium text-muted">{routine.description || "Без описания"}</p>
                  </div>
                  <Badge tone="success">{routine.days.length} дн.</Badge>
                </div>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {routine.days.map((day) => (
                    <div key={day.id} className="rounded-md border border-line bg-[#fbfaf6] p-3 text-sm">
                      <span className="font-bold">{day.position}. {day.name}</span>
                      <span className="font-medium text-muted"> · {day.exercises.length} упр.</span>
                    </div>
                  ))}
                </div>
              </Card>
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
