# Sprint 5 — Live push

## Outcome

The extension can receive matchup updates over a long-lived connection without polling. The gateway provides a recoverable stream that gives clients fresh state, handles reconnects, and rejects stale updates instead of silently corrupting the view.

## Starting point

Read `curriculum/versions/V7.md`, `docs/v7-live-push-design.md`, and
`learning/notes/v7-live-push-lab.md`.

## Concepts

- Async tasks and cancellation
- Queues and bounded backpressure
- Snapshot versus delta updates
- Sequence numbers and replay windows
- Reconnect and stale-sequence handling
- Liveness of the push channel versus correctness of state
- Client recovery patterns without polling loops

## Exercises

1. Write a tiny async gateway that owns a queue of state changes.
2. Produce a full state snapshot on first connect.
3. Emit deltas after the snapshot while tracking a monotonic sequence.
4. Inject a slow client and observe queue growth and backpressure behavior.
5. Inject stale or duplicate sequences and verify they are ignored.
6. Disconnect and reconnect with the last seen sequence.
7. Replay missing deltas when they are still in the retention window.
8. Fall back to a fresh snapshot when the client is outside replay coverage.
9. Compare the behavior of a bounded queue, an unbounded queue, and a reset policy.
10. Explain which state is authoritative when the client reconnects with stale context.

## Definition of done

- The gateway exposes a consistent snapshot-plus-delta protocol.
- Sequence numbers protect against stale or duplicate updates.
- Slow clients trigger bounded backpressure instead of unbounded memory growth.
- Reconnects recover state without dropping the client into an inconsistent view.
- The lab clearly describes what remains deferred: scaling, multi-instance fan-out, auth, and durable stream retention.

## Reflection

If a client reconnects after a long outage, should the server replay the last few deltas or send a full snapshot? Which choice is safer, and under what timing assumptions?
