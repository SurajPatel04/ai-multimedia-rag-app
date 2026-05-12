import { useEffect, useState } from "react";
import type { AxiosError } from "axios";
import { authService, type User } from "@/services/authService";

const getErrorMessage = (error: unknown) => {
  const axiosError = error as AxiosError<{ message?: string }>;
  return axiosError.response?.data?.message || "Unable to load profile.";
};

export default function MePage() {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadProfile = async () => {
      try {
        setUser(await authService.fetchProfile());
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setIsLoading(false);
      }
    };

    void loadProfile();
  }, []);

  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(" ");

  return (
    <section className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-3xl items-center">
      <div className="w-full rounded-lg bg-black p-6 shadow-sm ring-1 ring-white/10 md:p-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-neutral-800 pb-5">
          <div>
            <h1 className="text-2xl font-semibold text-white">My Profile</h1>
            <p className="mt-1 text-sm text-neutral-300">
              Loaded from /user/me using the auth cookie.
            </p>
          </div>
          <a
            className="rounded-md bg-white px-4 py-2 text-sm font-medium text-neutral-950"
            href="/login"
          >
            Sign in
          </a>
        </div>

        {isLoading ? (
          <p className="text-sm text-neutral-300">Loading profile...</p>
        ) : error ? (
          <p className="rounded-md border border-red-900/60 bg-red-950/30 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : user ? (
          <dl className="grid gap-4 text-sm md:grid-cols-2">
            <div className="rounded-md border border-neutral-800 p-4">
              <dt className="text-neutral-400">Name</dt>
              <dd className="mt-1 font-medium text-white">{fullName || user.first_name}</dd>
            </div>
            <div className="rounded-md border border-neutral-800 p-4">
              <dt className="text-neutral-400">Email</dt>
              <dd className="mt-1 font-medium text-white">{user.email}</dd>
            </div>
          </dl>
        ) : null}
      </div>
    </section>
  );
}
