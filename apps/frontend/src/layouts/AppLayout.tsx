import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bot,
  Dumbbell,
  Home,
  ListChecks,
  LogOut,
  Medal,
  Salad,
  UserRound,
  Utensils,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../shared/api/client";
import { Button } from "../shared/ui/button";
import { useAuthStore } from "../features/auth/store";

const desktopNav = [
  { to: "/dashboard", label: "Dashboard", icon: Home },
  { to: "/nutrition", label: "Nutrition", icon: Utensils },
  { to: "/nutrition/photo", label: "Photo AI", icon: Bot },
  { to: "/exercises", label: "Exercises", icon: Activity },
  { to: "/routines", label: "Routines", icon: ListChecks },
  { to: "/workouts", label: "Workouts", icon: Dumbbell },
  { to: "/records", label: "Records", icon: Medal },
  { to: "/profile", label: "Profile", icon: UserRound },
];

const mobileNav = [
  { to: "/dashboard", label: "Home", icon: Home },
  { to: "/nutrition", label: "Food", icon: Salad },
  { to: "/workouts", label: "Workout", icon: Dumbbell },
  { to: "/exercises", label: "Moves", icon: Activity },
  { to: "/profile", label: "Profile", icon: UserRound },
];

function NavItem({ to, label, icon: Icon }: (typeof desktopNav)[number]) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `group flex min-h-11 items-center gap-3 rounded-md px-3 text-sm font-bold transition ${
          isActive
            ? "bg-action text-white shadow-soft"
            : "text-muted hover:bg-white hover:text-ink hover:shadow-[0_1px_10px_rgba(31,39,36,0.06)]"
        }`
      }
    >
      <Icon className="h-5 w-5" aria-hidden />
      <span>{label}</span>
    </NavLink>
  );
}

export function AppLayout() {
  const navigate = useNavigate();
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const clearSession = useAuthStore((state) => state.clearSession);
  const activeWorkout = useQuery({
    queryKey: ["active-workout"],
    queryFn: () => api.activeWorkout().then((response) => response.data),
  });

  const logout = async () => {
    if (refreshToken) {
      await api.logout(refreshToken).catch(() => undefined);
    }
    clearSession();
    navigate("/login", { replace: true });
  };

  return (
    <div className="dashboard-grid min-h-screen bg-canvas text-ink">
      <aside className="fixed left-0 top-0 hidden h-screen w-68 border-r border-line bg-[#fbfaf6]/95 p-4 backdrop-blur lg:block">
        <div className="mb-6 rounded-lg border border-line/70 bg-white p-3 shadow-soft">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-lg bg-ink text-white shadow-soft">
              <Dumbbell className="h-5 w-5" aria-hidden />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-black">FitTrack AI</p>
              <p className="text-xs font-semibold text-muted">Daily performance desk</p>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-md bg-mint px-2 py-2">
              <p className="text-[10px] font-bold uppercase text-action">Food</p>
            </div>
            <div className="rounded-md bg-oat px-2 py-2">
              <p className="text-[10px] font-bold uppercase text-steel">Train</p>
            </div>
            <div className="rounded-md bg-[#f4dfd6] px-2 py-2">
              <p className="text-[10px] font-bold uppercase text-coral">AI</p>
            </div>
          </div>
        </div>
        <nav className="grid gap-1">
          {desktopNav.map((item) => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>
        <Button className="absolute bottom-4 left-4 right-4" variant="secondary" onClick={logout}>
          <LogOut className="h-4 w-4" aria-hidden />
          Выйти
        </Button>
      </aside>

      <main className="pb-24 lg:ml-64 lg:pb-0">
        {activeWorkout.data ? (
          <button
            className="sticky top-0 z-20 flex w-full items-center justify-center gap-2 bg-amber px-4 py-3 text-sm font-black text-white shadow-soft"
            onClick={() => navigate("/workouts/active")}
          >
            <Dumbbell className="h-4 w-4" aria-hidden />
            Активная тренировка
          </button>
        ) : null}
        <div className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </div>
      </main>

      <nav className="safe-bottom fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-line bg-white/95 px-2 pt-2 shadow-[0_-12px_30px_rgba(31,39,36,0.09)] backdrop-blur lg:hidden">
        {mobileNav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `grid min-h-14 place-items-center rounded-md text-[11px] font-bold transition ${
                isActive ? "bg-mint text-action" : "text-muted"
              }`
            }
          >
            <Icon className="h-5 w-5" aria-hidden />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
