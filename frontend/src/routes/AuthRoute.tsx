import { useEffect } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useSilentTokenRefresh } from "@/hooks/useSilentTokenRefresh";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/app/store";
import { fetchProfile } from "@/features/auth/authThunks";

type AuthRouteProps = {
  redirectTo?: string;
};

const LoadingScreen = () => (
  <div className="flex min-h-screen items-center justify-center bg-black">
    <div className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-700 border-t-white" />
  </div>
);

export function ProtectedRoute({
  redirectTo = "/login",
}: AuthRouteProps) {
  const dispatch = useDispatch<AppDispatch>();
  const { isAuthenticated, isInitialized } = useSelector((state: RootState) => state.auth);

  useSilentTokenRefresh(isAuthenticated);

  useEffect(() => {
    if (!isInitialized) {
      void dispatch(fetchProfile());
    }
  }, [dispatch, isInitialized]);

  if (!isInitialized) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate replace to={redirectTo} />;
  }

  return <Outlet />;
}

export function UnprotectedRoute({
  redirectTo = "/chat",
}: AuthRouteProps) {
  const dispatch = useDispatch<AppDispatch>();
  const { isAuthenticated, isInitialized } = useSelector((state: RootState) => state.auth);

  useEffect(() => {
    if (!isInitialized) {
      void dispatch(fetchProfile());
    }
  }, [dispatch, isInitialized]);

  if (!isInitialized) {
    return <LoadingScreen />;
  }

  if (isAuthenticated) {
    return <Navigate replace to={redirectTo} />;
  }

  return <Outlet />;
}

