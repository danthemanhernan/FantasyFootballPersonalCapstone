import type { PlayerStats } from "./scoring";
import { scorePlayer, standardScoring } from "./scoring";
import type { FootballEvent, Player, SimulatedEvent } from "./types";

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

export const samplePlayers: Player[] = [
  { id: "purdy", name: "Brock Purdy", position: "QB", team: "SF", stats: emptyStats(), fantasyPoints: 0 },
  { id: "kittle", name: "George Kittle", position: "TE", team: "SF", stats: emptyStats(), fantasyPoints: 0 },
  { id: "danh", name: "Danh Mann", position: "WR", team: "SF", stats: emptyStats(), fantasyPoints: 0 },
  { id: "mccaffrey", name: "Christian McCaffrey", position: "RB", team: "SF", stats: emptyStats(), fantasyPoints: 0 }
];

const scriptedEvents: FootballEvent[] = [
  { kind: "pass", passerId: "purdy", receiverId: "kittle", yards: 18 },
  { kind: "rush", playerId: "mccaffrey", yards: 7 },
  { kind: "pass", passerId: "purdy", receiverId: "kittle", yards: 12 },
  { kind: "touchdown", playerId: "kittle", touchdownType: "receiving", description: "Purdy finds Kittle for a 14-yard touchdown!" },
  { kind: "pass", passerId: "purdy", receiverId: "danh", yards: 18 },
  { kind: "touchdown", playerId: "kittle", touchdownType: "receiving", description: "Purdy finds Kittle for a 45-yard touchdown!" },
  { kind: "drive-end", description: "Extra point is good." }
];

export const createEvent = (event: FootballEvent, id: number): SimulatedEvent => ({
  ...event,
  id,
  clock: "Q2 08:42",
  createdAt: new Date().toISOString()
});

export const nextEvent = (index: number): SimulatedEvent =>
  createEvent(scriptedEvents[index % scriptedEvents.length], index);

export const applyEvent = (players: Player[], event: SimulatedEvent): Player[] => {
  const next = players.map((player) => ({ ...player, stats: { ...player.stats } }));
  const update = (id: string, change: Partial<PlayerStats>) => {
    const player = next.find((candidate) => candidate.id === id);
    if (!player) return;

    for (const [rawKey, rawVal] of Object.entries(change)) {
      const key = rawKey as keyof PlayerStats;
      const delta = Number(rawVal);
      if (!Number.isFinite(delta)) continue;              // skip bad values
      if (!(key in player.stats)) continue;               // skip unknown stats
      player.stats[key] = (player.stats[key] ?? 0) + delta;
    }
    player.fantasyPoints = scorePlayer(standardScoring, player.stats).total;
  };

  if (event.kind === "pass") {
    update(event.passerId, { passingYards: event.yards });
    update(event.receiverId, { receivingYards: event.yards, receptions: 1 });
  }
  if (event.kind === "rush") update(event.playerId, { rushingYards: event.yards });
  if (event.kind === "touchdown") {
    update(event.playerId, {
      [`${event.touchdownType}Touchdowns`]: 1,
    } as Partial<PlayerStats>);
  }

  return next;
};
