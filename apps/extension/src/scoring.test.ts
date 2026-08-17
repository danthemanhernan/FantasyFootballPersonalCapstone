import { describe, expect, it } from "vitest";
import {
  sampleStats,
  scorePlayer,
  standardScoring,
  type PlayerStats,
} from "./scoring";

const emptyStats: PlayerStats = {
  passingYards: 0,
  rushingYards: 0,
  receivingYards: 0,
  receptions: 0,
  passingTouchdowns: 0,
  rushingTouchdowns: 0,
  receivingTouchdowns: 0,
  interceptions: 0,
};

const statsWith = (overrides: Partial<PlayerStats>): PlayerStats => ({
  ...emptyStats,
  ...overrides,
});

const scoringCases = [
  { name: "passing yards", stats: { passingYards: 100 }, expected: 4 },
  { name: "rushing yards", stats: { rushingYards: 30 }, expected: 3 },
  { name: "receiving yards", stats: { receivingYards: 50 }, expected: 5 },
  { name: "receptions", stats: { receptions: 5 }, expected: 0 },
  { name: "passing touchdown", stats: { passingTouchdowns: 1 }, expected: 4 },
  { name: "rushing touchdown", stats: { rushingTouchdowns: 1 }, expected: 6 },
  { name: "receiving touchdown", stats: { receivingTouchdowns: 1 }, expected: 6 },
  { name: "interception", stats: { interceptions: 1 }, expected: -2 },
] satisfies Array<{
  name: string;
  stats: Partial<PlayerStats>;
  expected: number;
}>;

describe("scorePlayer", () => {
  it("returns the expected breakdown for the sample stats", () => {
    const result = scorePlayer(standardScoring, sampleStats);

    expect(result).toEqual({
      passingYards: 10,
      rushingYards: 2,
      receivingYards: 8,
      receptions: 0,
      passingTouchdowns: 8,
      rushingTouchdowns: 0,
      receivingTouchdowns: 6,
      interceptions: -2,
      total: 32,
    });
  });

  it.each(scoringCases)("scores $name correctly", ({ stats, expected }) => {
    const result = scorePlayer(standardScoring, statsWith(stats));

    expect(result.total).toBe(expected);
  });

  it("treats unspecified statistics as zero", () => {
    const result = scorePlayer(
      standardScoring,
      statsWith({ receivingYards: 50 }),
    );

    expect(result.total).toBe(5);
  });

  it("supports negative rushing yardage", () => {
    const result = scorePlayer(
      standardScoring,
      statsWith({ rushingYards: -10 }),
    );

    expect(result.total).toBe(-1);
  });
});
