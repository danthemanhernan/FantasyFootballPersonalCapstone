import type { FootballEvent, Player, SimulatedEvent } from "./types";

export const samplePlayers: Player[] = [
  { id: "purdy", name: "Brock Purdy", position: "QB", team: "SF", fantasyPoints: 0 },
  { id: "kittle", name: "George Kittle", position: "TE", team: "SF", fantasyPoints: 0 },
  { id: "mccaffrey", name: "Christian McCaffrey", position: "RB", team: "SF", fantasyPoints: 0 }
];

const scriptedEvents: FootballEvent[] = [
  { kind: "pass", passerId: "purdy", receiverId: "kittle", yards: 18 },
  { kind: "rush", playerId: "mccaffrey", yards: 7 },
  { kind: "pass", passerId: "purdy", receiverId: "kittle", yards: 12 },
  { kind: "touchdown", playerId: "kittle", description: "Purdy finds Kittle for a 14-yard touchdown!" },
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
  const next = players.map((player) => ({ ...player }));
  const add = (id: string, points: number) => {
    const player = next.find((candidate) => candidate.id === id);
    if (player) player.fantasyPoints = Number((player.fantasyPoints + points).toFixed(1));
  };

  if (event.kind === "pass") {
    add(event.passerId, event.yards * 0.04);
    add(event.receiverId, event.yards * 0.1);
  }
  if (event.kind === "rush") add(event.playerId, event.yards * 0.1);
  if (event.kind === "touchdown") add(event.playerId, 6);

  return next;
};
