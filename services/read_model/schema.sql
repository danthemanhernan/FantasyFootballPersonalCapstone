CREATE TABLE IF NOT EXISTS canonical_events (
  event_id TEXT PRIMARY KEY,
  game_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  yards INTEGER,
  cursor INTEGER NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL,
  received_at TIMESTAMPTZ NOT NULL,
  UNIQUE (game_id, cursor)
);

CREATE INDEX IF NOT EXISTS canonical_events_game_cursor
  ON canonical_events (game_id, cursor);

CREATE TABLE IF NOT EXISTS matchup_projections (
  matchup_id TEXT PRIMARY KEY,
  home_team TEXT NOT NULL,
  away_team TEXT NOT NULL,
  home_points DOUBLE PRECISION NOT NULL,
  away_points DOUBLE PRECISION NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO matchup_projections
  (matchup_id, home_team, away_team, home_points, away_points)
VALUES
  ('matchup-demo', 'Dan''s Dream Team', 'Sunday Scaries', 7.7, 0.0)
ON CONFLICT (matchup_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS fantasy_leagues (
  provider TEXT NOT NULL,
  league_id TEXT NOT NULL,
  season INTEGER NOT NULL,
  name TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (provider, league_id, season)
);

CREATE TABLE IF NOT EXISTS fantasy_teams (
  provider TEXT NOT NULL,
  league_id TEXT NOT NULL,
  season INTEGER NOT NULL,
  team_id TEXT NOT NULL,
  name TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (provider, league_id, season, team_id),
  FOREIGN KEY (provider, league_id, season)
    REFERENCES fantasy_leagues (provider, league_id, season)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fantasy_roster_players (
  provider TEXT NOT NULL,
  league_id TEXT NOT NULL,
  season INTEGER NOT NULL,
  team_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  player_name TEXT NOT NULL,
  position TEXT NOT NULL,
  pro_team TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (provider, league_id, season, team_id, player_id),
  FOREIGN KEY (provider, league_id, season, team_id)
    REFERENCES fantasy_teams (provider, league_id, season, team_id)
    ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS fantasy_roster_players_pro_team
  ON fantasy_roster_players (pro_team);
