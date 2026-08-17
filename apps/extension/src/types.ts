import type { PlayerStats } from "./scoring";

export type Position = "QB" | "RB" | "WR" | "TE";

export type Player = {
  id: string;
  name: string;
  position: Position;
  team: string;
  stats: PlayerStats;
  fantasyPoints: number;
};

export type FootballEvent =
  | { kind: "pass"; passerId: string; receiverId: string; yards: number }
  | { kind: "rush"; playerId: string; yards: number }
  | {
      kind: "touchdown";
      playerId: string;
      touchdownType: "passing" | "rushing" | "receiving";
      description: string;
    }
  | { kind: "drive-end"; description: string };

export type SimulatedEvent = FootballEvent & {
  id: number;
  clock: string;
  createdAt: string;
};
