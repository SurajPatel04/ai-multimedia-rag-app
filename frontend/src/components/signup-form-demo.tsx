"use client";
import React from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type AuthFormValues = {
  first_name?: string;
  last_name?: string;
  email: string;
  password: string;
};

type SignupFormDemoProps = {
  mode: "login" | "signup";
  isLoading?: boolean;
  error?: string | null;
  onSubmit: (values: AuthFormValues) => void | Promise<void>;
};

const GOOGLE_LOGIN_URL = `${
  import.meta.env.VITE_BACKEND_URL || "/api/v1"
}/auth/google/login`;

export default function SignupFormDemo({
  mode,
  isLoading = false,
  error: _error,
  onSubmit,
}: SignupFormDemoProps) {
  const isSignup = mode === "signup";

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);

    void onSubmit({
      first_name: formData.get("first_name")?.toString().trim(),
      last_name: formData.get("last_name")?.toString().trim(),
      email: formData.get("email")?.toString().trim() || "",
      password: formData.get("password")?.toString() || "",
    });
  };

  const handleGoogleLogin = () => {
    window.location.href = GOOGLE_LOGIN_URL;
  };

  return (
    <div className="shadow-input mx-auto w-full max-w-md rounded-lg bg-white p-5 pb-4 md:p-8 md:pb-4 dark:bg-black">
      <h2 className="text-xl font-bold text-neutral-800 dark:text-neutral-200">
        {isSignup ? "Create your account" : "Welcome back"}
      </h2>
      <p className="mt-2 max-w-sm text-sm text-neutral-600 dark:text-neutral-300">
        {isSignup
          ? "Sign up with your name, email, and password."
          : "Sign in with your email and password."}
      </p>

      <form className="mt-8 mb-0" onSubmit={handleSubmit}>
        {isSignup ? (
          <div className="mb-4 flex flex-col space-y-2 md:flex-row md:space-y-0 md:space-x-2">
            <LabelInputContainer>
              <Label htmlFor="first_name">First name</Label>
              <Input
                id="first_name"
                name="first_name"
                placeholder="Suraj"
                required
                type="text"
              />
            </LabelInputContainer>
            <LabelInputContainer>
              <Label htmlFor="last_name">Last name</Label>
              <Input
                id="last_name"
                name="last_name"
                placeholder="Patel"
                type="text"
              />
            </LabelInputContainer>
          </div>
        ) : null}

        <LabelInputContainer className="mb-4">
          <Label htmlFor="email">Email Address</Label>
          <Input
            autoComplete="email"
            id="email"
            name="email"
            placeholder={isSignup ? "patel@gmail.com" : "suraj@gmail.com"}
            required
            type="email"
          />
        </LabelInputContainer>
        <LabelInputContainer className="mb-4">
          <Label htmlFor="password">Password</Label>
          <Input
            autoComplete={isSignup ? "new-password" : "current-password"}
            id="password"
            name="password"
            placeholder="••••••••"
            required
            type="password"
          />
        </LabelInputContainer>


        <button
          className="group/btn relative block h-10 w-full rounded-md bg-gradient-to-br from-black to-neutral-700 font-medium text-white shadow-[0px_1px_0px_0px_#ffffff40_inset,0px_-1px_0px_0px_#ffffff40_inset] disabled:cursor-not-allowed disabled:opacity-70 dark:bg-zinc-800 dark:from-zinc-900 dark:to-zinc-900 dark:shadow-[0px_1px_0px_0px_#27272a_inset,0px_-1px_0px_0px_#27272a_inset]"
          disabled={isLoading}
          type="submit"
        >
          {isLoading ? "Please wait..." : isSignup ? "Sign up" : "Sign in"}
          <BottomGradient />
        </button>

        {/* Divider */}
        <div className="my-5 flex items-center gap-3">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-neutral-700 to-transparent" />
          <span className="text-xs font-medium uppercase tracking-widest text-neutral-500">
            or
          </span>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-neutral-700 to-transparent" />
        </div>

        {/* Google OAuth Button */}
        <button
          type="button"
          onClick={handleGoogleLogin}
          className="group/btn relative flex h-10 w-full items-center justify-center gap-2 rounded-md border border-white/10 bg-neutral-950 font-medium text-neutral-300 transition-colors hover:border-white/20 hover:text-white"
        >
          <GoogleIcon className="h-4 w-4" />
          <span>Continue with Google</span>
          <BottomGradient />
        </button>
      </form>
    </div>
  );
}

const GoogleIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none">
    <path
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
      fill="#4285F4"
    />
    <path
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      fill="#34A853"
    />
    <path
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93l3.66-2.84z"
      fill="#FBBC05"
    />
    <path
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      fill="#EA4335"
    />
  </svg>
);

const BottomGradient = () => {
  return (
    <>
      <span className="absolute inset-x-0 -bottom-px block h-px w-full bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-0 transition duration-500 group-hover/btn:opacity-100" />
      <span className="absolute inset-x-10 -bottom-px mx-auto block h-px w-1/2 bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-0 blur-sm transition duration-500 group-hover/btn:opacity-100" />
    </>
  );
};

const LabelInputContainer = ({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) => {
  return (
    <div className={cn("flex w-full flex-col space-y-2", className)}>
      {children}
    </div>
  );
};
