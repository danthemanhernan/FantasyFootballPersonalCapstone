import { standardScoring, type ScoringRules } from "./scoring";

export const SNAPSHOT_VERSION = 2 as const;
export const SNAPSHOT_KEY = "fantasy-hud.snapshot";

export type PersistedSnapshot = {
  version: typeof SNAPSHOT_VERSION;
  scoringRules: ScoringRules;
  simulator: { eventIndex: number };
};

export type StorageAdapter = {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
};

export const browserStorage: StorageAdapter = {
  getItem: (key) => window.localStorage.getItem(key),
  setItem: (key, value) => window.localStorage.setItem(key, value),
  removeItem: (key) => window.localStorage.removeItem(key),
};

export const defaultSnapshot = (): PersistedSnapshot => ({
  version: SNAPSHOT_VERSION,
  scoringRules: { ...standardScoring },
  simulator: { eventIndex: 0 },
});

const scoringRuleKeys: Array<keyof ScoringRules> = [
  "passingYardPoints",
  "rushingYardPoints",
  "receivingYardPoints",
  "receptionPoints",
  "passingTouchdownPoints",
  "rushingTouchdownPoints",
  "receivingTouchdownPoints",
  "interceptionPenalty",
];

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const parseRules = (value: unknown): ScoringRules | null => {
  if (!isRecord(value)) return null;
  const rules = {} as ScoringRules;
  for (const key of scoringRuleKeys) {
    if (typeof value[key] !== "number" || !Number.isFinite(value[key])) return null;
    rules[key] = value[key];
  }
  return rules;
};

const parseEventIndex = (value: unknown): number | null =>
  typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;

const parseV2 = (value: Record<string, unknown>): PersistedSnapshot | null => {
  const rules = parseRules(value.scoringRules);
  const simulator = value.simulator;
  const eventIndex = isRecord(simulator) ? parseEventIndex(simulator.eventIndex) : null;
  if (value.version !== SNAPSHOT_VERSION || !rules || eventIndex === null) return null;
  return { version: SNAPSHOT_VERSION, scoringRules: rules, simulator: { eventIndex } };
};

const migrate = (value: unknown): PersistedSnapshot | null => {
  if (!isRecord(value) || typeof value.version !== "number") return null;
  if (value.version === SNAPSHOT_VERSION) return parseV2(value);
  if (value.version !== 1) return null;

  const rules = parseRules(value.scoringRules);
  const eventIndex = parseEventIndex(value.eventIndex);
  if (!rules || eventIndex === null) return null;
  return { version: SNAPSHOT_VERSION, scoringRules: rules, simulator: { eventIndex } };
};

export const serializeSnapshot = (snapshot: PersistedSnapshot): string =>
  JSON.stringify(snapshot);

export const deserializeSnapshot = (raw: string): PersistedSnapshot | null => {
  try {
    return migrate(JSON.parse(raw));
  } catch {
    return null;
  }
};

export const loadSnapshot = (
  storage: StorageAdapter,
  key = SNAPSHOT_KEY,
): PersistedSnapshot => {
  let raw: string | null = null;
  try {
    raw = storage.getItem(key);
    if (!raw) return defaultSnapshot();
    const snapshot = deserializeSnapshot(raw);
    if (snapshot) return snapshot;
  } catch {
    // Fall through to safe defaults. Browser storage can throw on access.
  }

  try {
    if (raw !== null) storage.removeItem(key);
  } catch {
    // Quarantine is best effort; the app must remain usable in memory.
  }
  return defaultSnapshot();
};

export const saveSnapshot = (
  storage: StorageAdapter,
  snapshot: PersistedSnapshot,
  key = SNAPSHOT_KEY,
): boolean => {
  try {
    storage.setItem(key, serializeSnapshot(snapshot));
    return true;
  } catch {
    return false;
  }
};
