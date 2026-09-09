import { describe, expect, it, vi } from "vitest";
import { createEspnFixtureProvider, EspnProvider, mapEspnRoster } from "./espn";
import fixture from "./espn.fixture.json";
import type { ProviderPort } from "./provider";
import { ProviderError } from "./provider";
import { loadRosterWithRetry } from "./retry";

const league = { leagueId: "12345", season: 2026 };

describe("ESPN provider boundary", () => {
  it("maps an ESPN fixture to a canonical roster", async () => {
    const roster = await createEspnFixtureProvider(fixture).loadRoster(league);

    expect(roster.league).toEqual(league);
    expect(roster.players).toEqual([
      {
        id: "espn:1001",
        name: "Brock Purdy",
        position: "QB",
        team: "SF",
        source: { provider: "espn", playerId: "1001", teamId: "1" },
      },
      {
        id: "espn:1002",
        name: "Christian McCaffrey",
        position: "RB",
        team: "SF",
        source: { provider: "espn", playerId: "1002", teamId: "1" },
      },
      {
        id: "espn:1003",
        name: "George Kittle",
        position: "TE",
        team: "SF",
        source: { provider: "espn", playerId: "1003", teamId: "2" },
      },
    ]);
  });

  it("adds the optional scoring period while preserving repeated view parameters", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(input.toString());
      expect(url.pathname).toContain("/games/ffl/seasons/2026/segments/0/leagues/12345");
      expect(url.searchParams.getAll("view")).toEqual(["mTeam", "mRoster"]);
      expect(url.searchParams.get("scoringPeriodId")).toBe("3");
      return new Response(JSON.stringify(fixture), { status: 200 });
    });

    await new EspnProvider(fetchImpl).loadRoster({ ...league, scoringPeriodId: 3 });
  });

  it("rejects a renamed or missing payload field", () => {
    expect(() => mapEspnRoster({ teams: [{ id: 1 }] }, league)).toThrowError(
      new ProviderError("INVALID_PAYLOAD", "ESPN team roster is malformed"),
    );
  });

  it("classifies malformed nested entries instead of leaking a TypeError", () => {
    expect(() => mapEspnRoster({ teams: [{ id: 1, roster: { entries: [null] } }] }, league))
      .toThrowError(new ProviderError("INVALID_PAYLOAD", "ESPN roster payload is malformed"));
  });

  it.each([
    [401, "AUTHENTICATION_REQUIRED"],
    [403, "AUTHENTICATION_REQUIRED"],
    [404, "NOT_FOUND"],
    [429, "RATE_LIMITED"],
    [503, "UNAVAILABLE"],
  ] as const)("classifies HTTP %s as %s", async (status, code) => {
    const fetchImpl = vi.fn(async () => new Response(null, { status }));
    await expect(new EspnProvider(fetchImpl).loadRoster(league)).rejects.toMatchObject({ code, status });
  });

  it("classifies invalid JSON separately from transport failure", async () => {
    const fetchImpl = vi.fn(async () => new Response("not-json", { status: 200 }));

    await expect(new EspnProvider(fetchImpl).loadRoster(league)).rejects.toMatchObject({
      code: "INVALID_PAYLOAD",
    });
  });

  it("bounds a request with a timeout", async () => {
    const fetchImpl = vi.fn((_input: RequestInfo | URL, init?: RequestInit) =>
      new Promise<Response>((_, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
      }),
    );

    await expect(new EspnProvider(fetchImpl, 1).loadRoster(league)).rejects.toMatchObject({
      code: "UNAVAILABLE",
      message: "ESPN request timed out",
    });
  });

  it("retries transient unavailability in the caller-owned policy", async () => {
    const provider = {
      loadRoster: vi.fn()
        .mockRejectedValueOnce(new ProviderError("UNAVAILABLE", "temporary"))
        // .mockRejectedValueOnce(new ProviderError("UNAVAILABLE", "temporary"))
        .mockRejectedValueOnce(new ProviderError("UNAVAILABLE", "temporary"))
        .mockResolvedValue({ league, players: [], fetchedAt: "2026-08-24T00:00:00.000Z" }),
    };
    const sleep = vi.fn(async () => undefined);

    await expect(loadRosterWithRetry(provider, league, { maxAttempts: 3, sleep }))
      .resolves.toMatchObject({ league });
    expect(provider.loadRoster).toHaveBeenCalledTimes(3);
    expect(sleep).toHaveBeenCalledTimes(2);
  });

  it("does not retry rate limits or authentication failures", async () => {
    const provider = {
      loadRoster: vi.fn().mockRejectedValue(new ProviderError("RATE_LIMITED", "slow down", 429)),
    };

    await expect(loadRosterWithRetry(provider, league, { sleep: vi.fn(async () => undefined) }))
      .rejects.toMatchObject({ code: "RATE_LIMITED" });
    expect(provider.loadRoster).toHaveBeenCalledTimes(1);
  });

  it("allows another provider to implement the same port", async () => {
    const fakeProvider: ProviderPort = {
      loadRoster: async (league) => ({
        league,
        players: [
          {
            id: "fake:42",
            name: "Example Player",
            position: "WR",
            team: "TEST",
            source: {
              provider: "fake",
              playerId: "42",
            },
          },
        ],
        fetchedAt: "2026-09-06T00:00:00.000Z",
      }),
    };

    const roster = await fakeProvider.loadRoster(league);

    expect(roster.players[0]).toMatchObject({
      id: "fake:42",
      name: "Example Player",
      position: "WR",
    });
  });
});
