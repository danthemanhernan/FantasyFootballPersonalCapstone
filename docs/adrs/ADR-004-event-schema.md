# ADR-004: Versioned canonical events

- Status: Accepted
- Date: 2026-08-12

Canonical events carry event_id, event_type, timestamps, game_id, source metadata, schema version, and typed payload. Consumers assume at-least-once delivery and implement idempotency. Revisit when volume, ordering, or privacy requires a different log strategy.
