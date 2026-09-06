# V4 live ingestion design

## Boundary

The replay boundary accepts a fixture-shaped page of raw plays and emits
versioned `CanonicalFootballEvent` values. The extension and scoring code only
consume the canonical shape; cursor and raw event identifiers remain under
`source` for traceability.

```text
raw page -> validate cursor/timestamps -> normalize -> canonical event stream
```

## Replay contract

Each page has a game ID and one-based contiguous cursors. Replaying a page with
the same fixed receive time returns equivalent data. A cursor gap is rejected
because silently skipping a play would make the read model irreproducible.
Unknown player IDs are rejected until the identity mapping boundary exists.

This is intentionally not idempotent processing: repeated delivery is detected
and made safe in V5. Polling, persistence, retries, and live provider access are
also deferred.

## Failure injection and evidence

The fixture test covers repeated-page determinism, malformed values, cursor
gaps, duplicate identifiers, and unknown players. `npm test` is the
reproducible evidence for this lab.
