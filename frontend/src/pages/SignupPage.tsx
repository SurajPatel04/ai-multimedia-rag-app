import { useState } from "react";
import type { AxiosError } from "axios";
import SignupFormDemo, {
  type AuthFormValues,
} from "@/components/signup-form-demo";
import { authService } from "@/services/authService";

const getErrorMessage = (error: unknown) => {
  const axiosError = error as AxiosError<{ message?: string }>;
  return axiosError.response?.data?.message || "Unable to create account.";
};

export default function SignupPage() {
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async ({
    first_name,
    last_name,
    email,
    password,
  }: AuthFormValues) => {
    setError(null);
    setIsLoading(true);

    try {
      await authService.register({
        first_name: first_name || "",
        ...(last_name ? { last_name } : {}),
        email,
        password,
      });
      await authService.fetchProfile();
      window.location.href = "/me";
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-5xl items-center justify-center">
      <div className="w-full">
        <SignupFormDemo
          error={error}
          isLoading={isLoading}
          mode="signup"
          onSubmit={handleSubmit}
        />
        <p className="mt-5 text-center text-sm text-neutral-300">
          Already have an account?{" "}
          <a className="font-medium text-white underline" href="/login">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
