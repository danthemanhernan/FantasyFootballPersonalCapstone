# V5 learning lab: idempotent event processing

V4 made canonical events deterministic. V5 handles the next distributed-
systems reality: delivery is often at least once, so the same event can arrive
again.

## Learning goals

- Distinguish at-most-once, at-least-once, and effectively-once outcomes.
- Explain why deduplication belongs before projection mutation.
- Separate poison events from transient failures.
- Understand ordering policy, audit trails, and dead-letter queues.
- Rebuild confidence by processing the same events twice.

## Deep dive: delivery versus effect

An event can be delivered twice even when the producer created it once. A retry,
reconnect, or timeout can make the consumer unsure whether the first attempt
finished. V5 uses a stable `event_id` as the inbox key.

```text
event arrives
  ↓
have we processed event_id?
  ├── yes → audit DUPLICATE, stop
  └── no  → apply projection, record processed ID
```

The critical rule is that duplicate detection must happen before adding yards,
receptions, or touchdowns to projection state.

## Deep dive: transient versus poison

Transient failure: the event is valid, but infrastructure temporarily fails.
Retrying may succeed.

Poison event: the event itself cannot be safely processed, such as an unknown
player identity. Retrying the same bad input will not fix it, so it belongs in a
dead-letter queue for inspection or later reconciliation.

## Deep dive: audit records

The projection answers “what is true now?” The audit trail answers “what did we
do with each event?” V5 records processed, duplicate, and dead-letter outcomes,
including attempts and reasons. This makes an apparently unchanged projection
explainable.

## Exercises

Run:

```bash
npm test -- --run src/processing.test.ts
```

Then experiment:

1. Process `events` twice with the same store. Confirm points do not increase.
2. Reverse the input array. Confirm the audit cursors are still `1, 2`.
3. Change the player ID to an unknown value. Confirm no projection is created.
4. Inject two transient failures and confirm attempt three succeeds.
5. Inject three failures with `maxAttempts: 3`. Confirm a dead letter.
6. Delete the processed-ID check and observe duplicate scoring. Restore it.

## Checkpoint questions

- What exactly does the inbox guarantee?
- Why is an unknown player poison rather than transient?
- Why is an in-memory processed-ID set insufficient for a production restart?
- What should happen if two events share a cursor?
- Why are audit records useful even when the projection is correct?

## Further reading

- [Distributed systems module](../modules/distributed-systems.md)
- [ADR-006: Event idempotency](../../docs/adrs/ADR-006-event-idempotency.md)
- [Martin Fowler: Idempotent Receiver](https://martinfowler.com/articles/patterns-of-distributed-systems/idempotent-receiver.html)
- [Martin Fowler: Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)
- [AWS Builders’ Library: Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
