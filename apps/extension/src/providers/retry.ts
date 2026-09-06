import type { CanonicalRoster, LeagueRef, ProviderError, ProviderPort } from "./provider";

export type RetryOptions = {
  maxAttempts?: number;
  delayMs?: number;
  sleep?: (milliseconds: number) => Promise<void>;
};

const defaultSleep = (milliseconds: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, milliseconds));

const isRetryable = (error: unknown): error is ProviderError =>
  Boolean(error && typeof error === "object" && "code" in error &&
    ((error as ProviderError).code === "UNAVAILABLE"));

/** Application-owned bounded retry: auth, not-found, rate-limit, and payload errors are terminal. */
export const loadRosterWithRetry = async (
  provider: ProviderPort,
  league: LeagueRef,
  { maxAttempts = 3, delayMs = 250, sleep = defaultSleep }: RetryOptions = {},
): Promise<CanonicalRoster> => {
  const attempts = Math.max(1, Math.floor(maxAttempts));
  let attempt = 0;

  while (attempt < attempts) {
    attempt += 1;
    try {
      return await provider.loadRoster(league);
    } catch (error) {
      if (!isRetryable(error) || attempt >= attempts) throw error;
      await sleep(delayMs * attempt);
    }
  }

  throw new Error("Retry policy exhausted without a provider result");
};
