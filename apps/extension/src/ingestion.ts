export type CanonicalEventType = "RECEPTION" | "TOUCHDOWN";

export type CanonicalFootballEvent = {
  event_id: string;
  schema_version: 1;
  event_type: CanonicalEventType;
  occurred_at: string;
  received_at: string;
  game_id: string;
  source: { provider: "fixture"; cursor: number; raw_event_id: string };
  payload: { player_id: string; yards?: number };
};

export type RawPlay = {
  cursor: number;
  event_id: string;
  event_type: CanonicalEventType;
  player_id: string;
  yards?: number;
  occurred_at: string;
};

export type RawGameFixture = { game_id: string; events: RawPlay[] };

export class ReplayError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ReplayError";
  }
}

const eventTypes = new Set<CanonicalEventType>(["RECEPTION", "TOUCHDOWN"]);

const isValidDate = (value: unknown): value is string =>
  typeof value === "string" && !Number.isNaN(Date.parse(value));

const validatePlay: (play: unknown, index: number) => asserts play is RawPlay = (play, index) => {
  if (!isRecord(play)) {
    throw new ReplayError(`Malformed play at index ${index}`);
  }
  if (
    typeof play.event_id !== "string" || play.event_id.trim() === "" ||
    typeof play.player_id !== "string" || play.player_id.trim() === "" ||
    !eventTypes.has(play.event_type as CanonicalEventType) ||
    !isValidDate(play.occurred_at)
  ) {
    throw new ReplayError(`Malformed play at index ${index}`);
  }
  if (play.cursor !== index + 1) {
    throw new ReplayError(`Cursor gap at index ${index}: expected ${index + 1}, got ${play.cursor}`);
  }
  if (play.yards !== undefined &&
      (typeof play.yards !== "number" || !Number.isInteger(play.yards) || play.yards < 0)) {
    throw new ReplayError(`Invalid yards for play ${play.event_id}`);
  }
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const normalizePlay = (
  game: RawGameFixture,
  play: RawPlay,
  receivedAt: string,
): CanonicalFootballEvent => ({
  event_id: `${game.game_id}:${play.event_id}`,
  schema_version: 1,
  event_type: play.event_type,
  occurred_at: play.occurred_at,
  received_at: receivedAt,
  game_id: game.game_id,
  source: { provider: "fixture", cursor: play.cursor, raw_event_id: play.event_id },
  payload: { player_id: play.player_id, ...(play.yards === undefined ? {} : { yards: play.yards }) },
});

export const replayFixture = (
  fixture: unknown,
  receivedAt = "2026-08-30T00:00:00.000Z",
  knownPlayerIds: ReadonlySet<string>,
): CanonicalFootballEvent[] => {
  if (!isRecord(fixture) || typeof fixture.game_id !== "string" ||
      fixture.game_id.trim() === "" || !Array.isArray(fixture.events)) {
    throw new ReplayError("Malformed game fixture");
  }
  const events: RawPlay[] = fixture.events.map((play, index) => {
    validatePlay(play, index);
    return play;
  });
  const eventIds = new Set<string>();
  for (const play of events) {
    if (eventIds.has(play.event_id)) throw new ReplayError(`Duplicate play identifier: ${play.event_id}`);
    eventIds.add(play.event_id);
  }
  if (events.some((play) => !knownPlayerIds.has(play.player_id))) {
    throw new ReplayError("Unknown player identifier in fixture");
  }
  if (!isValidDate(receivedAt)) throw new ReplayError("Invalid replay receive time");
  const game = { game_id: fixture.game_id, events } as RawGameFixture;
  return events.map((play) => normalizePlay(game, play, receivedAt));
};
