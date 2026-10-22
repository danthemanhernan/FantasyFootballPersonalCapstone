# Matchup probability baseline

This package implements the deterministic V10 Monte Carlo baseline described in
[`docs/v10-probability-design.md`](../../docs/v10-probability-design.md). It is a
pure domain package: provider access, persistence, API transport, and UI concerns
remain outside the simulation boundary.

## Run the evidence tests

```bash
cd ml/probability
uv sync --frozen --group test
uv run pytest -q
```

The committed fixture is synthetic. The tests verify seeded repeatability,
input rejection, exact deterministic outcomes, probability/count invariants,
the projected-winner baseline, and agreement with the analytic
normal-difference probability.

## Current assumptions

- Each team's remaining total is an independent Gaussian random variable.
- A standard deviation of zero is deterministic.
- Ties are a first-class outcome.
- The RNG seed, simulation count, distribution name, model version, sampling
  error, and limitations are returned with each forecast.

This baseline is not evidence that the probabilities are calibrated on NFL
outcomes. Calibration experiments are the next V10 increment.

