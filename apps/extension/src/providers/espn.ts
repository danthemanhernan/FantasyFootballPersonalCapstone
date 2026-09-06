import type {
  CanonicalPosition,
  CanonicalRoster,
  LeagueRef,
  ProviderPort,
} from "./provider";
import { ProviderError } from "./provider";

type EspnPlayer = {
  id: string | number;
  fullName: string;
  defaultPositionId?: number;
  proTeamId?: number;
};

type EspnRosterEntry = { playerPoolEntry?: { player?: EspnPlayer } };
type EspnTeam = { id: string | number; roster?: { entries?: EspnRosterEntry[] } };
type EspnLeaguePayload = { teams: EspnTeam[] };

const positionById: Record<number, CanonicalPosition> = {
  1: "QB",
  2: "RB",
  3: "WR",
  4: "TE",
  5: "K",
  16: "DST",
};

const teamById: Record<number, string> = {
  1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE", 6: "DAL",
  7: "DEN", 8: "DET", 9: "GB", 10: "TEN", 11: "IND", 12: "KC",
  13: "LV", 14: "LAR", 15: "MIA", 16: "MIN", 17: "NE", 18: "NO",
  19: "NYG", 20: "NYJ", 21: "PHI", 22: "ARI", 23: "PIT", 24: "LAC",
  25: "SF", 26: "SEA", 27: "TB", 28: "WAS", 29: "CAR", 30: "JAX",
  33: "BAL", 34: "HOU",
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isPayload = (value: unknown): value is EspnLeaguePayload => {
  if (!isRecord(value) || !Array.isArray(value.teams)) return false;
  return value.teams.every((team): team is EspnTeam => {
    if (!isRecord(team) || (typeof team.id !== "string" && typeof team.id !== "number")) {
      return false;
    }
    return team.roster === undefined || (
      isRecord(team.roster) &&
      Array.isArray(team.roster.entries) &&
      team.roster.entries.every((entry) => isRecord(entry))
    );
  });
};

export const mapEspnRoster = (
  payload: unknown,
  league: LeagueRef,
  fetchedAt = new Date().toISOString(),
): CanonicalRoster => {
  if (!isPayload(payload)) {
    throw new ProviderError("INVALID_PAYLOAD", "ESPN roster payload is malformed");
  }

  const players = payload.teams.flatMap((team) => {
    if (!Array.isArray(team.roster?.entries)) {
      throw new ProviderError("INVALID_PAYLOAD", "ESPN team roster is malformed");
    }
    return team.roster.entries.map((entry) => {
      const playerPoolEntry = isRecord(entry.playerPoolEntry) ? entry.playerPoolEntry : null;
      const player = playerPoolEntry && isRecord(playerPoolEntry.player)
        ? playerPoolEntry.player
        : null;
      if (
        !player ||
        (typeof player.id !== "string" && typeof player.id !== "number") ||
        typeof player.fullName !== "string" ||
        player.fullName.trim() === ""
      ) {
        throw new ProviderError("INVALID_PAYLOAD", "ESPN player record is malformed");
      }
      return {
        id: `espn:${player.id}`,
        name: player.fullName,
        position: positionById[player.defaultPositionId ?? -1] ?? "UNKNOWN",
        team: teamById[player.proTeamId ?? -1] ?? "FA",
        source: {
          provider: "espn",
          playerId: String(player.id),
          teamId: String(team.id),
        },
      };
    });
  });

  return { league, players, fetchedAt };
};

export type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

const classifyStatus = (status: number): ProviderError => {
  if (status === 401 || status === 403) {
    return new ProviderError("AUTHENTICATION_REQUIRED", "ESPN authentication is required", status);
  }
  if (status === 404) return new ProviderError("NOT_FOUND", "ESPN league was not found", status);
  if (status === 429) return new ProviderError("RATE_LIMITED", "ESPN rate limit reached", status);
  return new ProviderError("UNAVAILABLE", `ESPN returned HTTP ${status}`, status);
};

export class EspnProvider implements ProviderPort {
  constructor(
    private readonly fetchImpl: FetchLike = fetch,
    private readonly timeoutMs = 5_000,
    private readonly baseUrl = "https://lm-api-reads.fantasy.espn.com/apis/v3",
  ) {}

  async loadRoster(ref: LeagueRef): Promise<CanonicalRoster> {
    const url = `${this.baseUrl}/games/ffl/seasons/${ref.season}/segments/0/leagues/${ref.leagueId}?view=mTeam&view=mRoster`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await this.fetchImpl(url, {
        method: "GET",
        credentials: "include",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok) throw classifyStatus(response.status);
      try {
        return mapEspnRoster(await response.json(), ref);
      } catch (error) {
        if (error instanceof ProviderError) throw error;
        throw new ProviderError("INVALID_PAYLOAD", "ESPN returned invalid JSON");
      }
    } catch (error) {
      if (error instanceof ProviderError) throw error;
      throw new ProviderError("UNAVAILABLE", controller.signal.aborted
        ? "ESPN request timed out"
        : "ESPN request failed");
    } finally {
      clearTimeout(timeout);
    }
  }
}

export const createEspnFixtureProvider = (
  payload: unknown,
  fetchedAt = "2026-08-24T00:00:00.000Z",
): ProviderPort => ({
  loadRoster: async (league) => mapEspnRoster(payload, league, fetchedAt),
});
