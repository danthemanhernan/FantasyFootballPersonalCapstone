# ADR-006: Defer event idempotency until real event streams

- Status: Proposed
- Date: 2026-08-16

## Context

The V1 scoring engine receives player statistics and calculates fantasy points. It does not receive event identities or maintain processing history.

The current simulator uses local scripted events, so duplicate delivery is not an active production concern. Real play-by-play feeds and message-based delivery may deliver the same event more than once because retries and reconnects commonly provide at-least-once delivery.

Counting a duplicate touchdown twice would produce an incorrect fantasy score.

## Decision

Do not add duplicate-event tracking to the V1 scoring function or the current local simulator. Document duplicate delivery as a known limitation and address it at the event-processing boundary when real event streams are introduced.

The future event-processing layer should use a stable provider event ID, record processed IDs, and make repeated delivery of the same event a no-op.

## Alternatives considered

- Track event IDs inside `scorePlayer`: rejected because scoring receives accumulated statistics, not events, and should remain a pure calculation.
- Track event IDs inside the current simulator: deferred because the local scripted simulator does not model real delivery, retries, or reconnects yet.
- Deduplicate in the future event-processing layer: selected because that layer owns event identity, ordering, retries, and state transitions.

## Consequences

V1 remains small and focused on configurable scoring. The current simulator can still double-count an event if the same event is manually applied twice, and that limitation is intentional.

When real event ingestion begins, the system must add idempotency before trusting fantasy totals. This will require a stable event identity and durable or appropriately scoped processed-event state.

## Revisit when

Revisit when the project introduces a live provider, replay service, message broker, reconnect handling, or any other at-least-once event-delivery path.
