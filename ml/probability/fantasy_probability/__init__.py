"""Public API for the V10 matchup probability baseline."""

from .models import (
    AnalyticForecast,
    MatchupForecastRequest,
    ProjectedWinner,
    TeamProjection,
    WinProbabilityForecast,
)
from .simulation import (
    analytic_normal_forecast,
    projected_winner_baseline,
    simulate_matchup,
)

__all__ = [
    "AnalyticForecast",
    "MatchupForecastRequest",
    "ProjectedWinner",
    "TeamProjection",
    "WinProbabilityForecast",
    "analytic_normal_forecast",
    "projected_winner_baseline",
    "simulate_matchup",
]

