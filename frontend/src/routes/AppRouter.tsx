import { Navigate, Route, Routes } from "react-router-dom";
import ChatPage from "@/pages/ChatPage";
import LoginPage from "@/pages/LoginPage";
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
        <Route path="/dashboard" element={<ChatPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/me" element={<Navigate replace to="/dashboard" />} />
        <Route path="/user/me" element={<Navigate replace to="/dashboard" />} />
      </Route>

      <Route path="*" element={<Navigate replace to="/login" />} />
    </Routes>
  );
}
