# V5 reliable processing design

## Goal

Make repeated delivery boring: the same canonical event may arrive more than
once, but it must affect the projection only once and remain visible in the
audit trail.

## Boundary

```text
canonical events → ordering policy → inbox/dedupe → handler → projection
                                      │                  │
                                      ├── audit log      └── dead letters
                                      └── processed IDs
```

The V5 implementation uses `InMemoryProcessingStore` as a teaching substitute
for durable storage. The store owns processed IDs, projection state, audit
records, and dead letters. The scoring function remains a pure calculation;
idempotency belongs around event application.

## Processing policy

- Events are ordered by game and source cursor before handling.
- A known event ID is recorded in the inbox before a later delivery can apply it.
- Duplicate delivery records `DUPLICATE` audit status and does not mutate state.
- Unknown players are poison events and go to the dead-letter queue.
- Transient failures retry up to a bounded attempt count.
- Events that exhaust retries go to the dead-letter queue.

This is process-once behavior within the lifetime of the in-memory store. A
durable database-backed inbox is required before making a production claim.

## Evidence

The test suite proves one projection after two deliveries, out-of-order input
is normalized into cursor order, poison events do not corrupt state, transient
failures can recover, and exhausted retries become dead letters.
