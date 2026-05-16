import { Link, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import SignupFormDemo, {
  type AuthFormValues,
} from "@/components/signup-form-demo";
import type { AppDispatch, RootState } from "@/app/store";
import { registerUser } from "@/features/auth/authThunks";
import { clearError } from "@/features/auth/authSlice";
import { useEffect } from "react";
import ragIcon from "@/assets/rag.png";
import { showToast } from "@/lib/toast";

export default function SignupPage() {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { isLoading, error } = useSelector((state: RootState) => state.auth);

  useEffect(() => {
    return () => {
      dispatch(clearError());
    };
  }, [dispatch]);

  const handleSubmit = async (values: AuthFormValues) => {
    const payload = {
      first_name: values.first_name || "",
      ...(values.last_name ? { last_name: values.last_name } : {}),
      email: values.email,
      password: values.password,
    };

    const resultAction = await dispatch(registerUser(payload));
    if (registerUser.fulfilled.match(resultAction)) {
      showToast.success("Account created successfully! Please sign in.");
      navigate("/login");
    } else if (registerUser.rejected.match(resultAction)) {
      showToast.error(resultAction.payload as string || "Registration failed");
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center p-6 relative">
      <div className="absolute top-8 left-8 md:left-12">
        <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <img src={ragIcon} alt="Logo" className="h-8 w-8 object-contain" />
          <span className="text-xl font-bold tracking-tight text-white">InsightFlow</span>
        </Link>
      </div>
      <div className="w-full max-w-md">
        <SignupFormDemo
          error={error}
          isLoading={isLoading}
          mode="signup"
          onSubmit={handleSubmit}
        />
        <p className="mt-3 text-center text-sm text-neutral-300">
          Already have an account?{" "}
          <button
            className="font-medium text-white underline bg-transparent border-none cursor-pointer p-0"
            onClick={() => navigate("/login")}
          >
            Sign in
          </button>
        </p>
      </div>
    </div>
  );
}

