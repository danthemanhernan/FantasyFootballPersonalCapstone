from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Protocol

from pydantic import BaseModel, Field


class RosterPlayer(BaseModel):
    player_id: str
    name: str
    position: str
    pro_team: str


class EspnRosterSync(BaseModel):
    league_id: str
    season: int = Field(ge=2000, le=2100)
    team_id: str
    league_name: str = "ESPN League"
    team_name: str = "My Team"
    players: list[RosterPlayer]


class FantasyTeam(BaseModel):
    league_id: str
    team_id: str
    league_name: str
    team_name: str
    season: int
    points: float = 0
    players: list[RosterPlayer]


class DashboardSnapshot(BaseModel):
    teams: list[FantasyTeam]


class DashboardRepository(Protocol):
    async def upsert_espn_roster(self, user_id: str, roster: EspnRosterSync) -> None: ...
    async def dashboard(self, user_id: str) -> DashboardSnapshot: ...


class DashboardHub:
    """In-process fan-out for local development; a broker replaces it in cloud mode."""

    def __init__(self, queue_size: int = 32) -> None:
        self.sequence = 0
        self.queue_size = queue_size
        self._subscribers: dict[asyncio.Queue[dict[str, object]], str] = {}

    async def subscribe(self, user_id: str) -> AsyncIterator[asyncio.Queue[dict[str, object]]]:
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(self.queue_size)
        self._subscribers[queue] = user_id
        try:
            yield queue
        finally:
            self._subscribers.pop(queue, None)

    def snapshot_message(self, snapshot: DashboardSnapshot) -> dict[str, object]:
        return {
            "kind": "snapshot",
            "sequence": self.sequence,
            "state": snapshot.model_dump(),
        }

    async def publish(self, user_id: str, snapshot: DashboardSnapshot) -> None:
        self.sequence += 1
        message = self.snapshot_message(snapshot)
        await self._fan_out(user_id, message)

    async def publish_delta(
        self, user_id: str, delta: dict[str, object]
    ) -> None:
        self.sequence += 1
        await self._fan_out(
            user_id,
            {"kind": "projection_delta", "sequence": self.sequence, "delta": delta},
        )

    async def _fan_out(self, user_id: str, message: dict[str, object]) -> None:
        for queue, subscriber_user_id in tuple(self._subscribers.items()):
            if subscriber_user_id != user_id:
                continue
            if queue.full():
                self._subscribers.pop(queue, None)
                continue
            queue.put_nowait(message)
