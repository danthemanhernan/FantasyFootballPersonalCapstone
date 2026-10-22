"""Seeded Monte Carlo and analytic baselines for one fantasy matchup."""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

from .models import (
    AnalyticForecast,
    MatchupForecastRequest,
    ProjectedWinner,
    TeamProjection,
    WinProbabilityForecast,
)

DISTRIBUTION = "independent_gaussian_v1"
LIMITATIONS = (
    "Remaining team totals are modeled as independent Gaussian variables.",
    "The baseline does not model player correlation, injuries, weather, or lineup changes.",
    "The forecast is not calibrated on live NFL outcomes.",
)


def _remaining_samples(
    rng: np.random.Generator, projection: TeamProjection, simulations: int
) -> np.ndarray:
    if projection.remaining_stddev == 0:
        return np.full(simulations, projection.remaining_mean, dtype=np.float64)
    return rng.normal(
        loc=projection.remaining_mean,
        scale=projection.remaining_stddev,
        size=simulations,
    )


def simulate_matchup(request: MatchupForecastRequest) -> WinProbabilityForecast:
    """Simulate final scores with a request-local RNG and explicit tie handling."""

    rng = np.random.default_rng(request.seed)
    home_final = request.home.current_points + _remaining_samples(
        rng, request.home, request.simulations
    )
    away_final = request.away.current_points + _remaining_samples(
        rng, request.away, request.simulations
    )

    home_wins = int(np.count_nonzero(home_final > away_final))
    away_wins = int(np.count_nonzero(away_final > home_final))
    ties = request.simulations - home_wins - away_wins
    home_probability = home_wins / request.simulations

    return WinProbabilityForecast(
        matchup_id=request.matchup_id,
        as_of=request.as_of,
        home_win_probability=home_probability,
        away_win_probability=away_wins / request.simulations,
        tie_probability=ties / request.simulations,
        home_wins=home_wins,
        away_wins=away_wins,
        ties=ties,
        simulations=request.simulations,
        seed=request.seed,
        distribution=DISTRIBUTION,
        model_version=request.model_version,
        monte_carlo_standard_error=math.sqrt(
            home_probability * (1 - home_probability) / request.simulations
        ),
        limitations=LIMITATIONS,
    )


def analytic_normal_forecast(request: MatchupForecastRequest) -> AnalyticForecast:
    """Return the exact result implied by the independent Gaussian assumptions."""

    mean_difference = (
        request.home.expected_final_points - request.away.expected_final_points
    )
    difference_stddev = math.hypot(
        request.home.remaining_stddev, request.away.remaining_stddev
    )

    if difference_stddev == 0:
        if mean_difference > 0:
            return AnalyticForecast(
                home_win_probability=1, away_win_probability=0, tie_probability=0
            )
        if mean_difference < 0:
            return AnalyticForecast(
                home_win_probability=0, away_win_probability=1, tie_probability=0
            )
        return AnalyticForecast(
            home_win_probability=0, away_win_probability=0, tie_probability=1
        )

    home_probability = NormalDist().cdf(mean_difference / difference_stddev)
    return AnalyticForecast(
        home_win_probability=home_probability,
        away_win_probability=1 - home_probability,
        tie_probability=0,
    )


def projected_winner_baseline(request: MatchupForecastRequest) -> ProjectedWinner:
    """Declare a winner from expected final points without modeling uncertainty."""

    home_expected = request.home.expected_final_points
    away_expected = request.away.expected_final_points
    winner = "home" if home_expected > away_expected else "away"
    if home_expected == away_expected:
        winner = "tie"
    return ProjectedWinner(
        winner=winner,
        home_expected_final_points=home_expected,
        away_expected_final_points=away_expected,
    )

