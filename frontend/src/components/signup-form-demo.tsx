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
      </form>
    </div>
  );
}

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
