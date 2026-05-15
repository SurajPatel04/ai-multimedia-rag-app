import { Link, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import SignupFormDemo, {
  type AuthFormValues,
} from "@/components/signup-form-demo";
import type { AppDispatch, RootState } from "@/app/store";
import { loginUser } from "@/features/auth/authThunks";
import { clearError } from "@/features/auth/authSlice";
import { useEffect } from "react";
import ragIcon from "@/assets/rag.png";

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
    <div className="min-h-screen w-full flex flex-col items-center justify-center p-6 relative">
      <div className="absolute top-8 left-8 md:left-12">
        <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <img src={ragIcon} alt="Logo" className="h-8 w-8 object-contain" />
          <span className="text-xl font-bold tracking-tight text-white">AI Chat</span>
        </Link>
      </div>
      <div className="w-full max-w-md">
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

