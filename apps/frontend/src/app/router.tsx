import { Navigate, createBrowserRouter } from "react-router-dom";
import { GuestRedirect, ProtectedRoute } from "./routeGuards";
import { DashboardPage } from "../pages/DashboardPage";
import { ExercisesPage } from "../pages/ExercisesPage";
import { LoginPage } from "../pages/LoginPage";
import { NutritionPage } from "../pages/NutritionPage";
import { PhotoRecognitionPage } from "../pages/PhotoRecognitionPage";
import { ProfilePage } from "../pages/ProfilePage";
import { RecordsPage } from "../pages/RecordsPage";
import { RegisterPage } from "../pages/RegisterPage";
import { RoutinesPage } from "../pages/RoutinesPage";
import { WorkoutsPage } from "../pages/WorkoutsPage";

export const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/dashboard" replace /> },
  {
    path: "/login",
    element: (
      <GuestRedirect>
        <LoginPage />
      </GuestRedirect>
    ),
  },
  {
    path: "/register",
    element: (
      <GuestRedirect>
        <RegisterPage />
      </GuestRedirect>
    ),
  },
  {
    element: <ProtectedRoute />,
    children: [
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/nutrition", element: <NutritionPage /> },
      { path: "/nutrition/photo", element: <PhotoRecognitionPage /> },
      { path: "/exercises", element: <ExercisesPage /> },
      { path: "/routines", element: <RoutinesPage /> },
      { path: "/workouts", element: <WorkoutsPage /> },
      { path: "/workouts/active", element: <WorkoutsPage activeOnly /> },
      { path: "/records", element: <RecordsPage /> },
      { path: "/profile", element: <ProfilePage /> },
    ],
  },
]);
