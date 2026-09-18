# V6 read model service

This is a dependency-injected FastAPI lab. The default app uses an in-memory
store so it can run without Postgres or Redis. The `EventRepository`,
`MatchupRepository`, and `Cache` protocols are the replacement boundaries for
those infrastructure adapters in a later iteration.

## Container-backed integration mode

Start the local dependencies from the repository root:

```bash
docker compose -f infra/v6/docker-compose.yml up -d
cp .env.example .env
uv run uvicorn app:app --reload
```

`app.py` loads `services/read_model/.env` with `python-dotenv`. The local
`.env` is ignored by Git; commit configuration changes to `.env.example` only.

The named volumes persist data between restarts. `docker compose ... down`
stops containers; `down -v` also removes the V6 data volumes.

Run locally with:

```bash
uv run --group test pytest
uv run uvicorn app:app --reload
```

Endpoints:

- `GET /health/live`: process liveness only.
- `GET /health/ready`: dependency-aware readiness.
- `GET /matchups/{matchup_id}`: cache-aside matchup read.
- `GET /games/{game_id}/events?limit=100`: bounded event read.
