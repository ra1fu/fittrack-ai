import { useAuthStore } from "../../features/auth/store";
import { ApiError, parseApiError } from "./errors";
import type {
  ApiResponse,
  AuthTokens,
  CountMeta,
  DashboardSummary,
  DashboardTrends,
  Exercise,
  Food,
  Meal,
  NutritionDay,
  Routine,
  User,
  Workout,
  WorkoutSet,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  auth?: boolean;
  retry401?: boolean;
};

async function readPayload(response: Response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function refreshAccessToken() {
  const { refreshToken, setSession, setAccessToken, user, clearSession } = useAuthStore.getState();
  if (!refreshToken) return false;

  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: refreshToken }),
  });

  if (!response.ok) {
    clearSession();
    return false;
  }

  const payload = (await readPayload(response)) as ApiResponse<Partial<AuthTokens>>;
  if (!payload.data.access) return false;
  if (payload.data.refresh) {
    setSession({ access: payload.data.access, refresh: payload.data.refresh }, user);
  } else {
    setAccessToken(payload.data.access);
  }
  return true;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { accessToken } = useAuthStore.getState();
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (options.auth !== false && accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      body:
        options.body instanceof FormData
          ? options.body
          : options.body !== undefined
            ? JSON.stringify(options.body)
            : undefined,
    });
  } catch (error) {
    throw new ApiError({
      status: 0,
      code: "NETWORK_ERROR",
      message: error instanceof Error ? error.message : "Нет соединения с сервером.",
    });
  }

  const payload = await readPayload(response);

  if (response.status === 401 && options.auth !== false && options.retry401 !== false) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return apiRequest<T>(path, { ...options, retry401: false });
  }

  if (!response.ok) {
    throw parseApiError(response.status, payload);
  }

  return payload as T;
}

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  });
  const value = search.toString();
  return value ? `?${value}` : "";
};

export const api = {
  login: (body: { email: string; password: string }) =>
    apiRequest<ApiResponse<AuthTokens & { user: User }>>("/auth/login", {
      method: "POST",
      auth: false,
      body,
    }),
  register: (body: {
    email: string;
    password: string;
    accepted_terms: boolean;
    accepted_privacy: boolean;
  }) => apiRequest<ApiResponse<User>>("/auth/register", { method: "POST", auth: false, body }),
  logout: (refresh: string) =>
    apiRequest<ApiResponse<{ success: boolean }>>("/auth/logout", {
      method: "POST",
      body: { refresh },
      retry401: false,
    }),
  me: () => apiRequest<ApiResponse<{ user: User; profile: Record<string, unknown> }>>("/me"),
  updateMe: (body: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/me", { method: "PATCH", body }),
  goals: () => apiRequest<ApiResponse<Array<Record<string, unknown>>>>("/me/goals"),
  createGoal: (body: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/me/goals", { method: "POST", body }),
  updateGoal: (id: string, body: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/me/goals/${id}`, { method: "PATCH", body }),
  dashboardSummary: (date: string) =>
    apiRequest<ApiResponse<DashboardSummary>>(`/dashboard/summary${qs({ date })}`),
  dashboardTrends: (date_from: string, date_to: string) =>
    apiRequest<ApiResponse<DashboardTrends>>(
      `/dashboard/trends${qs({ date_from, date_to })}`,
    ),
  nutritionDay: (date: string) => apiRequest<ApiResponse<NutritionDay>>(`/nutrition/days/${date}`),
  meals: (date: string) => apiRequest<ApiResponse<Meal[], CountMeta>>(`/meals${qs({ date })}`),
  createMeal: (body: Record<string, unknown>) =>
    apiRequest<ApiResponse<Meal>>("/meals", { method: "POST", body }),
  updateMeal: (id: string, body: Record<string, unknown>) =>
    apiRequest<ApiResponse<Meal>>(`/meals/${id}`, { method: "PATCH", body }),
  deleteMeal: (id: string) => apiRequest<ApiResponse<{ success: boolean }>>(`/meals/${id}`, { method: "DELETE" }),
  foods: (params: Record<string, string | number | boolean | undefined>) =>
    apiRequest<ApiResponse<Food[], CountMeta>>(`/foods${qs(params)}`),
  createFood: (body: Record<string, unknown>) =>
    apiRequest<ApiResponse<Food>>("/foods", { method: "POST", body }),
  addMealItem: (mealId: string, body: Record<string, unknown>) =>
    apiRequest<ApiResponse<unknown>>(`/meals/${mealId}/items`, { method: "POST", body }),
  updateMealItem: (itemId: string, body: Record<string, unknown>) =>
    apiRequest<ApiResponse<unknown>>(`/meal-items/${itemId}`, { method: "PATCH", body }),
  deleteMealItem: (itemId: string) =>
    apiRequest<ApiResponse<{ success: boolean }>>(`/meal-items/${itemId}`, { method: "DELETE" }),
  photoUpload: (body: FormData) =>
    apiRequest<ApiResponse<Record<string, unknown>>>("/nutrition/photo-recognitions/upload", {
      method: "POST",
      body,
    }),
  photoRecognitions: () =>
    apiRequest<ApiResponse<Array<Record<string, unknown>>, CountMeta>>("/nutrition/photo-recognitions"),
  updateRecognitionItem: (id: string, body: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(
      `/nutrition/photo-recognition-items/${id}`,
      { method: "PATCH", body },
    ),
  confirmRecognition: (id: string, body: Record<string, unknown>) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(
      `/nutrition/photo-recognitions/${id}/confirm`,
      { method: "POST", body },
    ),
  exercises: (params: Record<string, string | number | undefined>) =>
    apiRequest<ApiResponse<Exercise[], CountMeta>>(`/exercises${qs(params)}`),
  muscleGroups: () => apiRequest<ApiResponse<Array<{ id: string; name: string }>>>("/muscle-groups"),
  equipment: () => apiRequest<ApiResponse<Array<{ id: string; name: string }>>>("/equipment"),
  createExercise: (body: Record<string, unknown>) =>
    apiRequest<ApiResponse<Exercise>>("/exercises", { method: "POST", body }),
  routines: () => apiRequest<ApiResponse<Routine[], CountMeta>>("/routines"),
  createRoutine: (body: Record<string, unknown>) =>
    apiRequest<ApiResponse<Routine>>("/routines", { method: "POST", body }),
  workouts: () => apiRequest<ApiResponse<Workout[], CountMeta>>("/workouts"),
  activeWorkout: () => apiRequest<ApiResponse<Workout | null>>("/workouts/active"),
  startWorkout: (body: Record<string, unknown>) =>
    apiRequest<ApiResponse<Workout>>("/workouts", { method: "POST", body }),
  finishWorkout: (id: string) =>
    apiRequest<ApiResponse<{ success: boolean }>>(`/workouts/${id}/finish`, { method: "POST" }),
  cancelWorkout: (id: string) =>
    apiRequest<ApiResponse<{ success: boolean }>>(`/workouts/${id}/cancel`, { method: "POST" }),
  addWorkoutSet: (exerciseId: string, body: Record<string, unknown>) =>
    apiRequest<ApiResponse<WorkoutSet>>(`/workout-exercises/${exerciseId}/sets`, {
      method: "POST",
      body,
    }),
  updateWorkoutSet: (setId: string, body: Record<string, unknown>) =>
    apiRequest<ApiResponse<WorkoutSet>>(`/workout-sets/${setId}`, { method: "PATCH", body }),
  deleteWorkoutSet: (setId: string) =>
    apiRequest<ApiResponse<{ success: boolean }>>(`/workout-sets/${setId}`, { method: "DELETE" }),
  personalRecords: () =>
    apiRequest<ApiResponse<Array<Record<string, unknown>>, CountMeta>>("/personal-records"),
};
