import { Navigate, Route, Routes } from "react-router-dom";
import ChatPage from "@/pages/ChatPage";
import LoginPage from "@/pages/LoginPage";
import SignupPage from "@/pages/SignupPage";
import LandingPage from "@/pages/LandingPage";
import { ProtectedRoute, UnprotectedRoute } from "@/routes/AuthRoute";

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />

      <Route element={<UnprotectedRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/register" element={<SignupPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/dashboard" element={<Navigate replace to="/chat" />} />
        <Route path="/me" element={<Navigate replace to="/chat" />} />
        <Route path="/user/me" element={<Navigate replace to="/chat" />} />
      </Route>

      <Route path="*" element={<Navigate replace to="/login" />} />
    </Routes>
  );
}
