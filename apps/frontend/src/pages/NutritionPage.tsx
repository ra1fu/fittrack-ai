import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Apple, Coffee, Drumstick, Moon, Plus, Search, Soup, Trash2 } from "lucide-react";
import { ReactNode } from "react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../shared/api/client";
import { moneylessNumber, todayIso } from "../shared/lib/utils";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { Field, Input } from "../shared/ui/form";
import { PageHeader } from "../shared/ui/page";
import { EmptyState, ErrorState, SkeletonGrid } from "../shared/ui/state";

const mealTypes = [
  ["breakfast", "Завтрак", Coffee],
  ["lunch", "Обед", Soup],
  ["dinner", "Ужин", Moon],
  ["snack", "Перекус", Apple],
] as const;

const foodSchema = z.object({
  name: z.string().min(2, "Введите название"),
  calories_per_100g: z.coerce.number().min(0),
  protein_per_100g: z.coerce.number().min(0),
  fat_per_100g: z.coerce.number().min(0),
  carbs_per_100g: z.coerce.number().min(0),
});

export function NutritionPage() {
  const [date, setDate] = useState(todayIso());
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();
  const day = useQuery({
    queryKey: ["nutrition-day", date],
    queryFn: () => api.nutritionDay(date).then((response) => response.data),
  });
  const foods = useQuery({
    queryKey: ["foods", search],
    queryFn: () => api.foods({ search, limit: 10 }).then((response) => response.data),
  });
  const createMeal = useMutation({
    mutationFn: (meal_type: string) => api.createMeal({ meal_date: date, meal_type }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["nutrition-day", date] }),
  });
  const addItem = useMutation({
    mutationFn: ({ mealId, foodId }: { mealId: string; foodId: string }) =>
      api.addMealItem(mealId, { food_id: foodId, weight_g: 100 }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["nutrition-day", date] }),
  });
  const deleteItem = useMutation({
    mutationFn: (id: string) => api.deleteMealItem(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["nutrition-day", date] }),
  });

  const firstMeal = day.data?.meals[0];

  return (
    <>
      <PageHeader
        title="Nutrition"
        description="Дневник питания с пересчётом калорий и БЖУ."
        action={<Input aria-label="Дата" type="date" value={date} onChange={(event) => setDate(event.target.value)} />}
      />

      {day.isLoading ? <SkeletonGrid count={4} /> : null}
      {day.isError ? <ErrorState error={day.error} onRetry={() => day.refetch()} /> : null}
      {day.data ? (
        <div className="grid gap-4 xl:grid-cols-[1.4fr_.8fr]">
          <Card className="overflow-hidden bg-ink p-0 text-white xl:col-span-2">
            <div className="grid gap-4 p-5 sm:grid-cols-[1fr_2fr] sm:p-6">
              <div>
                <p className="text-xs font-black uppercase text-[#9fd5ba]">Daily intake</p>
                <p className="sr-only">Калории</p>
                <h2 className="mt-1 text-2xl font-black">{moneylessNumber(day.data.totals.calories)} ккал</h2>
                <p className="mt-1 text-sm font-medium text-white/65">{date}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <Metric icon={<Drumstick className="h-4 w-4" />} label="Белки" value={day.data.totals.protein} />
                <Metric icon={<Apple className="h-4 w-4" />} label="Жиры" value={day.data.totals.fat} />
                <Metric icon={<Soup className="h-4 w-4" />} label="Углеводы" value={day.data.totals.carbs} />
              </div>
            </div>
          </Card>

          <section className="grid gap-4">
            {mealTypes.map(([type, label, Icon]) => {
              const meal = day.data.meals.find((item) => item.meal_type === type);
              return (
                <Card key={type} className="transition hover:shadow-lift">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div className="grid h-10 w-10 place-items-center rounded-md bg-mint text-action">
                        <Icon className="h-5 w-5" aria-hidden />
                      </div>
                      <div>
                        <h2 className="text-lg font-black">{label}</h2>
                        <p className="text-xs font-semibold text-muted">
                          {meal ? `${meal.items.length} позиций · ${moneylessNumber(meal.totals.calories)} ккал` : "Приём ещё не создан"}
                        </p>
                      </div>
                    </div>
                    {!meal ? (
                      <Button variant="secondary" isLoading={createMeal.isPending} onClick={() => createMeal.mutate(type)}>
                        <Plus className="h-4 w-4" aria-hidden />
                        Создать
                      </Button>
                    ) : null}
                  </div>
                  {meal?.items.length ? (
                    <div className="grid gap-2">
                      {meal.items.map((item) => (
                        <div key={item.id} className="flex items-center justify-between gap-3 rounded-md border border-line bg-[#fbfaf6] p-3">
                          <div className="min-w-0">
                            <p className="truncate font-bold">{item.display_name_snapshot}</p>
                            <p className="text-sm font-medium text-muted">{moneylessNumber(item.weight_g)} г · {moneylessNumber(item.calories_snapshot)} ккал</p>
                          </div>
                          <Button aria-label="Удалить продукт" variant="ghost" onClick={() => deleteItem.mutate(item.id)}>
                            <Trash2 className="h-4 w-4" aria-hidden />
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState title="Пока пусто" text="Добавьте продукт из поиска справа." />
                  )}
                </Card>
              );
            })}
          </section>

          <aside className="grid content-start gap-4">
            <CreateFoodCard />
            <Card>
              <div className="mb-3 flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-md bg-oat text-steel">
                  <Search className="h-5 w-5" aria-hidden />
                </div>
                <div>
                  <p className="text-xs font-black uppercase text-action">Catalog</p>
                  <h2 className="text-lg font-black">Поиск продукта</h2>
                </div>
              </div>
              <Input placeholder="Например, творог" value={search} onChange={(event) => setSearch(event.target.value)} />
              <div className="mt-3 grid gap-2">
                {foods.data?.map((food) => (
                  <button
                    key={food.id}
                    className="rounded-md border border-line bg-[#fbfaf6] p-3 text-left transition hover:border-[#c9c4b8] hover:bg-white disabled:opacity-50"
                    disabled={!firstMeal}
                    onClick={() => firstMeal && addItem.mutate({ mealId: firstMeal.id, foodId: food.id })}
                  >
                    <span className="block font-bold">{food.name}</span>
                    <span className="text-sm font-medium text-muted">{moneylessNumber(food.calories_per_100g)} ккал / 100 г</span>
                  </button>
                ))}
                {foods.data?.length === 0 ? (
                  <p className="rounded-md border border-dashed border-line p-3 text-sm font-medium text-muted">Ничего не найдено.</p>
                ) : null}
              </div>
            </Card>
          </aside>
        </div>
      ) : null}
    </>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/10 p-3">
      <div className="mb-2 flex items-center gap-2 text-[#9fd5ba]">
        {icon}
        <p className="text-xs font-black uppercase">{label}</p>
      </div>
      <p className="text-xl font-black">{moneylessNumber(value)} г</p>
    </div>
  );
}

function CreateFoodCard() {
  const queryClient = useQueryClient();
  const form = useForm<z.infer<typeof foodSchema>>({ resolver: zodResolver(foodSchema), mode: "onChange" });
  const mutation = useMutation({
    mutationFn: (values: z.infer<typeof foodSchema>) => api.createFood(values),
    onSuccess: () => {
      form.reset();
      queryClient.invalidateQueries({ queryKey: ["foods"] });
    },
  });
  return (
    <Card>
      <div className="mb-3 flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-md bg-[#f4dfd6] text-coral">
          <Plus className="h-5 w-5" aria-hidden />
        </div>
        <div>
          <p className="text-xs font-black uppercase text-action">Custom food</p>
          <h2 className="text-lg font-black">Новый продукт</h2>
        </div>
      </div>
      <form className="grid gap-3" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <Field label="Название" error={form.formState.errors.name?.message}><Input {...form.register("name")} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Ккал"><Input type="number" step="0.01" {...form.register("calories_per_100g")} /></Field>
          <Field label="Белки"><Input type="number" step="0.01" {...form.register("protein_per_100g")} /></Field>
          <Field label="Жиры"><Input type="number" step="0.01" {...form.register("fat_per_100g")} /></Field>
          <Field label="Углеводы"><Input type="number" step="0.01" {...form.register("carbs_per_100g")} /></Field>
        </div>
        <Button type="submit" disabled={!form.formState.isValid} isLoading={mutation.isPending}>Создать</Button>
      </form>
    </Card>
  );
}
