CREATE TABLE IF NOT EXISTS canonical_players (
  canonical_player_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS player_identity_links (
  provider TEXT NOT NULL,
  external_player_id TEXT NOT NULL,
  canonical_player_id TEXT NOT NULL REFERENCES canonical_players(canonical_player_id),
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  verified_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (provider, external_player_id)
);

CREATE OR REPLACE VIEW analytics_team_scores AS
SELECT l.user_id,
       l.provider,
       l.league_id,
       l.season,
       l.name AS league_name,
       t.team_id,
       t.name AS team_name,
       COUNT(r.player_id) AS roster_players,
       COALESCE(SUM(s.fantasy_points), 0) AS fantasy_points,
       MAX(COALESCE(s.updated_at, t.updated_at)) AS updated_at
FROM user_fantasy_teams t
JOIN user_fantasy_leagues l USING (user_id, provider, league_id, season)
LEFT JOIN user_roster_players r
  USING (user_id, provider, league_id, season, team_id)
LEFT JOIN player_score_projections s
  USING (user_id, provider, league_id, season, team_id, player_id)
GROUP BY l.user_id, l.provider, l.league_id, l.season, l.name, t.team_id, t.name;

CREATE OR REPLACE VIEW analytics_event_pipeline_health AS
SELECT
  (SELECT COUNT(*) FROM event_inbox WHERE status = 'PENDING') AS pending_inbox,
  (SELECT EXTRACT(EPOCH FROM NOW() - MIN(received_at))
     FROM event_inbox WHERE status = 'PENDING') AS oldest_pending_seconds,
  (SELECT COUNT(*) FROM event_outbox WHERE published_at IS NULL) AS unpublished_outbox,
  (SELECT EXTRACT(EPOCH FROM NOW() - MIN(created_at))
     FROM event_outbox WHERE published_at IS NULL) AS oldest_unpublished_seconds;
