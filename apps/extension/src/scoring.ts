export type ScoringRules = {
  passingYardPoints: number;
  rushingYardPoints: number;
  receivingYardPoints: number;
  receptionPoints: number;
  passingTouchdownPoints: number;
  rushingTouchdownPoints: number;
  receivingTouchdownPoints: number;
  interceptionPenalty: number;
};

export type PlayerStats = {
  passingYards: number;
  rushingYards: number;
  receivingYards: number;
  receptions: number;
  passingTouchdowns: number;
  rushingTouchdowns: number;
  receivingTouchdowns: number;
  interceptions: number;
};

export type ScoringBreakdown = {
  passingYards: number;
  rushingYards: number;
  receivingYards: number;
  receptions: number;
  passingTouchdowns: number;
  rushingTouchdowns: number;
  receivingTouchdowns: number;
  interceptions: number;
  total: number;
};

export const standardScoring: ScoringRules = {
  passingYardPoints: 0.04,
  rushingYardPoints: 0.1,
  receivingYardPoints: 0.1,
  receptionPoints: 0,
  passingTouchdownPoints: 4,
  rushingTouchdownPoints: 6,
  receivingTouchdownPoints: 6,
  interceptionPenalty: -2,
};

export const sampleStats: PlayerStats = {
  passingYards: 250,
  rushingYards: 20,
  receivingYards: 80,
  receptions: 6,
  passingTouchdowns: 2,
  rushingTouchdowns: 0,
  receivingTouchdowns: 1,
  interceptions: 1,
};

export const scorePlayer = (
  rules: ScoringRules,
  stats: PlayerStats,
): ScoringBreakdown => {
  const breakdown = {
    passingYards: stats.passingYards * rules.passingYardPoints,
    rushingYards: stats.rushingYards * rules.rushingYardPoints,
    receivingYards: stats.receivingYards * rules.receivingYardPoints,
    receptions: stats.receptions * rules.receptionPoints,
    passingTouchdowns: stats.passingTouchdowns * rules.passingTouchdownPoints,
    rushingTouchdowns: stats.rushingTouchdowns * rules.rushingTouchdownPoints,
    receivingTouchdowns: stats.receivingTouchdowns * rules.receivingTouchdownPoints,
    interceptions: stats.interceptions * rules.interceptionPenalty,
  };

  const total = Object.values(breakdown).reduce(
    (sum, points) => sum + points,
    0,
  );

  return { ...breakdown, total };
};
