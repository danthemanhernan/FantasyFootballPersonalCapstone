# Fantasy Football ecosystem architecture

## Current integrated slice

```text
ESPN browser session
  → Chrome extension provider adapter
  → canonical roster
  → POST /sync/espn-roster
  → FastAPI application
      ├─ Postgres durable league/team/roster state
      ├─ Redis cache/readiness dependency
      └─ WebSocket dashboard snapshots
          ├─ standalone web command center
          └─ YouTube DOM overlay
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
| Push hub | local snapshot fan-out | API process memory | Redis Streams, NATS, or Kafka |
| Vision | identity fusion and confidence policy | tested Python module | GPU worker/service |

## What is real now

- A real private ESPN roster can be loaded from the signed-in browser.
- One selected ESPN team is normalized and stored durably in Postgres.
- Multiple leagues/teams can coexist in the database and dashboard.
- The standalone dashboard receives snapshots over WebSockets.
- The YouTube content script renders a roster HUD and synthetic marker boxes.
- Vision identity fusion abstains on ambiguous or low-confidence detections.

## What is still simulated or deferred

- Live NFL play-by-play and scoring updates are still fixture/simulator driven.
- The browser marker demo uses synthetic boxes, not video inference.
- ESPN league/team display names are placeholders because the current canonical
  roster contract does not retain them.
- Authentication and user tenancy are not yet enabled.
- WebSocket fan-out is single-process and not horizontally scalable.

## Next production increments

1. Add accounts, encrypted provider connections, and per-user authorization.
2. Add a permitted live play-by-play source and durable canonical event inbox.
3. Project scoring updates transactionally and publish deltas through a broker.
4. Add metrics, structured logs, traces, CI, migrations, and backup drills.
5. Train/evaluate detection, tracking, team classification, and jersey OCR on
   authorized football footage before connecting it to the live overlay.
