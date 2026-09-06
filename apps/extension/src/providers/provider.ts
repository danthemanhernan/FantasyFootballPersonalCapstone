export type CanonicalPosition = "QB" | "RB" | "WR" | "TE" | "K" | "DST" | "UNKNOWN";

export type LeagueRef = {
  leagueId: string;
  season: number;
  /** ESPN uses this to select the roster/scoring period; omitted for providers that do not need it. */
  scoringPeriodId?: number;
};

export type CanonicalRosterPlayer = {
  id: string;
  name: string;
  position: CanonicalPosition;
  team: string;
  source: { provider: string; playerId: string; teamId?: string };
};

export type CanonicalRoster = {
  league: LeagueRef;
  players: CanonicalRosterPlayer[];
  fetchedAt: string;
};

export type ProviderErrorCode =
  | "AUTHENTICATION_REQUIRED"
  | "NOT_FOUND"
  | "RATE_LIMITED"
  | "UNAVAILABLE"
  | "INVALID_PAYLOAD";

export class ProviderError extends Error {
  constructor(
    public readonly code: ProviderErrorCode,
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ProviderError";
  }
}

export type ProviderPort = {
  loadRoster(ref: LeagueRef): Promise<CanonicalRoster>;
};
