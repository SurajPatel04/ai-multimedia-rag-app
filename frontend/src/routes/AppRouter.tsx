import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";
import MePage from "@/pages/MePage";
import SignupPage from "@/pages/SignupPage";
import { ProtectedRoute, UnprotectedRoute } from "@/routes/AuthRoute";

export default function AppRouter() {
  return (
    <Routes>
      <Route element={<UnprotectedRoute />}>
        <Route path="/" element={<Navigate replace to="/login" />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/register" element={<SignupPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/me" element={<MePage />} />
        <Route path="/user/me" element={<MePage />} />
        <Route path="/dashboard" element={<MePage />} />
      </Route>

      <Route path="*" element={<Navigate replace to="/login" />} />
    </Routes>
  );
}
