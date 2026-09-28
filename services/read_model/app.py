from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from dashboard import (
    DashboardHub,
    DashboardRepository,
    DashboardSnapshot,
    EspnRosterSync,
    FantasyTeam,
    RosterPlayer,
)
from events import (
    CanonicalPlay,
    EventPipeline,
    InMemoryEventPipeline,
    OutboxPublisher,
    PostgresEventPipeline,
    RedisStreamBroker,
    RedisStreamConsumer,
)
from observability import configure_observability
from security import (
    CredentialCipher,
    InMemorySecurityStore,
    LoginRequest,
    Passwords,
    PostgresSecurityStore,
    ProviderConnectionRequest,
    ProviderConnectionSummary,
    RegisterRequest,
    SecurityStore,
    TokenManager,
    TokenResponse,
)

load_dotenv(Path(__file__).with_name(".env"))

LOCAL_USER_ID = "00000000-0000-0000-0000-000000000001"


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
        self.fantasy_teams: dict[tuple[str, str, str], FantasyTeam] = {}
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

    async def upsert_espn_roster(self, user_id: str, roster: EspnRosterSync) -> None:
        await self._check()
        self.fantasy_teams[(user_id, roster.league_id, roster.team_id)] = FantasyTeam(
            league_id=roster.league_id,
            team_id=roster.team_id,
            league_name=roster.league_name,
            team_name=roster.team_name,
            season=roster.season,
            players=roster.players,
        )

    async def dashboard(self, user_id: str) -> DashboardSnapshot:
        await self._check()
        teams = sorted(
            (
                team
                for (owner, _, _), team in self.fantasy_teams.items()
                if owner == user_id
            ),
            key=lambda team: (team.league_name, team.team_name),
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

    async def upsert_espn_roster(self, user_id: str, roster: EspnRosterSync) -> None:
        pool = await self._pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    """INSERT INTO user_fantasy_leagues
                           (user_id, provider, league_id, season, name)
                       VALUES ($1::uuid, 'espn', $2, $3, $4)
                       ON CONFLICT (user_id, provider, league_id, season)
                       DO UPDATE SET name = EXCLUDED.name, updated_at = NOW()""",
                    user_id,
                    roster.league_id,
                    roster.season,
                    roster.league_name,
                )
                await connection.execute(
                    """INSERT INTO user_fantasy_teams
                           (user_id, provider, league_id, season, team_id, name)
                       VALUES ($1::uuid, 'espn', $2, $3, $4, $5)
                       ON CONFLICT (user_id, provider, league_id, season, team_id)
                       DO UPDATE SET name = EXCLUDED.name, updated_at = NOW()""",
                    user_id,
                    roster.league_id,
                    roster.season,
                    roster.team_id,
                    roster.team_name,
                )
                if roster.players:
                    await connection.executemany(
                        """INSERT INTO user_roster_players
                               (user_id, provider, league_id, season, team_id, player_id,
                                player_name, position, pro_team)
                           VALUES ($1::uuid, 'espn', $2, $3, $4, $5, $6, $7, $8)
                           ON CONFLICT
                               (user_id, provider, league_id, season, team_id, player_id)
                           DO UPDATE SET player_name = EXCLUDED.player_name,
                                         position = EXCLUDED.position,
                                         pro_team = EXCLUDED.pro_team,
                                         updated_at = NOW()""",
                        [
                            (
                                user_id,
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
                await connection.execute(
                    """DELETE FROM user_roster_players
                       WHERE user_id = $1::uuid AND provider = 'espn' AND league_id = $2
                         AND season = $3 AND team_id = $4
                         AND NOT (player_id = ANY($5::text[]))""",
                    user_id,
                    roster.league_id,
                    roster.season,
                    roster.team_id,
                    [player.player_id for player in roster.players],
                )

    async def dashboard(self, user_id: str) -> DashboardSnapshot:
        rows = await (await self._pool()).fetch(
            """SELECT l.league_id, l.season, l.name AS league_name,
                      t.team_id, t.name AS team_name,
                      p.player_id, p.player_name, p.position, p.pro_team,
                      COALESCE(s.fantasy_points, 0) AS fantasy_points
               FROM user_fantasy_leagues l
               JOIN user_fantasy_teams t
                 USING (user_id, provider, league_id, season)
               LEFT JOIN user_roster_players p
                 USING (user_id, provider, league_id, season, team_id)
               LEFT JOIN player_score_projections s
                 USING (user_id, provider, league_id, season, team_id, player_id)
               WHERE l.user_id = $1::uuid AND l.provider = 'espn'
               ORDER BY l.name, t.name, p.player_name""",
            user_id,
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
                team.points += row["fantasy_points"]
        return DashboardSnapshot(teams=list(teams.values()))


class RedisCache(Cache):
    def __init__(self, url: str) -> None:
        self.url = url
        self._redis = None

    async def _client(self):
        if self._redis is None:
            from redis.asyncio import Redis

            self._redis = Redis.from_url(self.url, decode_responses=True)
        return self._redis

    async def get(self, key: str) -> object | None:
        import json

        value = await (await self._client()).get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: object, ttl_seconds: int) -> None:
        import json

        await (await self._client()).set(key, json.dumps(asdict(value)), ex=ttl_seconds)

    async def ping(self) -> bool:
        return bool(await (await self._client()).ping())

    async def client(self):
        return await self._client()


def create_configured_app() -> FastAPI:
    if os.getenv("READ_MODEL_BACKEND") != "postgres-redis":
        return create_app()
    dsn = os.environ["POSTGRES_DSN"]
    redis_url = os.environ["REDIS_URL"]
    postgres = PostgresRepository(dsn)
    if os.getenv("APP_ENV") == "production":
        for name in ("AUTH_SECRET", "PROVIDER_ENCRYPTION_KEY", "INGEST_API_KEY"):
            if not os.getenv(name):
                raise RuntimeError(f"{name} is required in production")
    token_manager = TokenManager(
        os.getenv("AUTH_SECRET", "local-auth-secret-change-me-000000000000000000")
    )
    cipher = CredentialCipher(
        os.getenv(
            "PROVIDER_ENCRYPTION_KEY",
            "local-provider-key-change-me-000000000000000",
        )
    )
    redis = RedisCache(redis_url)
    broker = RedisStreamBroker(redis.client)
    return create_app(
        postgres,
        postgres,
        redis,
        postgres,
        security_store=PostgresSecurityStore(postgres._pool),
        token_manager=token_manager,
        credential_cipher=cipher,
        event_pipeline=PostgresEventPipeline(postgres._pool),
        outbox_publisher=OutboxPublisher(postgres._pool, broker),
        stream_consumer=RedisStreamConsumer(redis.client),
        auth_required=True,
        ingest_key=os.getenv("INGEST_API_KEY", "local-ingest-key"),
    )


def create_app(
    event_repository: EventRepository | None = None,
    matchup_repository: MatchupRepository | None = None,
    cache: Cache | None = None,
    dashboard_repository: DashboardRepository | None = None,
    dashboard_hub: DashboardHub | None = None,
    security_store: SecurityStore | None = None,
    token_manager: TokenManager | None = None,
    credential_cipher: CredentialCipher | None = None,
    event_pipeline: EventPipeline | None = None,
    outbox_publisher: OutboxPublisher | None = None,
    stream_consumer: RedisStreamConsumer | None = None,
    auth_required: bool = False,
    ingest_key: str = "local-ingest-key",
) -> FastAPI:
    default_store = InMemoryStore()
    events = event_repository or default_store
    matchups = matchup_repository or default_store
    read_cache = cache or default_store
    dashboards = dashboard_repository or default_store
    hub = dashboard_hub or DashboardHub()
    security = security_store or InMemorySecurityStore()
    tokens = token_manager or TokenManager("local-development-auth-secret-32chars")
    cipher = credential_cipher or CredentialCipher(
        "local-development-provider-secret-32chars"
    )
    pipeline = event_pipeline or InMemoryEventPipeline()
    passwords = Passwords()
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        tasks: list[asyncio.Task[None]] = []
        background_logger = logging.getLogger("fantasy_hud.background")

        async def publish_outbox() -> None:
            while True:
                try:
                    await outbox_publisher.publish_pending()
                    await asyncio.sleep(0.25)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    background_logger.exception("outbox publish failed")
                    await asyncio.sleep(1)

        async def consume_stream() -> None:
            while True:
                try:
                    await stream_consumer.run(hub.publish_delta)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    background_logger.exception("stream consume failed")
                    await asyncio.sleep(1)

        if outbox_publisher:
            tasks.append(asyncio.create_task(publish_outbox()))
        if stream_consumer:
            tasks.append(asyncio.create_task(consume_stream()))
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(
        title="Fantasy HUD Read Model", version="0.2.0", lifespan=lifespan
    )
    configure_observability(app)
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

    async def current_user(authorization: str | None = Header(default=None)) -> str:
        if not auth_required:
            return LOCAL_USER_ID
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="bearer token required",
            )
        try:
            return tokens.verify(authorization.removeprefix("Bearer "))
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or expired token",
            ) from error

    @app.post("/accounts/register", response_model=TokenResponse, status_code=201)
    async def register(request: RegisterRequest) -> TokenResponse:
        try:
            user = await security.create_user(request.email, passwords.hash(request.password))
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return TokenResponse(access_token=tokens.issue(user))

    @app.post("/auth/token", response_model=TokenResponse)
    async def login(request: LoginRequest) -> TokenResponse:
        user = await security.find_user_by_email(request.email)
        if user is None or not passwords.verify(user.password_hash, request.password):
            raise HTTPException(status_code=401, detail="invalid credentials")
        return TokenResponse(access_token=tokens.issue(user))

    @app.post(
        "/provider-connections",
        response_model=ProviderConnectionSummary,
        status_code=201,
    )
    async def save_provider_connection(
        request: ProviderConnectionRequest,
        user_id: str = Depends(current_user),
    ) -> ProviderConnectionSummary:
        encrypted = cipher.encrypt(json.dumps(request.credentials).encode())
        return await security.save_connection(
            user_id,
            request.provider,
            request.external_account_id,
            encrypted,
        )

    @app.get("/provider-connections", response_model=list[ProviderConnectionSummary])
    async def provider_connections(
        user_id: str = Depends(current_user),
    ) -> list[ProviderConnectionSummary]:
        return await security.list_connections(user_id)

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
    async def dashboard(user_id: str = Depends(current_user)) -> DashboardSnapshot:
        try:
            return await dashboards.dashboard(user_id)
        except DependencyUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post("/sync/espn-roster")
    async def sync_espn_roster(
        roster: EspnRosterSync,
        user_id: str = Depends(current_user),
    ) -> DashboardSnapshot:
        try:
            await dashboards.upsert_espn_roster(user_id, roster)
            snapshot = await dashboards.dashboard(user_id)
            await hub.publish(user_id, snapshot)
            return snapshot
        except DependencyUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.websocket("/ws/dashboard")
    async def dashboard_socket(websocket: WebSocket) -> None:
        if auth_required:
            token = websocket.query_params.get("token")
            try:
                user_id = tokens.verify(token or "")
            except Exception:
                await websocket.close(code=4401)
                return
        else:
            user_id = LOCAL_USER_ID
        await websocket.accept()
        subscriber = hub.subscribe(user_id)
        queue = await anext(subscriber)
        try:
            await websocket.send_json(
                hub.snapshot_message(await dashboards.dashboard(user_id))
            )
            while True:
                await websocket.send_json(await queue.get())
        except WebSocketDisconnect:
            pass
        finally:
            await subscriber.aclose()

    @app.post("/ingest/events")
    async def ingest_event(
        play: CanonicalPlay,
        x_ingest_key: str | None = Header(default=None),
    ):
        if not x_ingest_key or not hmac.compare_digest(x_ingest_key, ingest_key):
            raise HTTPException(status_code=401, detail="invalid ingest key")
        return await pipeline.ingest(play)

    return app


app = create_configured_app()
