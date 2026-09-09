import { describe, expect, it } from "vitest";
import fixture from "../../../simulation/fixtures/game-001.json";
import { replayFixture, type RawGameFixture } from "./ingestion";

const gameFixture = fixture as unknown as RawGameFixture;
const knownPlayers = new Set(["player-kittle"]);

describe("deterministic fixture replay", () => {
  it("emits canonical events with source metadata", () => {
    expect(replayFixture(gameFixture, undefined, knownPlayers)).toEqual([
      {
        event_id: "demo-001:demo-001-001", schema_version: 1, event_type: "RECEPTION",
        occurred_at: "2026-08-30T20:00:01.000Z", received_at: "2026-08-30T00:00:00.000Z",
        game_id: "demo-001", source: { provider: "fixture", cursor: 1, raw_event_id: "demo-001-001" },
        payload: { player_id: "player-kittle", yards: 17 },
      },
      {
        event_id: "demo-001:demo-001-002", schema_version: 1, event_type: "TOUCHDOWN",
        occurred_at: "2026-08-30T20:00:08.000Z", received_at: "2026-08-30T00:00:00.000Z",
        game_id: "demo-001", source: { provider: "fixture", cursor: 2, raw_event_id: "demo-001-002" },
        payload: { player_id: "player-kittle", yards: 3 },
      },
    ]);
  });

  it("replaying the same page produces the same output", () => {
    expect(replayFixture(gameFixture, undefined, knownPlayers)).toEqual(replayFixture(gameFixture, undefined, knownPlayers));
  });

  it("rejects a cursor gap instead of silently reordering plays", () => {
    const broken = { ...gameFixture, events: [{ ...gameFixture.events[1], cursor: 3 }] };
    expect(() => replayFixture(broken, undefined, knownPlayers)).toThrow("Cursor gap");
  });

  it("rejects an unknown player identifier at the normalization boundary", () => {
    const broken: RawGameFixture = {
      ...gameFixture,
      events: [{ ...gameFixture.events[0], player_id: "unknown-player", cursor: 1 }],
    };
    expect(() => replayFixture(broken, undefined, knownPlayers)).toThrow("Unknown player");
  });

  it.each([
    ["bad timestamp", { ...gameFixture.events[0], occurred_at: "later" }],
    ["bad event type", { ...gameFixture.events[0], event_type: "INTERCEPTION" }],
    ["bad yards", { ...gameFixture.events[0], yards: -1 }],
    ["duplicate event id", { ...gameFixture.events[0], cursor: 2 }],
  ])("rejects %s before normalization", (_name, event) => {
    const broken = { ...gameFixture, events: [event, { ...gameFixture.events[1], cursor: 2 }] };
    expect(() => replayFixture(broken, undefined, knownPlayers)).toThrow();
  });

  it("rejects a non-object fixture instead of leaking a runtime error", () => {
    expect(() => replayFixture(null, undefined, knownPlayers)).toThrow("Malformed game fixture");
  });
});
