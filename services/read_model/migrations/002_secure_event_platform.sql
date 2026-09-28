CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS app_users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS provider_connections (
  connection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  external_account_id TEXT NOT NULL,
  encrypted_credentials BYTEA NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, provider, external_account_id)
);

CREATE TABLE IF NOT EXISTS user_fantasy_leagues (
  user_id UUID NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  league_id TEXT NOT NULL,
  season INTEGER NOT NULL,
  name TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, provider, league_id, season)
);

CREATE TABLE IF NOT EXISTS user_fantasy_teams (
  user_id UUID NOT NULL,
  provider TEXT NOT NULL,
  league_id TEXT NOT NULL,
  season INTEGER NOT NULL,
  team_id TEXT NOT NULL,
  name TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, provider, league_id, season, team_id),
  FOREIGN KEY (user_id, provider, league_id, season)
    REFERENCES user_fantasy_leagues(user_id, provider, league_id, season)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_roster_players (
  user_id UUID NOT NULL,
  provider TEXT NOT NULL,
  league_id TEXT NOT NULL,
  season INTEGER NOT NULL,
  team_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  player_name TEXT NOT NULL,
  position TEXT NOT NULL,
  pro_team TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, provider, league_id, season, team_id, player_id),
  FOREIGN KEY (user_id, provider, league_id, season, team_id)
    REFERENCES user_fantasy_teams(user_id, provider, league_id, season, team_id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_inbox (
  inbox_id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  source_event_id TEXT NOT NULL,
  game_id TEXT NOT NULL,
  payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING',
  attempts INTEGER NOT NULL DEFAULT 0,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed_at TIMESTAMPTZ,
  error TEXT,
  UNIQUE (source, source_event_id)
);

CREATE TABLE IF NOT EXISTS player_score_projections (
  user_id UUID NOT NULL,
  provider TEXT NOT NULL,
  league_id TEXT NOT NULL,
  season INTEGER NOT NULL,
  team_id TEXT NOT NULL,
  player_id TEXT NOT NULL,
  fantasy_points DOUBLE PRECISION NOT NULL DEFAULT 0,
  last_event_id TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, provider, league_id, season, team_id, player_id),
  FOREIGN KEY (user_id, provider, league_id, season, team_id, player_id)
    REFERENCES user_roster_players(user_id, provider, league_id, season, team_id, player_id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_outbox (
  outbox_id BIGSERIAL PRIMARY KEY,
  topic TEXT NOT NULL,
  aggregate_key TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  published_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS event_inbox_pending
  ON event_inbox (status, received_at) WHERE status = 'PENDING';
CREATE INDEX IF NOT EXISTS event_outbox_unpublished
  ON event_outbox (outbox_id) WHERE published_at IS NULL;
