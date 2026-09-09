import { describe, expect, it } from "vitest";
import fixture from "../../../simulation/fixtures/game-001.json";
import { replayFixture, type RawGameFixture } from "./ingestion";
import { InMemoryProcessingStore, processEvents } from "./processing";

const events = replayFixture(fixture as RawGameFixture, undefined, new Set(["player-kittle"]));
const options = { knownPlayerIds: new Set(["player-kittle"]) };

describe("reliable event processing", () => {
  it("processes an event once and turns it into projection state", () => {
    const result = processEvents(events, new InMemoryProcessingStore(), options);

    expect(result.projection["player-kittle"]).toMatchObject({
      stats: { receivingYards: 17, receptions: 1, receivingTouchdowns: 1 },
      fantasyPoints: 7.7,
    });
    expect(result.audit.every((record) => record.status === "PROCESSED")).toBe(true);
  });

  it("makes repeated delivery a no-op while preserving an audit record", () => {
    const store = new InMemoryProcessingStore();
    const first = processEvents(events, store, options);
    const second = processEvents(events, store, options);

    expect(second.projection).toEqual(first.projection);
    expect(second.audit.filter((record) => record.status === "DUPLICATE")).toHaveLength(2);
  });

  it("reorders out-of-order delivery before projection", () => {
    const store = new InMemoryProcessingStore();
    const result = processEvents([events[1], events[0]], store, options);

    expect(result.audit.slice(0, 2).map((record) => record.cursor)).toEqual([1, 2]);
    expect(result.projection["player-kittle"].stats.receivingYards).toBe(17);
  });

  it("dead-letters a poison event without corrupting the projection", () => {
    const poison = { ...events[0], payload: { ...events[0].payload, player_id: "unknown" } };
    const result = processEvents([poison], new InMemoryProcessingStore(), options);

    expect(result.deadLetters).toHaveLength(1);
    expect(result.projection).toEqual({});
    expect(result.audit[0].status).toBe("DEAD_LETTER");
  });

  it("retries a transient failure with a bounded attempt count", () => {
    const injected = new Map([[events[0].event_id, 2]]);
    const result = processEvents(events.slice(0, 1), new InMemoryProcessingStore(), {
      ...options,
      transientFailures: injected,
    });

    expect(result.audit[0]).toMatchObject({ status: "PROCESSED", attempts: 3 });
  });

  it("dead-letters a transient failure after the attempt limit", () => {
    const injected = new Map([[events[0].event_id, 3]]);
    const result = processEvents(events.slice(0, 1), new InMemoryProcessingStore(), {
      ...options,
      transientFailures: injected,
      maxAttempts: 3,
    });

    expect(result.audit[0]).toMatchObject({ status: "DEAD_LETTER", attempts: 3 });
    expect(result.projection).toEqual({});
  });
});
