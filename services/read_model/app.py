from __future__ import annotations

import asyncio
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query


load_dotenv(Path(__file__).with_name(".env"))


class DependencyUnavailable(RuntimeError):
    """A repository or cache cannot currently serve the read model."""


@dataclass(frozen=True)
class Event:
    event_id: str
    game_id: str
    player_id: str
    event_type: str
    yards: int | None
    cursor: int


@dataclass(frozen=True)
class Matchup:
    matchup_id: str
    home_team: str
    away_team: str
    home_points: float
    away_points: float


class EventRepository(Protocol):
    async def list_events(self, game_id: str, limit: int) -> list[Event]: ...


class MatchupRepository(Protocol):
    async def get_matchup(self, matchup_id: str) -> Matchup | None: ...


class Cache(Protocol):
    async def get(self, key: str) -> object | None: ...
    async def set(self, key: str, value: object, ttl_seconds: int) -> None: ...
    async def ping(self) -> bool: ...


class InMemoryStore(EventRepository, MatchupRepository, Cache):
    def __init__(self) -> None:
        self.events = [
            Event("demo-001:demo-001-001", "demo-001", "player-kittle", "RECEPTION", 17, 1),
            Event("demo-001:demo-001-002", "demo-001", "player-kittle", "TOUCHDOWN", 3, 2),
        ]
        self.matchups = {
            "matchup-demo": Matchup("matchup-demo", "Dan's Dream Team", "Sunday Scaries", 7.7, 0.0),
        }
        self.cache: dict[str, object] = {}
        self.available = True
        self.delay_seconds = 0.0

    async def _check(self) -> None:
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if not self.available:
            raise DependencyUnavailable("in-memory dependency unavailable")

    async def list_events(self, game_id: str, limit: int) -> list[Event]:
        await self._check()
        return [event for event in self.events if event.game_id == game_id][:limit]

    async def get_matchup(self, matchup_id: str) -> Matchup | None:
        await self._check()
        return self.matchups.get(matchup_id)

    async def get(self, key: str) -> object | None:
        await self._check()
        return self.cache.get(key)

    async def set(self, key: str, value: object, ttl_seconds: int) -> None:
        await self._check()
        self.cache[key] = value

    async def ping(self) -> bool:
        await self._check()
        return True


class PostgresRepository(EventRepository, MatchupRepository):
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.pool = None

    async def _pool(self):
        if self.pool is None:
            import asyncpg
            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)
        return self.pool

    async def list_events(self, game_id: str, limit: int) -> list[Event]:
        rows = await (await self._pool()).fetch(
            """SELECT event_id, game_id, player_id, event_type, yards, cursor
               FROM canonical_events WHERE game_id = $1 ORDER BY cursor LIMIT $2""",
            game_id, limit,
        )
        return [Event(**dict(row)) for row in rows]

    async def get_matchup(self, matchup_id: str) -> Matchup | None:
        row = await (await self._pool()).fetchrow(
            """SELECT matchup_id, home_team, away_team, home_points, away_points
               FROM matchup_projections WHERE matchup_id = $1""",
            matchup_id,
        )
        return Matchup(**dict(row)) if row else None


class RedisCache(Cache):
    def __init__(self, url: str) -> None:
        self.url = url
        self.client = None

    async def _client(self):
        if self.client is None:
            from redis.asyncio import Redis
            self.client = Redis.from_url(self.url, decode_responses=True)
        return self.client

    async def get(self, key: str) -> object | None:
        import json
        value = await (await self._client()).get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: object, ttl_seconds: int) -> None:
        import json
        await (await self._client()).set(key, json.dumps(asdict(value)), ex=ttl_seconds)

    async def ping(self) -> bool:
        return bool(await (await self._client()).ping())


def create_configured_app() -> FastAPI:
    if os.getenv("READ_MODEL_BACKEND") != "postgres-redis":
        return create_app()
    dsn = os.environ["POSTGRES_DSN"]
    redis_url = os.environ["REDIS_URL"]
    postgres = PostgresRepository(dsn)
    return create_app(postgres, postgres, RedisCache(redis_url))


def create_app(
    event_repository: EventRepository | None = None,
    matchup_repository: MatchupRepository | None = None,
    cache: Cache | None = None,
) -> FastAPI:
    default_store = InMemoryStore()
    events = event_repository or default_store
    matchups = matchup_repository or default_store
    read_cache = cache or default_store
    app = FastAPI(title="Fantasy HUD Read Model", version="0.1.0")

    @app.get("/health/live")
    async def liveness() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready")
    async def readiness() -> dict[str, str]:
        try:
            await read_cache.ping()
        except DependencyUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return {"status": "ready"}

    @app.get("/matchups/{matchup_id}")
    async def matchup(matchup_id: str) -> Matchup:
        key = f"matchup:{matchup_id}"
        try:
            cached = await read_cache.get(key)
            if isinstance(cached, Matchup):
                return cached
            if isinstance(cached, dict):
                return Matchup(**cached)
            value = await matchups.get_matchup(matchup_id)
            if value is None:
                raise HTTPException(status_code=404, detail="matchup not found")
            await read_cache.set(key, value, ttl_seconds=15)
            return value
        except DependencyUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.get("/games/{game_id}/events")
    async def game_events(game_id: str, limit: int = Query(default=100, ge=1, le=500)) -> list[Event]:
        try:
            return await events.list_events(game_id, limit)
        except DependencyUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    return app


app = create_configured_app()
