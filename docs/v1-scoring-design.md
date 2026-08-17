# V1 Scoring Design

## Goal

Separate fantasy scoring rules from the React UI and event simulator.

## Inputs

The scoring engine will receive:

- League scoring rules
- A player's football statistics

## Outputs

The scoring engine will return:

- A category-by-category scoring breakdown
- A total fantasy score

## Initial scoring categories

- Passing yards
- Rushing yards
- Receiving yards
- Receptions
- Passing touchdowns
- Rushing touchdowns
- Receiving touchdowns
- Interceptions

## Initial failure cases

- Missing statistics
- Negative yardage
- Duplicate events

Duplicate-event protection is intentionally deferred. The current simulator uses local scripted events rather than a real event stream, so V1 will document the risk and test it later at the event-processing boundary.

## Invariant

The total score must equal the sum of all scoring-breakdown categories.

## Deliberate deferrals

The first version will not support:

- Kickers
- Team defense
- Fumbles
- Two-point conversions
- Bonuses
- League persistence
- Idempotent processing of real event streams; see ADR-006.
