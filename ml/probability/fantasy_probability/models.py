"""Validated input and output contracts for matchup probability experiments."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)


class ContractModel(BaseModel):
    """Strict base model so malformed experiment inputs fail immediately."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class TeamProjection(ContractModel):
    team_id: str
    current_points: float
    remaining_mean: float
    remaining_stddev: float = Field(ge=0)

    @field_validator("team_id")
    @classmethod
    def validate_team_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("team_id must not be blank")
        return normalized

    @field_validator("current_points", "remaining_mean", "remaining_stddev")
    @classmethod
    def validate_finite_number(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("projection values must be finite")
        return value

    @property
    def expected_final_points(self) -> float:
        return self.current_points + self.remaining_mean


class MatchupForecastRequest(ContractModel):
    matchup_id: str
    as_of: datetime
    home: TeamProjection
    away: TeamProjection
    simulations: StrictInt = Field(default=10_000, ge=100, le=1_000_000)
    seed: StrictInt = Field(ge=0)
    model_version: str

    @field_validator("matchup_id", "model_version")
    @classmethod
    def validate_nonempty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("as_of")
    @classmethod
    def validate_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of must include an RFC 3339 timezone offset")
        return value

    @model_validator(mode="after")
    def validate_distinct_teams(self) -> MatchupForecastRequest:
        if self.home.team_id == self.away.team_id:
            raise ValueError("home and away team_id values must be different")
        return self


class AnalyticForecast(ContractModel):
    home_win_probability: float = Field(ge=0, le=1)
    away_win_probability: float = Field(ge=0, le=1)
    tie_probability: float = Field(ge=0, le=1)


class ProjectedWinner(ContractModel):
    winner: Literal["home", "away", "tie"]
    home_expected_final_points: float
    away_expected_final_points: float


class WinProbabilityForecast(ContractModel):
    matchup_id: str
    as_of: datetime
    home_win_probability: float = Field(ge=0, le=1)
    away_win_probability: float = Field(ge=0, le=1)
    tie_probability: float = Field(ge=0, le=1)
    home_wins: int = Field(ge=0)
    away_wins: int = Field(ge=0)
    ties: int = Field(ge=0)
    simulations: int = Field(ge=100)
    seed: int = Field(ge=0)
    distribution: Literal["independent_gaussian_v1"]
    model_version: str
    monte_carlo_standard_error: float = Field(ge=0)
    limitations: tuple[str, ...]
