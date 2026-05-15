import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import SignupFormDemo, {
  type AuthFormValues,
} from "@/components/signup-form-demo";
import type { AppDispatch, RootState } from "@/app/store";
import { loginUser } from "@/features/auth/authThunks";
import { clearError } from "@/features/auth/authSlice";
import { useEffect } from "react";

export default function LoginPage() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { isLoading, error } = useSelector((state: RootState) => state.auth);

  useEffect(() => {
    return () => {
      dispatch(clearError());
    };
  }, [dispatch]);

  const handleSubmit = async (values: AuthFormValues) => {
    const resultAction = await dispatch(loginUser(values));
    if (loginUser.fulfilled.match(resultAction)) {
      navigate("/chat");
    }
  };

  return (
    <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-5xl items-center justify-center">
      <div className="w-full">
        <SignupFormDemo
          error={error}
          isLoading={isLoading}
          mode="login"
          onSubmit={handleSubmit}
        />
        <p className="mt-5 text-center text-sm text-neutral-300">
          Need an account?{" "}
          <button
            className="font-medium text-white underline bg-transparent border-none cursor-pointer p-0"
            onClick={() => navigate("/signup")}
          >
            Sign up
          </button>
        </p>
      </div>
    </div>
  );
}

