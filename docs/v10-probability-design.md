# V10 win-probability and calibration design

## Purpose

V10 turns a point projection into an honest probability forecast. A point
projection answers "what is the expected final score?" A probability forecast
answers "across plausible ways the rest of this matchup can unfold, how often
does each team win or tie?"

The first implementation is deliberately a baseline. It proves reproducibility,
simulation semantics, and evaluation before introducing richer player-level
distributions, correlation, injuries, weather, or learned calibration.

## Product contract

For one matchup at one `as_of` timestamp, the engine accepts the current score
and a distribution for each team's remaining fantasy points. It returns mutually
exclusive home-win, away-win, and tie probabilities plus enough metadata to
reproduce the run.

```text
projection provider or fixture
  -> validated MatchupForecastRequest
  -> seeded distribution sampler
  -> N simulated final-score pairs
  -> win/tie counts and sampling uncertainty
  -> WinProbabilityForecast + experiment metadata

resolved historical or synthetic fixture outcomes
  -> calibration evaluator
  -> Brier score + reliability bins + ECE + baseline comparison
```

This engine does not fetch provider data. Projection sources implement a
separate adapter and translate into this contract. That keeps credentials,
provider DTOs, and network failures outside the probability calculation.

## Input contract

```text
TeamProjection
  team_id: non-empty string
  current_points: finite number
  remaining_mean: finite number
  remaining_stddev: finite number >= 0

MatchupForecastRequest
  matchup_id: non-empty string
  as_of: RFC 3339 timestamp
  home: TeamProjection
  away: TeamProjection
  simulations: integer from 100 through 1,000,000
  seed: non-negative integer
  model_version: non-empty string
```

`current_points` and `remaining_mean` may be negative because fantasy scoring
can include penalties. Negative standard deviation, non-finite values, duplicate
team IDs, invalid timestamps, and invalid simulation counts are rejected.

The default evidence run uses 10,000 simulations. At the worst-case probability
of 0.5, the approximate 95% Monte Carlo margin from sampling alone is at most
`1.96 / (2 * sqrt(10,000))`, or about 0.98 percentage points. The response must
report its actual simulation count; the UI must not imply more precision than
the run supports.

## Baseline distribution

V10 samples each team's remaining points independently from a Gaussian
distribution parameterized by `remaining_mean` and `remaining_stddev`. A zero
standard deviation is a point mass at the mean.

This is intentionally simple and analytically checkable: the difference between
two independent Gaussian samples is also Gaussian. Tests can therefore compare
the Monte Carlo result with an exact normal-difference probability.

Known limitation: independent Gaussian team totals do not model skew, shared game
environment, teammates, opposing players, injuries, or bounded player outcomes.
The engine must label the distribution family and independence assumption. It
must not describe the result as empirically calibrated for NFL games until a
time-ordered historical evaluation supports that claim.

## Reproducibility policy

- Every experiment requires a seed and records it in the output.
- Record code commit, runtime and dependency versions, model version, input
  fixture version, simulation count, and timestamp.
- Use a local random-generator instance; never depend on mutable global RNG
  state.
- Golden tests assert invariants and repeatability, not a long hard-coded random
  stream. NumPy explicitly does not guarantee identical bit streams across all
  future versions, so dependency versions belong in the evidence manifest.
- Production may generate a seed, but it must return and log the generated value.

## Output contract

```text
WinProbabilityForecast
  matchup_id: string
  as_of: RFC 3339 timestamp
  home_win_probability: number in [0, 1]
  away_win_probability: number in [0, 1]
  tie_probability: number in [0, 1]
  home_wins: integer
  away_wins: integer
  ties: integer
  simulations: integer
  seed: integer
  distribution: "independent_gaussian_v1"
  model_version: string
  monte_carlo_standard_error: number
  limitations: string[]
```

The three probabilities must sum to one within floating-point tolerance, and the
three counts must sum exactly to `simulations`. Ties remain explicit instead of
being silently assigned to either team.

## Baselines

The evidence report compares the Monte Carlo forecast with both:

1. **Projected-winner baseline:** choose the team with the higher expected final
   score. This demonstrates what uncertainty adds over a single point estimate.
2. **Constant 0.5 baseline:** predict an even chance for every resolved matchup.
   Its Brier score is 0.25 and gives probabilistic evaluation a useful reference.

For independent Gaussian fixtures, the analytic normal-difference probability is
also used as an implementation oracle. It is not a competing product model; it
checks that sampling and win counting are correct.

## Calibration evidence

A forecast is calibrated when events assigned probability `p` occur at roughly
frequency `p`. For example, among a sufficiently large group of forecasts near
0.70, the forecast team should win about 70% of the time.

V10 reports:

- **Brier score:** mean squared error `(probability - outcome)^2`; lower is better.
- **Reliability table:** count, mean forecast, observed win rate, and gap for each
  of ten equal-width probability bins.
- **Expected calibration error (ECE):** bin-count-weighted absolute reliability
  gap. Because ECE depends on binning, the report always includes the underlying
  table and bin definition.
- **Sampling evidence:** results at 100, 1,000, 10,000, and 100,000 simulations
  across repeated seeds to expose low-sample wobble.

Brier score reflects calibration and discrimination together, so it must not be
presented as a calibration-only measurement. V10 uses reliability bins alongside
it. Real football calibration remains unproven until forecasts are frozen before
outcomes and evaluated on time-ordered, unseen matchups.

## Failure experiments

1. **Too few samples:** compare repeated 100-simulation runs with 10,000- and
   100,000-simulation runs and show the larger run's reduced sampling variation.
2. **Impossible inputs:** reject negative standard deviation, NaN/infinity,
   duplicate teams, zero/negative simulation counts, and malformed timestamps.
3. **Biased projection:** shift one team's remaining mean upward in a resolved
   fixture set and show degraded Brier/reliability evidence.
4. **Deterministic tie:** with equal deterministic final scores, return tie
   probability 1 rather than dividing the tie silently.

## Acceptance gates

- Identical input, seed, code, and dependency versions produce identical output.
- Counts sum exactly to the requested simulation count; probabilities sum to one
  within `1e-12`.
- Deterministic fixtures produce exact 0 or 1 win/tie probabilities.
- At 10,000 simulations, baseline fixtures are within 0.02 absolute probability
  of the analytic independent-normal result.
- The evidence report includes seed, count, distribution, baselines, reliability
  bins, Brier score, ECE, failure experiments, and limitations.
- Credential-free fixtures and tests run in CI.
- Synthetic calibration evidence is labeled synthetic and makes no claim of live
  NFL predictive validity.

## Implementation boundary

The probability domain belongs under `ml/probability/` because it combines a
simulation engine with evaluation tooling and will later support calibration.
The first package exposes pure input/output models, a seeded Monte Carlo engine,
an analytic baseline, and calibration metrics. API and dashboard integration are
deferred until this domain evidence passes.

No ADR is required yet because V10 adds a leaf capability without changing the
accepted service boundaries. An ADR becomes appropriate if probability moves
into a separately deployed service or gains a durable forecast-log contract.

## Deliberate deferrals

- Player-level distributions and lineup uncertainty
- Correlation and covariance between players or teams
- Learned distributions and post-hoc calibration models
- Time-series backtesting on real provider projections
- Injury, weather, betting, or play-by-play feature ingestion
- API, WebSocket, dashboard, and HUD presentation
- Production claim that the probabilities are calibrated on NFL outcomes

## Learning checkpoint

A probability is useful when its meaning is testable: it is tied to a specific
event and timestamp, generated by a reproducible process, sharp enough to improve
on a baseline, and calibrated across comparable resolved events. “70%” is not a
synonym for confidence or certainty; it is a claim about long-run frequency.

## References

- [NumPy random Generator documentation](https://numpy.org/doc/stable/reference/random/generator.html), read 2026-10-12.
- [scikit-learn probability calibration documentation](https://scikit-learn.org/stable/modules/calibration.html), read 2026-10-12.
- Glenn W. Brier, [Verification of Forecasts Expressed in Terms of Probability](https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2), 1950; read 2026-10-12.
