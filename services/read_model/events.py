from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import httpx
from pydantic import BaseModel, Field


class CanonicalPlay(BaseModel):
    source: str
    source_event_id: str
    game_id: str
    player_id: str
    event_type: str = Field(pattern=r"^(RECEPTION|TOUCHDOWN)$")
    yards: int | None = Field(default=None, ge=0)
    cursor: int = Field(ge=0)
    occurred_at: datetime


class IngestResult(BaseModel):
    accepted: bool
    duplicate: bool
    projection_updates: int


def fantasy_points(play: CanonicalPlay) -> float:
    if play.event_type == "RECEPTION":
        return 1.0 + (play.yards or 0) * 0.1
    if play.event_type == "TOUCHDOWN":
        return 6.0
    return 0.0


class EventPipeline(Protocol):
    async def ingest(self, play: CanonicalPlay) -> IngestResult: ...


class InMemoryEventPipeline(EventPipeline):
    def __init__(self) -> None:
        self.processed: set[tuple[str, str]] = set()
        self.points: dict[str, float] = {}
        self.outbox: list[dict[str, object]] = []

    async def ingest(self, play: CanonicalPlay) -> IngestResult:
        key = (play.source, play.source_event_id)
        if key in self.processed:
            return IngestResult(accepted=False, duplicate=True, projection_updates=0)
        self.processed.add(key)
        self.points[play.player_id] = self.points.get(play.player_id, 0) + fantasy_points(play)
        self.outbox.append({"topic": "projection.updated", "play": play.model_dump(mode="json")})
        return IngestResult(accepted=True, duplicate=False, projection_updates=1)


class PostgresEventPipeline(EventPipeline):
    def __init__(self, pool_provider) -> None:
        self.pool_provider = pool_provider

    async def ingest(self, play: CanonicalPlay) -> IngestResult:
        pool = await self.pool_provider()
        async with pool.acquire() as connection:
            async with connection.transaction():
                inbox = await connection.fetchrow(
                    """INSERT INTO event_inbox
                           (source, source_event_id, game_id, payload)
                       VALUES ($1, $2, $3, $4::jsonb)
                       ON CONFLICT (source, source_event_id) DO NOTHING
                       RETURNING inbox_id""",
                    play.source,
                    play.source_event_id,
                    play.game_id,
                    json.dumps(play.model_dump(mode="json")),
                )
                if inbox is None:
                    return IngestResult(accepted=False, duplicate=True, projection_updates=0)

                await connection.execute(
                    """INSERT INTO canonical_events
                           (event_id, game_id, player_id, event_type, yards, cursor,
                            occurred_at, received_at)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                       ON CONFLICT (event_id) DO NOTHING""",
                    f"{play.source}:{play.source_event_id}",
                    play.game_id,
                    play.player_id,
                    play.event_type,
                    play.yards,
                    play.cursor,
                    play.occurred_at,
                )
                points = fantasy_points(play)
                rows = await connection.fetch(
                    """SELECT r.user_id, r.provider, r.league_id, r.season,
                              r.team_id, r.player_id
                       FROM user_roster_players r
                       LEFT JOIN player_identity_links i
                         ON i.provider = r.provider
                        AND i.external_player_id = r.player_id
                       WHERE r.player_id = $1 OR i.canonical_player_id = $1""",
                    play.player_id,
                )
                for row in rows:
                    await connection.execute(
                        """INSERT INTO player_score_projections
                               (user_id, provider, league_id, season, team_id,
                                player_id, fantasy_points, last_event_id)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                           ON CONFLICT
                               (user_id, provider, league_id, season, team_id, player_id)
                           DO UPDATE SET
                               fantasy_points = player_score_projections.fantasy_points
                                                + EXCLUDED.fantasy_points,
                               last_event_id = EXCLUDED.last_event_id,
                               updated_at = NOW()""",
                        row["user_id"],
                        row["provider"],
                        row["league_id"],
                        row["season"],
                        row["team_id"],
                        row["player_id"],
                        points,
                        play.source_event_id,
                    )
                    await connection.execute(
                        """INSERT INTO event_outbox (topic, aggregate_key, payload)
                           VALUES ('projection.updated', $1, $2::jsonb)""",
                        str(row["user_id"]),
                        json.dumps(
                            {
                                "user_id": str(row["user_id"]),
                                "league_id": row["league_id"],
                                "team_id": row["team_id"],
                                "player_id": row["player_id"],
                                "points_delta": points,
                                "event_id": play.source_event_id,
                            }
                        ),
                    )
                await connection.execute(
                    """UPDATE event_inbox
                       SET status = 'PROCESSED', processed_at = NOW(), attempts = attempts + 1
                       WHERE inbox_id = $1""",
                    inbox["inbox_id"],
                )
                return IngestResult(
                    accepted=True, duplicate=False, projection_updates=len(rows)
                )


class Broker(Protocol):
    async def publish(self, topic: str, payload: dict[str, object]) -> None: ...


class RedisStreamBroker(Broker):
    def __init__(self, redis_client_provider) -> None:
        self.redis_client_provider = redis_client_provider

    async def publish(self, topic: str, payload: dict[str, object]) -> None:
        client = await self.redis_client_provider()
        await client.xadd(topic, {"payload": json.dumps(payload)}, maxlen=10_000)


class RedisStreamConsumer:
    """Bridges durable projection deltas into this API process's WebSocket hub."""

    def __init__(self, redis_client_provider, topic: str = "projection.updated") -> None:
        self.redis_client_provider = redis_client_provider
        self.topic = topic

    async def run(self, callback) -> None:
        client = await self.redis_client_provider()
        cursor = "$"
        while True:
            batches = await client.xread({self.topic: cursor}, block=1_000, count=100)
            for _, messages in batches:
                for message_id, fields in messages:
                    cursor = message_id
                    raw_payload = fields.get("payload") or fields.get(b"payload")
                    if isinstance(raw_payload, bytes):
                        raw_payload = raw_payload.decode()
                    payload = json.loads(raw_payload)
                    await callback(str(payload["user_id"]), payload)


class OutboxPublisher:
    def __init__(self, pool_provider, broker: Broker) -> None:
        self.pool_provider = pool_provider
        self.broker = broker

    async def publish_pending(self, limit: int = 100) -> int:
        pool = await self.pool_provider()
        rows = await pool.fetch(
            """SELECT outbox_id, topic, payload FROM event_outbox
               WHERE published_at IS NULL ORDER BY outbox_id LIMIT $1""",
            limit,
        )
        published = 0
        for row in rows:
            raw_payload = row["payload"]
            payload = (
                json.loads(raw_payload)
                if isinstance(raw_payload, str)
                else dict(raw_payload)
            )
            await self.broker.publish(row["topic"], payload)
            await pool.execute(
                "UPDATE event_outbox SET published_at = NOW() WHERE outbox_id = $1",
                row["outbox_id"],
            )
            published += 1
        return published


@dataclass
class SportradarConnector:
    api_key: str
    access_level: str = "trial"
    base_url: str = "https://api.sportradar.com/nfl/official"

    async def fetch_game_play_by_play(self, game_id: str) -> dict[str, object]:
        url = f"{self.base_url}/{self.access_level}/v7/en/games/{game_id}/pbp.json"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers={"x-api-key": self.api_key})
            response.raise_for_status()
            return response.json()
