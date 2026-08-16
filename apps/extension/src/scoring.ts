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
