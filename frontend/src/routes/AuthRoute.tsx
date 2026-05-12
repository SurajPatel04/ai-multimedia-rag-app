import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { authService } from "@/services/authService";

type AuthRouteProps = {
  redirectTo?: string;
};

const LoadingScreen = () => (
  <div className="flex min-h-[calc(100vh-5rem)] items-center justify-center">
    <p className="text-sm text-neutral-300">Checking session...</p>
  </div>
);

export function ProtectedRoute({
  redirectTo = "/login",
}: AuthRouteProps) {
  const [isAllowed, setIsAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        await authService.fetchProfile();
        setIsAllowed(true);
      } catch {
        setIsAllowed(false);
      }
    };

    void checkAuth();
  }, [redirectTo]);

  if (isAllowed === null) {
    return <LoadingScreen />;
  }

  if (!isAllowed) {
    return <Navigate replace to={redirectTo} />;
  }

  return <Outlet />;
}

export function UnprotectedRoute({
  redirectTo = "/me",
}: AuthRouteProps) {
  const [isAllowed, setIsAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        await authService.fetchProfile();
        setIsAllowed(false);
      } catch {
        setIsAllowed(true);
      }
    };

    void checkAuth();
  }, [redirectTo]);

  if (isAllowed === null) {
    return <LoadingScreen />;
  }

  if (!isAllowed) {
    return <Navigate replace to={redirectTo} />;
  }

  return <Outlet />;
}
