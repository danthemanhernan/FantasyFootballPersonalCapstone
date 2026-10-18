from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from fantasy_probability import (
    MatchupForecastRequest,
    TeamProjection,
    analytic_normal_forecast,
    projected_winner_baseline,
    simulate_matchup,
)

FIXTURE = Path(__file__).parent / "fixtures" / "baseline_matchup.json"


def load_request() -> MatchupForecastRequest:
    return MatchupForecastRequest.model_validate_json(FIXTURE.read_text())


def test_same_seed_produces_identical_forecast() -> None:
    request = load_request()

    assert simulate_matchup(request) == simulate_matchup(request)


def test_forecast_preserves_probability_and_count_invariants() -> None:
    request = load_request()
    forecast = simulate_matchup(request)

    assert forecast.home_wins + forecast.away_wins + forecast.ties == request.simulations
    assert (
        forecast.home_win_probability
        + forecast.away_win_probability
        + forecast.tie_probability
        == pytest.approx(1, abs=1e-12)
    )
    assert forecast.seed == request.seed
    assert forecast.simulations == request.simulations
    assert forecast.distribution == "independent_gaussian_v1"
    assert forecast.model_version == request.model_version
    assert len(forecast.limitations) >= 3


def test_monte_carlo_matches_analytic_normal_probability() -> None:
    request = load_request()
    simulated = simulate_matchup(request)
    analytic = analytic_normal_forecast(request)

    assert simulated.home_win_probability == pytest.approx(
        analytic.home_win_probability, abs=0.02
    )
    assert simulated.away_win_probability == pytest.approx(
        analytic.away_win_probability, abs=0.02
    )


def test_projected_winner_baseline_declares_expected_score_leader() -> None:
    baseline = projected_winner_baseline(load_request())

    assert baseline.winner == "home"
    assert baseline.home_expected_final_points == 110.5
    assert baseline.away_expected_final_points == 104.0


def test_deterministic_tie_remains_explicit() -> None:
    request = load_request().model_copy(
        update={
            "home": TeamProjection(
                team_id="home", current_points=50, remaining_mean=10, remaining_stddev=0
            ),
            "away": TeamProjection(
                team_id="away", current_points=40, remaining_mean=20, remaining_stddev=0
            ),
        }
    )

    forecast = simulate_matchup(request)
    analytic = analytic_normal_forecast(request)

    assert (forecast.home_wins, forecast.away_wins, forecast.ties) == (0, 0, 10_000)
    assert forecast.tie_probability == 1
    assert analytic.tie_probability == 1


def test_deterministic_winner_is_exact() -> None:
    request = load_request().model_copy(
        update={
            "home": TeamProjection(
                team_id="home", current_points=50, remaining_mean=11, remaining_stddev=0
            ),
            "away": TeamProjection(
                team_id="away", current_points=40, remaining_mean=20, remaining_stddev=0
            ),
        }
    )

    forecast = simulate_matchup(request)

    assert forecast.home_win_probability == 1
    assert forecast.monte_carlo_standard_error == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("remaining_stddev", -0.1),
        ("remaining_stddev", float("nan")),
        ("remaining_mean", float("inf")),
        ("current_points", float("-inf")),
    ],
)
def test_invalid_projection_values_are_rejected(field: str, value: float) -> None:
    projection = {
        "team_id": "team",
        "current_points": 1,
        "remaining_mean": 2,
        "remaining_stddev": 3,
    }
    projection[field] = value

    with pytest.raises(ValidationError):
        TeamProjection.model_validate(projection)


@pytest.mark.parametrize(
    "updates",
    [
        {"simulations": 99},
        {"simulations": 1_000_001},
        {"simulations": 10_000.5},
        {"seed": -1},
        {"seed": True},
        {"as_of": "not-a-timestamp"},
        {"as_of": datetime(2026, 9, 13, 18, 30)},
    ],
)
def test_invalid_request_values_are_rejected(updates: dict[str, object]) -> None:
    payload = json.loads(FIXTURE.read_text())
    payload.update(updates)

    with pytest.raises(ValidationError):
        MatchupForecastRequest.model_validate(payload)


def test_duplicate_team_ids_are_rejected() -> None:
    payload = json.loads(FIXTURE.read_text())
    payload["away"]["team_id"] = payload["home"]["team_id"]

    with pytest.raises(ValidationError):
        MatchupForecastRequest.model_validate(payload)


def test_timezone_aware_datetime_is_accepted() -> None:
    request = load_request().model_copy(update={"as_of": datetime.now(timezone.utc)})

    assert request.as_of.utcoffset() is not None
