# V4 learning lab: deterministic event ingestion

V3 taught us how to obtain provider data without leaking ESPN into the app.
V4 asks the next question: how do we turn a sequence of raw plays into a
stable event stream that downstream scoring can safely consume?

## Learning goals

By the end, you should be able to:

1. Distinguish a raw play, a canonical event, and derived player state.
2. Explain why cursors and stable event IDs are different things.
3. Normalize timestamps and source metadata at an ingestion boundary.
4. Make replay deterministic by controlling receive time and input order.
5. Reject bad input before it reaches scoring or projections.

## The three representations

```text
raw provider page → canonical event → derived state
     DTO              durable fact       current score/stats
```

The raw play is shaped for the source. The canonical event is shaped for the
application and records what happened. Derived state is calculated later from
events. Keeping these separate allows replay: if scoring rules change, we can
recalculate state from the same event history.

## Deep dive 1: cursor versus event identity

A cursor answers: “Where was this play in this provider’s sequence?” The
fixture uses one-based contiguous cursors and rejects gaps. An event ID answers:
“Which play is this?” The canonical ID combines game ID and raw event ID:

```text
demo-001 + demo-001-001 = demo-001:demo-001-001
```

The cursor is useful for ordering and resuming. The event ID is useful for
traceability and, in V5, deduplication. They should not be conflated: a cursor
can change between pages or deliveries, while an event identity should remain
stable.

## Deep dive 2: deterministic replay

Replay is deterministic when the same fixture and receive time produce the same
canonical output. `occurred_at` comes from the play; `received_at` is supplied
by the caller. Tests pass a fixed receive time instead of using the wall clock.

This makes failures reproducible. A test failure can point to a specific input,
cursor, and transformation rather than depending on when the test happened to
run.

## Deep dive 3: validation as a trust boundary

TypeScript cannot validate JSON received at runtime. V4 therefore validates:

- fixture and game identifiers;
- event IDs and player IDs;
- recognized event types;
- timestamps that parse as dates;
- contiguous cursors;
- non-negative integer yardage;
- known player identities;
- duplicate raw event IDs.

The mapper only runs after these checks pass. This is fail-closed behavior:
unknown input is rejected rather than silently repaired or partially processed.

## Deep dive 4: event facts versus state

`RECEPTION` with 17 yards is a fact. “Kittle has 17 receiving yards and 1.7
fantasy points” is derived state. Storing the fact separately gives us an audit
trail and lets later versions handle replay, idempotency, ordering, and
rebuilding projections.

V4 does not yet make repeated delivery safe. If the same page arrives twice,
the events are normalized consistently, but V5 owns the rule that processing a
duplicate event must be a no-op.

## Lab exercises

Run the focused tests:

```bash
npm test -- --run src/ingestion.test.ts
```

Then perform these experiments:

1. Change a fixture cursor from `2` to `3`. Observe the cursor-gap failure.
2. Change `occurred_at` to `tomorrow`. Observe malformed-play rejection.
3. Change the event type to `INTERCEPTION`. Observe that unsupported facts do
   not reach normalization.
4. Change `player_id` to an unknown value. Observe the identity-boundary
   failure.
5. Run the deterministic replay test twice. Compare the complete output.
6. Duplicate a raw event ID. Observe duplicate-identifier rejection.

For each exercise, write down the invariant that was protected and whether the
failure should be fixed at the provider adapter, ingestion boundary, or domain
layer.

## Checkpoint questions

- Why should `received_at` not replace `occurred_at`?
- What problem does a cursor solve that an event ID does not?
- Why is rejecting an unknown player safer than creating a partial event?
- Which parts of a canonical event are useful for audit and replay?
- Why is deterministic normalization not the same as idempotent processing?

## What V4 does not claim

This is an offline replay boundary. It does not yet provide live polling,
durable event storage, duplicate-safe processing, out-of-order reconciliation,
provider pagination, or a production play-by-play contract. Those are separate
problems and are intentionally staged into later versions.

## Further reading

- [ADR-004: Versioned canonical events](../../docs/adrs/ADR-004-event-schema.md)
- [V4 live ingestion design](../../docs/v4-live-ingestion-design.md)
- [Domain modeling module](../modules/domain-modeling.md)
- [Martin Fowler: Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)
- [RFC 3339 timestamps](https://www.rfc-editor.org/rfc/rfc3339)
- [TypeScript narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)
