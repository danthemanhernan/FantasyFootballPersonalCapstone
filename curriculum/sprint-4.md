# Sprint 4 — Backend read model

## Outcome

Shared matchup and event projections are available through a dependency-injected
FastAPI read service with explicit HTTP contracts and dependency-aware health.

## Starting point

Read `curriculum/versions/V6.md`, `docs/v6-backend-read-model-design.md`, and
`learning/notes/v6-backend-read-model-lab.md`.

## Concepts

- Async request handlers
- REST resource contracts
- Repository ports
- Cache-aside reads and TTLs
- Source of truth
- Liveness versus readiness
- Dependency failure and 503 semantics

## Exercises

1. Run the FastAPI tests with the in-memory adapters.
2. Inject a dependency outage and compare liveness/readiness.
3. Exercise matchup cache hit and cache miss paths.
4. Exercise event limits and invalid query values.
5. Replace the in-memory repository with a fake slow repository and observe
   that route contracts remain stable.

## Definition of done

- Health endpoints distinguish process liveness from dependency readiness.
- Matchup and event endpoints return stable contracts.
- Repository and cache dependencies are behind protocols.
- Tests inject outage, missing-resource, cache, and slow-dependency behavior.
- Postgres and Redis remain clearly identified as the next infrastructure step.

## Reflection

If the cache contains stale matchup points but Postgres has newer points, which
one is authoritative and how should the system repair the cache?
