import { Navigate } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";
import { useAuthStore } from "../features/auth/store";

export function ProtectedRoute() {
  const accessToken = useAuthStore((state) => state.accessToken);
  if (!accessToken) return <Navigate to="/login" replace />;
  return <AppLayout />;
}

export function GuestRedirect({ children }: { children: JSX.Element }) {
  const accessToken = useAuthStore((state) => state.accessToken);
  return accessToken ? <Navigate to="/dashboard" replace /> : children;
}
