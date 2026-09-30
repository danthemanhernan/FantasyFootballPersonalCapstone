# Operations runbook

## Security boundaries

- Browser clients authenticate with short-lived bearer tokens. Every league,
  team, roster, projection, connection, HTTP request, and WebSocket subscription
  is scoped by `user_id`.
- Passwords use Argon2. Provider credentials are Fernet-encrypted with a key
  independent from the JWT signing secret. Production secrets must come from a
  secret manager and must be rotated; they do not belong in images or Git.
- `/ingest/events` has a separate service key. A production deployment should
  replace this static key with workload identity or mTLS and rate limiting.
- A WebSocket currently receives its short-lived token in the query string.
  Before public deployment, replace that with a single-use WebSocket ticket so
  proxies and access logs cannot retain bearer tokens.

## Event guarantees

The licensed source adapter fetches Sportradar NFL v7 play-by-play server-side.
Its API key never reaches a browser. Adapters normalize provider documents into
`CanonicalPlay`, then submit them to the durable inbox.

Provider player IDs are not interchangeable. `player_identity_links` maps ESPN
and live-feed IDs onto a canonical player ID with confidence and evidence. Until
a link is verified, the scorer can match only an identical ID and should prefer
missing an update to crediting the wrong player.

One database transaction deduplicates `(source, source_event_id)`, appends the
canonical event, updates every affected user's projection, and writes an outbox
record. A background publisher sends outbox records to a Redis Stream. Delivery
is at least once: consumers must deduplicate by event ID. A crash after publish
but before `published_at` may produce a duplicate, while a crash before publish
leaves a recoverable outbox row.

## Observability

- JSON logs include request and trace IDs; never log credentials or provider
  payloads without an allowlist/redaction layer.
- Prometheus metrics are exposed at `/metrics`.
- Set `OTEL_EXPORTER_OTLP_ENDPOINT` to export OpenTelemetry traces over HTTP.
- Alert on readiness failures, 5xx rate, p95 latency, inbox age, unpublished
  outbox age, reconnect rate, and source-to-overlay latency.

The local stack provisions Grafana with Prometheus for operational metrics and
Postgres for league/scoring analysis. Keep the React dashboard for authenticated
control and live HUD state; use Grafana for engineering telemetry and internal
exploration. For Tableau, publish curated SQL views to a read replica or
warehouse and grant a dedicated read-only role. Do not point analyst tools at
encrypted credential tables or the primary write path in production.
`analytics_team_scores` and `analytics_event_pipeline_health` are the first
curated views for Grafana/Tableau; add user/league filters and row-level policy
before exposing them beyond trusted operators.

## Migrations and backups

`migrate.py` applies immutable, checksummed migrations before the API starts.
For production, run migrations as a one-shot deployment job and take a snapshot
before destructive changes.

Run a local backup and restore drill:

```bash
scripts/backup-postgres.sh
scripts/restore-drill.sh backups/fantasy_hud_TIMESTAMP.dump
```

The drill checks the SHA-256 checksum, restores into a throwaway database,
queries the migration ledger, and drops only that test database. A real drill
also records recovery time (RTO), maximum acceptable data loss (RPO), row-count
checks, and an application smoke test. Schedule restores; an untested backup is
only a hypothesis.
