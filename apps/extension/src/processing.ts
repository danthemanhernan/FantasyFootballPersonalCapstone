import { scorePlayer, standardScoring, type PlayerStats, type ScoringRules } from "./scoring";
import type { CanonicalFootballEvent } from "./ingestion";

export type PlayerProjection = {
  stats: PlayerStats;
  fantasyPoints: number;
};

export type AuditStatus = "PROCESSED" | "DUPLICATE" | "DEAD_LETTER";

export type AuditRecord = {
  eventId: string;
  gameId: string;
  cursor: number;
  status: AuditStatus;
  attempts: number;
  reason?: string;
};

export type DeadLetter = {
  event: CanonicalFootballEvent;
  reason: string;
};

export type ProcessingResult = {
  projection: Readonly<Record<string, PlayerProjection>>;
  audit: readonly AuditRecord[];
  deadLetters: readonly DeadLetter[];
};

export type ProcessingOptions = {
  knownPlayerIds: ReadonlySet<string>;
  scoringRules?: ScoringRules;
  maxAttempts?: number;
  /** Number of injected transient failures before a given event succeeds. */
  transientFailures?: ReadonlyMap<string, number>;
};

const emptyStats = (): PlayerStats => ({
  passingYards: 0,
  rushingYards: 0,
  receivingYards: 0,
  receptions: 0,
  passingTouchdowns: 0,
  rushingTouchdowns: 0,
  receivingTouchdowns: 0,
  interceptions: 0,
});

const cloneProjection = (projection: Record<string, PlayerProjection>) =>
  Object.fromEntries(Object.entries(projection).map(([id, value]) => [id, {
    stats: { ...value.stats },
    fantasyPoints: value.fantasyPoints,
  }]));

/** In-memory stand-in for a durable inbox, projection store, and audit log. */
export class InMemoryProcessingStore {
  readonly processedEventIds = new Set<string>();
  readonly projection: Record<string, PlayerProjection> = {};
  readonly audit: AuditRecord[] = [];
  readonly deadLetters: DeadLetter[] = [];
}

const orderedEvents = (events: readonly CanonicalFootballEvent[]) => {
  const grouped = new Map<string, CanonicalFootballEvent[]>();
  for (const event of events) {
    const gameEvents = grouped.get(event.game_id) ?? [];
    gameEvents.push(event);
    grouped.set(event.game_id, gameEvents);
  }

  return [...grouped.values()]
    .flatMap((gameEvents) => [...gameEvents].sort((a, b) => a.source.cursor - b.source.cursor));
};

const applyEvent = (
  event: CanonicalFootballEvent,
  projection: Record<string, PlayerProjection>,
  scoringRules: ScoringRules,
) => {
  const current = projection[event.payload.player_id] ?? {
    stats: emptyStats(),
    fantasyPoints: 0,
  };
  const stats = { ...current.stats };

  if (event.event_type === "RECEPTION") {
    stats.receivingYards += event.payload.yards ?? 0;
    stats.receptions += 1;
  } else if (event.event_type === "TOUCHDOWN") {
    stats.receivingTouchdowns += 1;
  }

  projection[event.payload.player_id] = {
    stats,
    fantasyPoints: scorePlayer(scoringRules, stats).total,
  };
};

/** Process events in sequence order. Repeated event IDs become no-ops. */
export const processEvents = (
  events: readonly CanonicalFootballEvent[],
  store: InMemoryProcessingStore,
  { knownPlayerIds, scoringRules = standardScoring, maxAttempts = 3, transientFailures = new Map() }: ProcessingOptions,
): ProcessingResult => {
  const attemptsLimit = Math.max(1, Math.floor(maxAttempts));
  for (const event of orderedEvents(events)) {
    if (store.processedEventIds.has(event.event_id)) {
      store.audit.push({
        eventId: event.event_id,
        gameId: event.game_id,
        cursor: event.source.cursor,
        status: "DUPLICATE",
        attempts: 0,
      });
      continue;
    }

    if (!knownPlayerIds.has(event.payload.player_id)) {
      const reason = `Unknown player identifier: ${event.payload.player_id}`;
      store.deadLetters.push({ event, reason });
      store.audit.push({ eventId: event.event_id, gameId: event.game_id, cursor: event.source.cursor, status: "DEAD_LETTER", attempts: 0, reason });
      continue;
    }

    let attempts = 0;
    let succeeded = false;
    const injectedFailures = Math.max(0, transientFailures.get(event.event_id) ?? 0);
    while (attempts < attemptsLimit) {
      attempts += 1;
      if (attempts <= injectedFailures) continue;
      applyEvent(event, store.projection, scoringRules);
      succeeded = true;
      break;
    }

    if (!succeeded) {
      const reason = `Transient processing failed after ${attempts} attempts`;
      store.deadLetters.push({ event, reason });
      store.audit.push({ eventId: event.event_id, gameId: event.game_id, cursor: event.source.cursor, status: "DEAD_LETTER", attempts, reason });
      continue;
    }

    store.processedEventIds.add(event.event_id);
    store.audit.push({ eventId: event.event_id, gameId: event.game_id, cursor: event.source.cursor, status: "PROCESSED", attempts });
  }

  return {
    projection: cloneProjection(store.projection),
    audit: [...store.audit],
    deadLetters: [...store.deadLetters],
  };
};
