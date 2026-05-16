import { useEffect } from "react";
import { authService } from "@/services/authService";

const DEFAULT_REFRESH_MS = 3_000_000;
const REFRESH_BUFFER_MS = 10_000;

const parseTtlToMs = (ttl?: string) => {
  if (!ttl) return DEFAULT_REFRESH_MS;

  const normalized = ttl.trim().replaceAll('"', "");
  const match = normalized.match(/^(\d+(?:\.\d+)?)(ms|s|m|h)?$/i);
  if (!match) return DEFAULT_REFRESH_MS;

  const value = Number(match[1]);
  const unit = match[2]?.toLowerCase() || "ms";

  if (unit === "h") return value * 60 * 60 * 1000;
  if (unit === "m") return value * 60 * 1000;
  if (unit === "s") return value * 1000;
  return value;
};

const getRefreshDelay = () => {
  const ttlMs = parseTtlToMs(import.meta.env.VITE_ACCESS_TOKEN_TTL);
  return Math.max(5_000, ttlMs - REFRESH_BUFFER_MS);
};

export function useSilentTokenRefresh(enabled: boolean) {
  useEffect(() => {
    if (!enabled) return;

    let isActive = true;
    let timeoutId: ReturnType<typeof setTimeout>;

    const scheduleRefresh = () => {
      timeoutId = setTimeout(async () => {
        try {
          await authService.refreshToken();
          if (isActive) {
            scheduleRefresh();
          }
        } catch {
          if (isActive) {
            window.location.replace("/login");
          }
        }
      }, getRefreshDelay());
    };

    scheduleRefresh();

    return () => {
      isActive = false;
      clearTimeout(timeoutId);
    };
  }, [enabled]);
}
