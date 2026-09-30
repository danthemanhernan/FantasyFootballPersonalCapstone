# Fantasy Football ecosystem architecture

## Current integrated slice

```text
ESPN browser session
  → Chrome extension provider adapter
  → canonical roster
  → authorized POST /sync/espn-roster
  → Postgres user/league/team/roster state

canonical play source
  → authenticated event ingestion
  → Postgres inbox + event + projection + outbox transaction
  → Redis Stream
  → user-scoped WebSocket snapshot/delta
      ├─ standalone web command center
      └─ YouTube DOM overlay

FastAPI metrics → Prometheus → Grafana
Postgres analytics views ──────────┘
```

The extension is the ESPN credential boundary: ESPN cookies remain in the
browser and are never persisted by the backend. Only normalized roster fields
cross into the application.

## Runtime boundaries

| Component | Responsibility | Local runtime | Cloud direction |
|---|---|---|---|
| Extension | ESPN session access and YouTube overlay | Chrome MV3 | Chrome Web Store/private distribution |
| Dashboard | Multi-league operational view | Nginx container | Static CDN/object storage |
| API | validation, reads, sync, WebSockets | FastAPI container | Container service behind TLS |
| Postgres | leagues, teams, rosters, projections | Docker volume | Managed Postgres with backups/PITR |
| Redis | cache and dependency check | Docker volume | Managed Redis |
| Push hub | user-scoped snapshots and projection deltas | Redis Streams plus API fan-out | Managed Redis Streams, NATS, or Kafka |
| Vision | identity fusion and confidence policy | tested Python module | GPU worker/service |
| Observability | service and product telemetry | Prometheus, Grafana, JSON logs, optional OTLP | Managed metrics/logs/traces |

## What is real now

- A real private ESPN roster can be loaded from the signed-in browser.
- One selected ESPN team is normalized and stored durably in Postgres.
- Multiple leagues/teams can coexist in the database and dashboard.
- The standalone dashboard receives snapshots over WebSockets.
- The YouTube content script renders a roster HUD and synthetic marker boxes.
- Vision identity fusion abstains on ambiguous or low-confidence detections.
- Accounts, Argon2 password hashes, encrypted provider connections, and
  user-scoped authorization are enabled.
- Canonical events are deduplicated in a durable inbox; score projections and
  outbox records commit transactionally.
- Projection deltas publish through Redis Streams.
- Prometheus, Grafana, structured logs, CI, checksummed migrations, and tested
  backup/restore scripts are available locally.

## What is still simulated or deferred

- Live NFL play-by-play and scoring updates are still fixture/simulator driven.
- The browser marker demo uses synthetic boxes, not video inference.
- ESPN league/team display names are placeholders because the current canonical
  roster contract does not retain them.
- The permitted live-feed connector is not active without a licensed account,
  source normalizer, and verified player-ID mappings.
- Scoring projection currently demonstrates only a small event subset, not a
  complete configurable fantasy scoring engine.
- API WebSocket fan-out remains process-local after consuming broker events;
  production still needs workload identity, rate limits, and scale testing.
- No real detector, tracker, jersey recognizer, or authorized live capture path
  is connected to the overlay.

## Next production increments

1. Close V10–V11 with calibrated probability and measured resilience evidence.
2. Execute V12–V13: freeze the vision contract and create a versioned,
   authorized evaluation corpus before choosing models.
3. Execute V14–V17: build scene gating, detection, tracking, and field geometry
   as independently measurable stages.
4. Execute V18–V21: add team, jersey, and identity evidence with calibrated
   abstention and a strict false-label budget.
5. Execute V22–V23: optimize the bounded real-time graph and replay it through
   the production broker and HUD.
6. Execute V24–V25: validate a permitted live path in shadow mode, then add
   model lifecycle, drift, canary, rollback, and release controls.
