import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Bot, CalendarCheck, Camera, CheckCircle2, Save, Sparkles, Trash2, UploadCloud } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../shared/api/client";
import { todayIso } from "../shared/lib/utils";
import { Badge } from "../shared/ui/badge";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { Field, Input, Select } from "../shared/ui/form";
import { PageHeader } from "../shared/ui/page";
import { SectionTitle } from "../shared/ui/section";
import { EmptyState, ErrorState, SkeletonGrid } from "../shared/ui/state";

type RecognitionFood = Record<string, unknown>;

function textValue(value: unknown, fallback = "") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function totalsValue(food: RecognitionFood, key: string) {
  const totals = food.totals;
  if (!totals || typeof totals !== "object") return "0";
  return textValue((totals as Record<string, unknown>)[key], "0");
}

function RecognitionFoodEditor({ food, editable }: { food: RecognitionFood; editable: boolean }) {
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [values, setValues] = useState({
    corrected_name: textValue(food.corrected_name ?? food.ai_name),
    corrected_weight_g: textValue(food.corrected_weight_g ?? food.ai_weight_g, "100"),
    corrected_calories_per_100g: textValue(food.corrected_calories_per_100g ?? food.ai_calories_per_100g, "0"),
    corrected_protein_per_100g: textValue(food.corrected_protein_per_100g ?? food.ai_protein_per_100g, "0"),
    corrected_fat_per_100g: textValue(food.corrected_fat_per_100g ?? food.ai_fat_per_100g, "0"),
    corrected_carbs_per_100g: textValue(food.corrected_carbs_per_100g ?? food.ai_carbs_per_100g, "0"),
  });

  const save = useMutation({
    mutationFn: () =>
      api.updateRecognitionItem(String(food.id), {
        corrected_name: values.corrected_name.trim(),
        corrected_weight_g: values.corrected_weight_g,
        corrected_calories_per_100g: values.corrected_calories_per_100g,
        corrected_protein_per_100g: values.corrected_protein_per_100g,
        corrected_fat_per_100g: values.corrected_fat_per_100g,
        corrected_carbs_per_100g: values.corrected_carbs_per_100g,
      }),
    onSuccess: () => {
      setSaved(true);
      queryClient.invalidateQueries({ queryKey: ["photo-recognitions"] });
    },
  });
  const remove = useMutation({
    mutationFn: () => api.deleteRecognitionItem(String(food.id)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["photo-recognitions"] }),
  });

  const setField = (field: keyof typeof values, value: string) => {
    setSaved(false);
    setValues((current) => ({ ...current, [field]: value }));
  };

  return (
    <form
      className="grid gap-3 rounded-md border border-line bg-white p-3 text-sm"
      onSubmit={(event) => {
        event.preventDefault();
        if (editable) save.mutate();
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-black uppercase text-muted">Позиция #{textValue(food.position, "1")}</p>
          <p className="font-black">{values.corrected_name || "Без названия"}</p>
          <p className="mt-1 text-xs font-bold text-muted">AI confidence: {textValue(food.ai_confidence, "0")}</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs font-black text-steel">
          <span className="rounded-md bg-oat px-2 py-1">{totalsValue(food, "calories")} ккал</span>
          <span className="rounded-md bg-oat px-2 py-1">Б {totalsValue(food, "protein")}</span>
          <span className="rounded-md bg-oat px-2 py-1">Ж {totalsValue(food, "fat")}</span>
          <span className="rounded-md bg-oat px-2 py-1">У {totalsValue(food, "carbs")}</span>
        </div>
      </div>
      <div className="grid gap-2 md:grid-cols-[1.3fr_.7fr]">
        <Field label="Название">
          <Input
            disabled={!editable}
            value={values.corrected_name}
            onChange={(event) => setField("corrected_name", event.target.value)}
          />
        </Field>
        <Field label="Вес, г">
          <Input
            disabled={!editable}
            min="0.01"
            step="0.01"
            type="number"
            value={values.corrected_weight_g}
            onChange={(event) => setField("corrected_weight_g", event.target.value)}
          />
        </Field>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <Field label="Ккал / 100 г">
          <Input
            disabled={!editable}
            min="0"
            step="0.01"
            type="number"
            value={values.corrected_calories_per_100g}
            onChange={(event) => setField("corrected_calories_per_100g", event.target.value)}
          />
        </Field>
        <Field label="Белки / 100 г">
          <Input
            disabled={!editable}
            min="0"
            step="0.01"
            type="number"
            value={values.corrected_protein_per_100g}
            onChange={(event) => setField("corrected_protein_per_100g", event.target.value)}
          />
        </Field>
        <Field label="Жиры / 100 г">
          <Input
            disabled={!editable}
            min="0"
            step="0.01"
            type="number"
            value={values.corrected_fat_per_100g}
            onChange={(event) => setField("corrected_fat_per_100g", event.target.value)}
          />
        </Field>
        <Field label="Углеводы / 100 г">
          <Input
            disabled={!editable}
            min="0"
            step="0.01"
            type="number"
            value={values.corrected_carbs_per_100g}
            onChange={(event) => setField("corrected_carbs_per_100g", event.target.value)}
          />
        </Field>
      </div>
      {editable ? (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            disabled={!values.corrected_name.trim() || Number(values.corrected_weight_g) <= 0}
            isLoading={save.isPending}
            type="submit"
            variant="secondary"
          >
            <Save className="h-4 w-4" aria-hidden />
            Сохранить правки
          </Button>
          {saved ? <span className="text-sm font-bold text-action">Правки сохранены.</span> : null}
          {save.error ? (
            <span className="text-sm font-bold text-coral">
              {save.error instanceof Error ? save.error.message : "Не удалось сохранить позицию"}
            </span>
          ) : null}
          <Button
            aria-label="Удалить позицию распознавания"
            isLoading={remove.isPending}
            onClick={() => remove.mutate()}
            type="button"
            variant="danger"
          >
            <Trash2 className="h-4 w-4" aria-hidden />
            Удалить
          </Button>
          {remove.error ? (
            <span className="text-sm font-bold text-coral">
              {remove.error instanceof Error ? remove.error.message : "Не удалось удалить позицию"}
            </span>
          ) : null}
        </div>
      ) : null}
    </form>
  );
}

export function PhotoRecognitionPage() {
  const navigate = useNavigate();
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["photo-recognitions"] });
      navigate(`/nutrition?date=${mealDate}`);
    },
  });

  return (
    <>
      <PageHeader title="Photo AI" description="Черновик распознавания можно проверить и подтвердить в дневник питания." />
      <div className="grid gap-4 lg:grid-cols-[.85fr_1.15fr]">
        <div className="grid content-start gap-4">
          <Card className="overflow-hidden p-0">
            <div className="bg-ink p-5 text-white">
              <div className="mb-4 grid h-12 w-12 place-items-center rounded-lg bg-white/10 text-[#9fd5ba]">
                <Bot className="h-6 w-6" aria-hidden />
              </div>
              <h2 className="text-2xl font-black">Photo AI</h2>
              <p className="mt-2 text-sm font-medium leading-6 text-white/70">
                AI делает только черновик. Проверь вес, калории и БЖУ перед сохранением.
              </p>
            </div>
            <div className="grid gap-3 p-4">
              <div className="flex items-start gap-3 rounded-md bg-mint p-3 text-sm font-medium text-action">
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                Фото удаляется backend после обработки; в дневник сохраняются только позиции.
              </div>
            </div>
          </Card>

          <Card>
            <SectionTitle eyebrow="Step 1" title="Загрузить фото" description="JPEG, PNG или WEBP. Лучше снимать сверху при хорошем свете." />
          <div className="grid gap-3">
            <Field label="Фото еды">
              <Input accept="image/jpeg,image/png,image/webp" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            </Field>
            <Button disabled={!file} isLoading={upload.isPending} onClick={() => upload.mutate()}>
              <UploadCloud className="h-4 w-4" aria-hidden />
              Отправить на анализ
            </Button>
            {upload.error ? <p className="text-sm text-coral">{upload.error instanceof Error ? upload.error.message : "Ошибка загрузки"}</p> : null}
            {upload.isSuccess ? <p className="text-sm font-bold text-action">Фото обработано. Проверьте результат справа.</p> : null}
          </div>
          </Card>

          <Card>
            <SectionTitle eyebrow="Step 2" title="Куда сохранить" description="Эти параметры применяются при подтверждении draft." />
            <div className="grid gap-3">
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
          </Card>
        </div>

        <Card>
          <SectionTitle eyebrow="Results" title="Черновики распознавания" description="Подтверждайте только после проверки состава." />
          {recognitions.isLoading ? <SkeletonGrid count={2} /> : null}
          {recognitions.isError ? <ErrorState error={recognitions.error} onRetry={() => recognitions.refetch()} /> : null}
          {recognitions.data?.length === 0 ? <EmptyState title="Нет распознаваний" text="Загрузите фото, чтобы получить редактируемый draft." /> : null}
          <div className="grid gap-3">
            {recognitions.data?.map((item) => (
              <div key={String(item.id)} className="rounded-lg border border-line bg-[#fbfaf6] p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-start gap-3">
                    <div className="grid h-10 w-10 place-items-center rounded-md bg-white text-action">
                      {item.status === "failed" ? <AlertTriangle className="h-5 w-5 text-coral" aria-hidden /> : <Camera className="h-5 w-5" aria-hidden />}
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-black">Распознавание</p>
                        <Badge tone={item.status === "failed" ? "danger" : item.confirmed_meal_id ? "success" : "warning"}>
                          {String(item.status)}
                        </Badge>
                      </div>
                      {item.error_message ? <p className="mt-1 text-sm font-medium text-coral">{String(item.error_message)}</p> : null}
                    </div>
                  </div>
                  {!item.confirmed_meal_id ? (
                    item.status === "draft" ? (
                      <Button isLoading={confirm.isPending} onClick={() => confirm.mutate(String(item.id))}>
                        <CheckCircle2 className="h-4 w-4" aria-hidden />
                        Сохранить
                      </Button>
                    ) : null
                  ) : (
                    <Badge tone="success"><CalendarCheck className="mr-1 h-3.5 w-3.5" aria-hidden />В дневнике</Badge>
                  )}
                </div>
                <div className="mt-3 grid gap-2">
                  {(Array.isArray(item.items) ? item.items : []).map((food: Record<string, unknown>) => (
                    <RecognitionFoodEditor key={String(food.id)} food={food} editable={item.status === "draft"} />
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
