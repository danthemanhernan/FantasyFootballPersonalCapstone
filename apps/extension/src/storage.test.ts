import { describe, expect, it } from "vitest";
import { standardScoring } from "./scoring";
import {
  defaultSnapshot,
  deserializeSnapshot,
  loadSnapshot,
  saveSnapshot,
  serializeSnapshot,
  type StorageAdapter,
} from "./storage";

const memoryStorage = (initial: string | null = null): StorageAdapter & { value: string | null } => {
  const state = { value: initial };
  return {
    get value() { return state.value; },
    set value(value: string | null) { state.value = value; },
    getItem: () => state.value,
    setItem: (_key, value) => { state.value = value; },
    removeItem: () => { state.value = null; },
  };
};

describe("snapshot persistence", () => {
  it("serializes and restores a valid V2 snapshot", () => {
    const storage = memoryStorage();
    const snapshot = {
      version: 2 as const,
      scoringRules: { ...standardScoring, receptionPoints: 1 },
      simulator: { eventIndex: 4 },
    };

    expect(saveSnapshot(storage, snapshot)).toBe(true);
    expect(loadSnapshot(storage)).toEqual(snapshot);
  });

  it("uses defaults when storage is missing", () => {
    expect(loadSnapshot(memoryStorage())).toEqual(defaultSnapshot());
  });

  it("quarantines corrupt JSON", () => {
    const storage = memoryStorage("{not-json");

    expect(loadSnapshot(storage)).toEqual(defaultSnapshot());
    expect(storage.value).toBeNull();
  });

  it("quarantines invalid snapshot shapes", () => {
    const storage = memoryStorage(JSON.stringify({ version: 2, scoringRules: {} }));

    expect(loadSnapshot(storage)).toEqual(defaultSnapshot());
    expect(storage.value).toBeNull();
  });

  it("migrates a valid V1 cursor into the V2 simulator shape", () => {
    const v1 = {
      version: 1,
      scoringRules: standardScoring,
      eventIndex: 9,
    };

    expect(deserializeSnapshot(JSON.stringify(v1))).toEqual({
      version: 2,
      scoringRules: standardScoring,
      simulator: { eventIndex: 9 },
    });
  });

  it("rejects unsupported versions", () => {
    expect(deserializeSnapshot(JSON.stringify({ version: 99 }))).toBeNull();
  });

  it("does not throw when saving fails", () => {
    const storage: StorageAdapter = {
      getItem: () => null,
      setItem: () => { throw new Error("quota exceeded"); },
      removeItem: () => undefined,
    };

    expect(saveSnapshot(storage, defaultSnapshot())).toBe(false);
  });

  it("does not throw when reading fails", () => {
    const storage: StorageAdapter = {
      getItem: () => { throw new Error("storage unavailable"); },
      setItem: () => undefined,
      removeItem: () => undefined,
    };

    expect(loadSnapshot(storage)).toEqual(defaultSnapshot());
  });

  it("round-trips through the explicit serializer", () => {
    const snapshot = defaultSnapshot();
    expect(deserializeSnapshot(serializeSnapshot(snapshot))).toEqual(snapshot);
  });
});
