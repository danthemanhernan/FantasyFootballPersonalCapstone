# V7 live push design

## Goal

Let the extension receive matchup changes without polling while preserving a
recoverable synchronization path after disconnects.

## Message contract

Every message carries a monotonically increasing `sequence` for one stream.

```json
{"kind":"snapshot","sequence":12,"state":{...}}
{"kind":"delta","sequence":13,"change":{...}}
```

The snapshot is authoritative for the state it contains. A client applies a
delta only when its sequence is exactly one less than the delta sequence. A
duplicate or older delta is ignored. A gap requests a new snapshot instead of
guessing at missing state.

## Reconnect behavior

The client reconnects with its last applied sequence. The server replays the
contiguous deltas when they are still in the bounded replay window. If the
client is older than that window, the server sends a fresh snapshot.

```text
connect(last_sequence)
  ├─ replay available → delta, delta, ...
  └─ replay unavailable → snapshot
```

The replay window is an optimization, not durable history. A snapshot must be
available from the read model so reconnect remains correct after overflow.

## Failure injection and deliberate deferrals

The protocol tests inject duplicate deltas, stale deltas, and replay-window
overflow. Slow-client backpressure, authentication, multi-instance fan-out,
and durable event streaming remain deferred to a later operational milestone.
