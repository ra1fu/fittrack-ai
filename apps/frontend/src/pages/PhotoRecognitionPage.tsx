import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { api } from "../shared/api/client";
import { todayIso } from "../shared/lib/utils";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { Field, Input, Select } from "../shared/ui/form";
import { PageHeader } from "../shared/ui/page";
import { EmptyState, ErrorState, SkeletonGrid } from "../shared/ui/state";

export function PhotoRecognitionPage() {
  const [file, setFile] = useState<File | null>(null);
  const [mealDate, setMealDate] = useState(todayIso());
  const [mealType, setMealType] = useState("breakfast");
  const queryClient = useQueryClient();
  const recognitions = useQuery({
    queryKey: ["photo-recognitions"],
    queryFn: () => api.photoRecognitions().then((response) => response.data),
  });
  const upload = useMutation({
    mutationFn: () => {
      const body = new FormData();
      if (file) body.append("image", file);
      return api.photoUpload(body);
    },
    onSuccess: () => {
      setFile(null);
      queryClient.invalidateQueries({ queryKey: ["photo-recognitions"] });
    },
  });
  const confirm = useMutation({
    mutationFn: (id: string) => api.confirmRecognition(id, { meal_date: mealDate, meal_type: mealType }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["photo-recognitions"] }),
  });

  return (
    <>
      <PageHeader title="Photo AI" description="Черновик распознавания можно проверить и подтвердить в дневник питания." />
      <div className="grid gap-4 lg:grid-cols-[.8fr_1.2fr]">
        <Card>
          <h2 className="mb-3 text-lg font-bold">Загрузить фото</h2>
          <div className="grid gap-3">
            <Field label="Фото еды">
              <Input accept="image/jpeg,image/png,image/webp" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            </Field>
            <Button disabled={!file} isLoading={upload.isPending} onClick={() => upload.mutate()}>
              <Camera className="h-4 w-4" aria-hidden />
              Отправить
            </Button>
            {upload.error ? <p className="text-sm text-coral">{upload.error instanceof Error ? upload.error.message : "Ошибка загрузки"}</p> : null}
          </div>
        </Card>

        <Card>
          <div className="mb-3 grid gap-3 sm:grid-cols-2">
            <Field label="Дата"><Input type="date" value={mealDate} onChange={(event) => setMealDate(event.target.value)} /></Field>
            <Field label="Приём пищи">
              <Select value={mealType} onChange={(event) => setMealType(event.target.value)}>
                <option value="breakfast">Завтрак</option>
                <option value="lunch">Обед</option>
                <option value="dinner">Ужин</option>
                <option value="snack">Перекус</option>
              </Select>
            </Field>
          </div>
          {recognitions.isLoading ? <SkeletonGrid count={2} /> : null}
          {recognitions.isError ? <ErrorState error={recognitions.error} onRetry={() => recognitions.refetch()} /> : null}
          {recognitions.data?.length === 0 ? <EmptyState title="Нет распознаваний" text="Загрузите фото, чтобы получить редактируемый draft." /> : null}
          <div className="grid gap-3">
            {recognitions.data?.map((item) => (
              <div key={String(item.id)} className="rounded-md border border-line p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-semibold">Статус: {String(item.status)}</p>
                    {item.error_message ? <p className="text-sm text-coral">{String(item.error_message)}</p> : null}
                  </div>
                  {!item.confirmed_meal_id ? (
                    <Button isLoading={confirm.isPending} onClick={() => confirm.mutate(String(item.id))}>
                      <CheckCircle2 className="h-4 w-4" aria-hidden />
                      Confirm
                    </Button>
                  ) : (
                    <span className="rounded-md bg-[#e1f1e8] px-3 py-2 text-sm font-semibold text-action">В дневнике</span>
                  )}
                </div>
                <div className="mt-3 grid gap-2">
                  {(Array.isArray(item.items) ? item.items : []).map((food: Record<string, unknown>) => (
                    <div key={String(food.id)} className="rounded-md bg-[#f5f3ec] p-2 text-sm">
                      <span className="font-semibold">{String(food.corrected_name ?? food.ai_name)}</span>
                      <span className="text-muted"> · {String(food.corrected_weight_g ?? food.ai_weight_g)} г</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}
