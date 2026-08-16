# Sprint 1 — Configurable scoring

## Outcome

Fantasy scoring is represented by a small, deterministic domain module instead of being embedded in the React UI or simulator. A player can receive an explainable scoring breakdown for a configurable league.

## Concepts

- Domain logic versus presentation logic
- League settings as configuration
- Statistics versus fantasy points
- Value objects and data contracts
- Pure scoring functions
- Invariants and deterministic tests
- Table-driven tests

## Starting point

Read:

- `curriculum/versions/V1.md`
- `learning/modules/domain-modeling.md`
- `apps/extension/src/simulator.ts`
- `apps/extension/src/types.ts`

## Exercises

1. Write `docs/v1-scoring-design.md` before writing the scoring implementation.
2. Define `ScoringRules` and `PlayerStats` types in `apps/extension/src/scoring.ts`.
3. Add a standard scoring configuration and a credential-free sample stat line.
4. Manually calculate the expected score for the sample stat line.
5. Implement a pure scoring function that returns a category-by-category breakdown and total.
6. Add deterministic tests for yardage, receptions, touchdowns, and interceptions.
7. Add table-driven tests for standard and PPR scoring.
8. Test failure cases: missing statistics, negative yardage, and duplicate events.
9. Connect the scoring module to the simulator without moving scoring rules into `Hud.tsx`.
10. Explain the invariant: the total must equal the sum of the breakdown categories.

## Suggested domain shape

```text
ScoringRules + PlayerStats → ScoringBreakdown
```

The UI should consume the result but should not calculate it.

## Failure injection

- Remove a statistic from a fixture.
- Pass negative yardage.
- Process one event twice.
- Change reception scoring from standard to PPR.

Record what breaks and whether the failure should be rejected, normalized, or made idempotent.

## Definition of done

- Scoring rules are configurable.
- Scoring logic is independent of React.
- Tests are deterministic and credential-free.
- Breakdown categories reconcile exactly to the total.
- The simulator still runs and the HUD still renders.
- Incomplete scoring categories are documented rather than implied to be supported.

## Reflection

Which rules belong in the scoring domain invariant? Which inputs should be rejected, and which should be normalized to zero?

## Deepen your understanding

Read `learning/modules/domain-modeling.md`, explain one concept in your own words, connect it to this lab, and add a dated source to `learning/REFERENCES.md`.
