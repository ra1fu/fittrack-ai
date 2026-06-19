export type ApiResponse<T, M = Record<string, unknown>> = {
  data: T;
  meta: M;
};

export type CountMeta = {
  count: number;
  total_count: number;
  limit: number;
  offset: number;
};

export type User = {
  id: string;
  email: string;
  email_verified: boolean;
};

export type AuthTokens = {
  access: string;
  refresh: string;
};

export type NutrientTotals = {
  calories: string;
  protein: string;
  fat: string;
  carbs: string;
};

export type ProgressItem = {
  consumed: string;
  target: string | null;
  remaining: string | null;
  percent: string | null;
};

export type Food = {
  id: string;
  name: string;
  brand?: string;
  source: string;
  barcode?: string;
  serving_size?: string | null;
  serving_unit?: string;
  calories_per_100g: string;
  protein_per_100g: string;
  fat_per_100g: string;
  carbs_per_100g: string;
  is_verified: boolean;
};

export type MealItem = {
  id: string;
  food_id: string;
  display_name_snapshot: string;
  weight_g: string | null;
  servings: string | null;
  calories_snapshot: string;
  protein_snapshot: string;
  fat_snapshot: string;
  carbs_snapshot: string;
};

export type Meal = {
  id: string;
  meal_date: string;
  meal_type: "breakfast" | "lunch" | "dinner" | "snack";
  custom_name?: string;
  notes?: string;
  items: MealItem[];
  totals: NutrientTotals;
};

export type NutritionDay = {
  date: string;
  totals: NutrientTotals;
  progress: Record<keyof NutrientTotals, ProgressItem>;
  meals: Meal[];
};

export type DashboardSummary = {
  date: string;
  nutrition: {
    totals: NutrientTotals;
    progress: Record<keyof NutrientTotals, ProgressItem>;
    meal_count: number;
  };
  workouts: {
    completed_workouts: number;
    total_volume: string;
    completed_working_sets: number;
    duration_seconds: number;
  };
};

export type DashboardTrends = {
  date_from: string;
  date_to: string;
  points: Array<{
    date: string;
    nutrition: NutrientTotals & { meal_count: number };
    workouts: { completed_workouts: number; total_volume: string };
  }>;
};

export type Exercise = {
  id: string;
  name: string;
  description?: string;
  tracking_type: string;
  is_system: boolean;
  primary_muscle_group?: { id: string; code: string; name: string };
  equipment?: { id: string; code: string; name: string } | null;
};

export type RoutineExercise = {
  id: string;
  exercise_id: string;
  position: number;
  planned_sets: number;
  rep_min: number | null;
  rep_max: number | null;
  target_weight: string | null;
  target_rpe: string | null;
  target_rir: string | null;
  rest_seconds: number | null;
  notes?: string;
  superset_group?: string;
};

export type RoutineDay = {
  id: string;
  name: string;
  position: number;
  planned_weekday: number | null;
  exercises: RoutineExercise[];
};

export type Routine = {
  id: string;
  name: string;
  description?: string;
  color?: string;
  is_active: boolean;
  days: RoutineDay[];
};

export type WorkoutSet = {
  id: string;
  position: number;
  set_type: string;
  weight: string | null;
  repetitions: number | null;
  duration_seconds: number | null;
  distance_meters: string | null;
  is_completed: boolean;
  notes?: string;
};

export type Workout = {
  id: string;
  name: string | null;
  status: string;
  started_at: string;
  finished_at: string | null;
  metrics: Record<string, unknown>;
  exercises: Array<{
    id: string;
    exercise_id: string;
    position: number;
    sets: WorkoutSet[];
  }>;
};
