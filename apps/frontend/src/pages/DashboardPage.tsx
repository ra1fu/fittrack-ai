import { useQuery } from "@tanstack/react-query";
import { Beef, Camera, Dumbbell, Flame, Plus, Scale, Utensils } from "lucide-react";
import { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../shared/api/client";
import { moneylessNumber, startOfRange, todayIso } from "../shared/lib/utils";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { ErrorState, SkeletonGrid } from "../shared/ui/state";

export function DashboardPage() {
  const date = todayIso();
  const summary = useQuery({
    queryKey: ["dashboard-summary", date],
    queryFn: () => api.dashboardSummary(date).then((response) => response.data),
  });
  const trends = useQuery({
    queryKey: ["dashboard-trends", date],
    queryFn: () => api.dashboardTrends(startOfRange(14), date).then((response) => response.data),
  });

  if (summary.isLoading) return <SkeletonGrid count={6} />;
  if (summary.isError) return <ErrorState error={summary.error} onRetry={() => summary.refetch()} />;
  if (!summary.data) return <ErrorState error={new Error("Dashboard data is empty")} onRetry={() => summary.refetch()} />;

  const data = summary.data;

  return (
    <>
      <div className="mb-5 overflow-hidden rounded-lg border border-line bg-ink text-white shadow-lift">
        <div className="grid gap-4 p-5 sm:p-6 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="mb-2 text-xs font-black uppercase text-[#9fd5ba]">Today Command Center</p>
            <h1 className="text-3xl font-black tracking-normal sm:text-4xl">Dashboard</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-white/70">
              Сегодняшний баланс питания, тренировки и быстрые действия для ежедневного контроля.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button className="bg-white text-ink hover:bg-[#f0eee7]" variant="secondary">Сегодня</Button>
            <LinkButton compact to="/nutrition/photo" icon={<Camera className="h-4 w-4" />}>Photo AI</LinkButton>
          </div>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 lg:col-span-2">
          <Metric icon={<Flame className="h-5 w-5" />} title="Калории" value={moneylessNumber(data.nutrition.totals.calories)} suffix="ккал" tone="action" />
          <Metric icon={<Beef className="h-5 w-5" />} title="Белки" value={moneylessNumber(data.nutrition.totals.protein)} suffix="г" tone="coral" />
          <Metric icon={<Dumbbell className="h-5 w-5" />} title="Тренировки" value={String(data.workouts.completed_workouts)} suffix="за неделю" tone="amber" />
          <Metric icon={<Scale className="h-5 w-5" />} title="Объём" value={moneylessNumber(data.workouts.total_volume)} suffix="кг" tone="steel" />
        </section>

        <Card className="lg:col-span-1">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="text-xs font-black uppercase text-action">Shortcuts</p>
              <h2 className="text-lg font-black">Быстрые действия</h2>
            </div>
          </div>
          <div className="grid gap-2">
            <LinkButton to="/nutrition" icon={<Plus className="h-4 w-4" />}>Добавить еду</LinkButton>
            <LinkButton to="/nutrition/photo" icon={<Camera className="h-4 w-4" />}>Распознать фото</LinkButton>
            <LinkButton to="/workouts" icon={<Dumbbell className="h-4 w-4" />}>Начать тренировку</LinkButton>
            <LinkButton to="/workouts/active" icon={<Utensils className="h-4 w-4" />}>Открыть активную</LinkButton>
          </div>
        </Card>

        <Card>
          <p className="text-xs font-black uppercase text-action">Nutrition</p>
          <h2 className="mb-3 text-lg font-black">Прогресс по целям</h2>
          <div className="grid gap-3">
            {(["calories", "protein", "fat", "carbs"] as const).map((key) => {
              const item = data.nutrition.progress[key];
              const pct = Math.min(Number(item.percent ?? 0), 100);
              return (
                <div key={key}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="font-semibold">{labels[key]}</span>
                    <span className="text-muted">{moneylessNumber(item.consumed)} / {moneylessNumber(item.target)}</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-[#e8e6de]">
                    <div className="h-2.5 rounded-full bg-action transition-all" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
            <div>
              <p className="text-xs font-black uppercase text-action">Analytics</p>
              <h2 className="text-lg font-black">Тренд 14 дней</h2>
            </div>
            <span className="rounded-md bg-mint px-2 py-1 text-xs font-bold text-action">calories</span>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends.data?.points ?? []}>
                <CartesianGrid stroke="#dfded6" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Area type="monotone" dataKey="nutrition.calories" stroke="#187454" fill="#d9eadf" name="Калории" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </>
  );
}

const labels = { calories: "Калории", protein: "Белки", fat: "Жиры", carbs: "Углеводы" };

function Metric({
  icon,
  title,
  value,
  suffix,
  tone,
}: {
  icon: ReactNode;
  title: string;
  value: string;
  suffix: string;
  tone: "action" | "coral" | "amber" | "steel";
}) {
  const toneClass = {
    action: "bg-mint text-action",
    coral: "bg-[#f4dfd6] text-coral",
    amber: "bg-[#f2e5ce] text-amber",
    steel: "bg-oat text-steel",
  }[tone];

  return (
    <Card className="transition hover:-translate-y-0.5 hover:shadow-lift">
      <div className={`mb-4 grid h-10 w-10 place-items-center rounded-md ${toneClass}`}>{icon}</div>
      <p className="text-sm font-bold text-muted">{title}</p>
      <p className="mt-1 text-3xl font-black">{value}</p>
      <p className="text-sm font-medium text-muted">{suffix}</p>
    </Card>
  );
}

function LinkButton({ to, icon, children, compact = false }: { to: string; icon: ReactNode; children: ReactNode; compact?: boolean }) {
  return (
    <Link
      className={`flex min-h-11 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-bold text-ink transition hover:border-[#c9c4b8] hover:bg-[#f6f3ec] ${
        compact ? "shadow-none" : ""
      }`}
      to={to}
    >
      {icon}
      {children}
    </Link>
  );
}
