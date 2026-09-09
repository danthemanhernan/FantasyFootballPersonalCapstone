# Sprint 3 — Reliable event processing

## Outcome

Canonical football events can be delivered more than once without double-
counting fantasy points. Processing preserves an audit trail, reorders events
by cursor, retries bounded transient failures, and dead-letters poison inputs.

## Starting point

Read `curriculum/versions/V5.md`, `docs/v5-reliable-processing-design.md`, and
`learning/notes/v5-reliable-processing-lab.md`.

## Concepts

- At-least-once delivery
- Idempotency keys and inboxes
- Projection state versus event history
- Ordering and sequence policy
- Transient failure versus poison message
- Dead-letter queues and audit trails
- Process-once claims versus durable exactly-once claims

## Exercises

1. Run the V4 replay to produce canonical events.
2. Process the events twice using one processing store.
3. Reverse delivery order and inspect cursor-ordered audit records.
4. Inject an unknown player and inspect the dead letter.
5. Inject transient failures and observe bounded recovery.
6. Rebuild the projection from a clean store and compare the result.

## Definition of done

- Duplicate events produce one projection effect.
- Duplicate deliveries remain visible in audit records.
- Out-of-order delivery follows the documented sequence policy.
- Poison events do not corrupt projection state.
- Transient failures have bounded retries.
- The lab explains why in-memory dedupe is not durable production idempotency.

## Reflection

What would happen after a process restart if processed IDs existed only in
memory? What durable constraint would a database-backed inbox need?
