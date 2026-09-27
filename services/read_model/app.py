from __future__ import annotations

import asyncio
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from dashboard import (
    DashboardHub,
    DashboardRepository,
    DashboardSnapshot,
    EspnRosterSync,
    FantasyTeam,
    RosterPlayer,
)

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


class InMemoryStore(EventRepository, MatchupRepository, Cache, DashboardRepository):
    def __init__(self) -> None:
        self.events = [
            Event(
                "demo-001:demo-001-001", "demo-001", "player-kittle", "RECEPTION", 17, 1
            ),
            Event(
                "demo-001:demo-001-002", "demo-001", "player-kittle", "TOUCHDOWN", 3, 2
            ),
        ]
        self.matchups = {
            "matchup-demo": Matchup(
                "matchup-demo", "Dan's Dream Team", "Sunday Scaries", 7.7, 0.0
            ),
        }
        self.cache: dict[str, object] = {}
        self.fantasy_teams: dict[tuple[str, str], FantasyTeam] = {}
        self.available = True
        self.delay_seconds = 0.1

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

    async def upsert_espn_roster(self, roster: EspnRosterSync) -> None:
        await self._check()
        self.fantasy_teams[(roster.league_id, roster.team_id)] = FantasyTeam(
            league_id=roster.league_id,
            team_id=roster.team_id,
            league_name=roster.league_name,
            team_name=roster.team_name,
            season=roster.season,
            players=roster.players,
        )

    async def dashboard(self) -> DashboardSnapshot:
        await self._check()
        teams = sorted(
            self.fantasy_teams.values(), key=lambda team: (team.league_name, team.team_name)
        )
        return DashboardSnapshot(teams=teams)


class PostgresRepository(EventRepository, MatchupRepository, DashboardRepository):
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
            game_id,
            limit,
        )
        return [Event(**dict(row)) for row in rows]

    async def get_matchup(self, matchup_id: str) -> Matchup | None:
        row = await (await self._pool()).fetchrow(
            """SELECT matchup_id, home_team, away_team, home_points, away_points
               FROM matchup_projections WHERE matchup_id = $1""",
            matchup_id,
        )
        return Matchup(**dict(row)) if row else None

    async def upsert_espn_roster(self, roster: EspnRosterSync) -> None:
        pool = await self._pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """INSERT INTO fantasy_leagues (provider, league_id, season, name)
                       VALUES ('espn', $1, $2, $3)
                       ON CONFLICT (provider, league_id, season)
                       DO UPDATE SET name = EXCLUDED.name, updated_at = NOW()""",
                    roster.league_id,
                    roster.season,
                    roster.league_name,
                )
                await connection.execute(
                    """INSERT INTO fantasy_teams
                           (provider, league_id, season, team_id, name)
                       VALUES ('espn', $1, $2, $3, $4)
                       ON CONFLICT (provider, league_id, season, team_id)
                       DO UPDATE SET name = EXCLUDED.name, updated_at = NOW()""",
                    roster.league_id,
                    roster.season,
                    roster.team_id,
                    roster.team_name,
                )
                await connection.execute(
                    """DELETE FROM fantasy_roster_players
                       WHERE provider = 'espn' AND league_id = $1
                         AND season = $2 AND team_id = $3""",
                    roster.league_id,
                    roster.season,
                    roster.team_id,
                )
                if roster.players:
                    await connection.executemany(
                        """INSERT INTO fantasy_roster_players
                               (provider, league_id, season, team_id, player_id,
                                player_name, position, pro_team)
                           VALUES ('espn', $1, $2, $3, $4, $5, $6, $7)""",
                        [
                            (
                                roster.league_id,
                                roster.season,
                                roster.team_id,
                                player.player_id,
                                player.name,
                                player.position,
                                player.pro_team,
                            )
                            for player in roster.players
                        ],
                    )

    async def dashboard(self) -> DashboardSnapshot:
        rows = await (await self._pool()).fetch(
            """SELECT l.league_id, l.season, l.name AS league_name,
                      t.team_id, t.name AS team_name,
                      p.player_id, p.player_name, p.position, p.pro_team
               FROM fantasy_leagues l
               JOIN fantasy_teams t USING (provider, league_id, season)
               LEFT JOIN fantasy_roster_players p
                 USING (provider, league_id, season, team_id)
               WHERE l.provider = 'espn'
               ORDER BY l.name, t.name, p.player_name"""
        )
        teams: dict[tuple[str, int, str], FantasyTeam] = {}
        for row in rows:
            key = (row["league_id"], row["season"], row["team_id"])
            team = teams.setdefault(
                key,
                FantasyTeam(
                    league_id=row["league_id"],
                    team_id=row["team_id"],
                    league_name=row["league_name"],
                    team_name=row["team_name"],
                    season=row["season"],
                    players=[],
                ),
            )
            if row["player_id"] is not None:
                team.players.append(
                    RosterPlayer(
                        player_id=row["player_id"],
                        name=row["player_name"],
                        position=row["position"],
                        pro_team=row["pro_team"],
                    )
                )
        return DashboardSnapshot(teams=list(teams.values()))


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
    return create_app(postgres, postgres, RedisCache(redis_url), postgres)


def create_app(
    event_repository: EventRepository | None = None,
    matchup_repository: MatchupRepository | None = None,
    cache: Cache | None = None,
    dashboard_repository: DashboardRepository | None = None,
    dashboard_hub: DashboardHub | None = None,
) -> FastAPI:
    default_store = InMemoryStore()
    events = event_repository or default_store
    matchups = matchup_repository or default_store
    read_cache = cache or default_store
    dashboards = dashboard_repository or default_store
    hub = dashboard_hub or DashboardHub()
    app = FastAPI(title="Fantasy HUD Read Model", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ],
        allow_origin_regex=r"chrome-extension://.*",
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

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
    async def game_events(
        game_id: str, limit: int = Query(default=100, ge=1, le=500)
    ) -> list[Event]:
        try:
            return await events.list_events(game_id, limit)
        except DependencyUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.get("/dashboard")
    async def dashboard() -> DashboardSnapshot:
        try:
            return await dashboards.dashboard()
        except DependencyUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post("/sync/espn-roster")
    async def sync_espn_roster(roster: EspnRosterSync) -> DashboardSnapshot:
        try:
            await dashboards.upsert_espn_roster(roster)
            snapshot = await dashboards.dashboard()
            await hub.publish(snapshot)
            return snapshot
        except DependencyUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.websocket("/ws/dashboard")
    async def dashboard_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        subscriber = hub.subscribe()
        queue = await anext(subscriber)
        try:
            await websocket.send_json(hub.snapshot_message(await dashboards.dashboard()))
            while True:
                await websocket.send_json(await queue.get())
        except WebSocketDisconnect:
            pass
        finally:
            await subscriber.aclose()

    return app


app = create_configured_app()
