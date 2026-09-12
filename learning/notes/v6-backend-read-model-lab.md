# V6 learning lab: backend read models

V5 made event processing reliable in one process. V6 moves shared state behind
an HTTP service so multiple clients can read the same projections.

## Learning goals

- Distinguish liveness from readiness.
- Understand repository and cache ports.
- Explain cache-aside behavior and source-of-truth rules.
- Treat HTTP response shapes as contracts.
- Inject dependency outages and slow paths without external infrastructure.

## Deep dive: why a read model?

The browser popup is a client, not the ideal owner of shared league state. A
backend read model gives the HUD, future mobile clients, and other consumers a
common view:

```text
events → projection → read model API → clients
```

The service serves reads. Later versions can add authenticated writes and push
updates without making every client understand storage details.

## Deep dive: liveness versus readiness

`/health/live` asks whether the process is alive. It should be cheap and should
not fail merely because Postgres or Redis is down.

`/health/ready` asks whether the process can serve useful traffic. It checks a
dependency and returns `503 Service Unavailable` when that dependency cannot
respond.

Restarting a healthy process because a database is temporarily unavailable can
make recovery worse. Readiness lets orchestration stop traffic without
confusing process failure with dependency failure.

## Deep dive: repository and cache

The repository is the authoritative read source. The cache is an optimization.
With cache-aside:

1. Try the cache.
2. On a miss, read the repository.
3. Put the result in the cache with a TTL.
4. Return the result.

If the cache is empty, the system can still work. If the repository is down,
the service cannot reconstruct a missing matchup from cache alone unless a
cached value exists.

## Exercises

From `services/read_model`, run:

```bash
uv run --group test pytest
```

For the integration experiment, start the local dependencies from the
repository root:

```bash
docker compose -f infra/v6/docker-compose.yml up -d
cp services/read_model/.env.example services/read_model/.env
```

The service reads its local `.env` through `python-dotenv`, so the application
command does not need inline connection strings or backend flags.

The Postgres and Redis containers are deliberately separate from the FastAPI
process. Stop them with `docker compose -f infra/v6/docker-compose.yml down`;
use `down -v` only when you intend to remove the local data volumes.

Then try:

1. Set `store.available = False`. Compare `/health/live` and `/health/ready`.
2. Request `/matchups/missing`. Distinguish a 404 from a dependency outage.
3. Request `/games/demo-001/events?limit=1`, then try `limit=0` and `limit=501`.
4. Set `store.delay_seconds = 0.1` and observe that the HTTP contract remains
   unchanged even though the dependency is slow.
5. Remove the cache value and request the matchup twice. Identify the cache
   miss, repository read, and cache fill.
6. Run the service in `postgres-redis` mode and compare the endpoint responses
   with in-memory mode.

## Checkpoint questions

- Why should liveness avoid checking Postgres?
- Which system is authoritative when the cache and repository disagree?
- What should a client do with a 503 versus a 404?
- Why are repository protocols useful before Postgres exists?
- What information would you add to a production health response without
  exposing secrets?

## Further reading

- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [FastAPI response status codes](https://fastapi.tiangolo.com/tutorial/response-status-code/)
- [Redis cache-aside pattern](https://redis.io/docs/latest/develop/use/patterns/)
- [PostgreSQL transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [Kubernetes liveness, readiness, and startup probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/)
