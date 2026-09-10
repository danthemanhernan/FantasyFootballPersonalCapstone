# V6 backend read model design

## Goal

Move shared matchup and event state out of the extension popup behind a small
HTTP read service.

## Boundary

```text
HTTP route → application service → repository/cache protocols
                              ├── Postgres repository (future)
                              └── Redis cache (future)
```

The lab uses `InMemoryStore` so the behavior is testable without external
services. `EventRepository`, `MatchupRepository`, and `Cache` are ports. A real
Postgres or Redis adapter can replace them without changing route contracts.

V6 now includes a Compose integration path: Postgres stores canonical events and
matchup projections; Redis provides the cache-aside layer. The containers are
local development dependencies, not a production deployment claim.

## Endpoint contract

| Endpoint | Purpose | Dependency behavior |
|---|---|---|
| `GET /health/live` | Is the process running? | Does not call dependencies |
| `GET /health/ready` | Can dependencies serve traffic? | Returns 503 if cache is unavailable |
| `GET /matchups/{id}` | Read current matchup projection | Cache-aside; 404 if absent; 503 on outage |
| `GET /games/{id}/events` | Read bounded event history | Validates `limit` from 1 to 500 |

## Cache-aside flow

```text
read matchup
  ↓
cache hit? ── yes → return cached value
  ↓ no
read repository
  ↓
write cache with TTL
  ↓
return value
```

The cache is an optimization, not the authority. The repository remains the
source of the matchup if the cache misses.

## Health semantics

Liveness answers whether the process should be restarted. Readiness answers
whether the process should receive traffic. Conflating them can cause a
dependency outage to trigger unnecessary process restarts, or can route traffic
to an instance that cannot serve useful data.

## Deliberate deferrals

Postgres schema/migrations, Redis TTL eviction, authentication, pagination
cursors, write endpoints, and production deployment are deferred. The Compose
stack proves local integration wiring, not production backup, migration,
security, or failover practices.
