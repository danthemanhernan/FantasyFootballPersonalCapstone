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
    async def upsert_espn_roster(self, roster: EspnRosterSync) -> None: ...
    async def dashboard(self) -> DashboardSnapshot: ...


class DashboardHub:
    """In-process fan-out for local development; a broker replaces it in cloud mode."""

    def __init__(self, queue_size: int = 32) -> None:
        self.sequence = 0
        self.queue_size = queue_size
        self._subscribers: set[asyncio.Queue[dict[str, object]]] = set()

    async def subscribe(self) -> AsyncIterator[asyncio.Queue[dict[str, object]]]:
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(self.queue_size)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    def snapshot_message(self, snapshot: DashboardSnapshot) -> dict[str, object]:
        return {
            "kind": "snapshot",
            "sequence": self.sequence,
            "state": snapshot.model_dump(),
        }

    async def publish(self, snapshot: DashboardSnapshot) -> None:
        self.sequence += 1
        message = self.snapshot_message(snapshot)
        for queue in tuple(self._subscribers):
            if queue.full():
                self._subscribers.discard(queue)
                continue
            queue.put_nowait(message)
