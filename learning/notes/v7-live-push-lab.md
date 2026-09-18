# V7 learning lab: live push and reconnect recovery

V6 moved shared matchup state behind a read model. V7 adds the live transport that pushes updates to clients without making them poll the API on a timer.

## Learning goals

- Explain why async tasks need cancellation design.
- Distinguish snapshot updates from delta updates.
- Understand how sequence numbers detect stale messages.
- Model reconnect behavior with replay windows and snapshot fallback.
- Understand why backpressure is a correctness problem, not only a performance problem.

## Deep dive: the gateway pattern

A live gateway usually has at least three parts:

```text
state source  →  stream producer  →  bounded queue  →  websocket task
```

The producer emits updates as state changes occur. The queue decouples the source from the socket writer so the producer does not block on network latency. The socket task drains the queue and writes to the client. When the client is slow, the queue becomes the pressure valve: either the producer pauses, discards stale work, or disconnects the client after a clear policy.

## Deep dive: snapshot versus delta

A snapshot is the full state of a resource, such as the entire matchup projection. A delta is the transform: “player X changed from 3 to 7.” Snapshots are easier to reason about and are ideal for first connection, reconnect, or recovery. Deltas are cheaper to send during steady-state updates when the client already has the current state.

The protocol is safest when it is explicit:

```text
{ "sequence": 12, "kind": "snapshot", "state": { ... } }
{ "sequence": 13, "kind": "delta", "change": { ... } }
```

The client must apply a delta only if it has already seen the prior sequence and the new sequence is exactly the next expected version.

## Deep dive: reconnect and stale sequence

Network issues are normal. The server should not assume the client received every message in order. After reconnect, the client sends its last successful sequence. The server can:

1. replay recent deltas if they still exist in a bounded replay window;
2. send a fresh snapshot if the client is too far behind; or
3. reject stale updates if the client replays an older sequence without a valid recovery path.

This is the difference between “works most of the time” and “stays correct under weird network conditions.”

## Exercises

Run a minimal async gateway experiment in Python:

```python
async def gateway():
    queue = asyncio.Queue(maxsize=10)
    sequence = 0

    async def producer():
        nonlocal sequence
        while True:
            await asyncio.sleep(0.2)
            sequence += 1
            await queue.put({"sequence": sequence, "kind": "delta", "state": {"score": sequence}})

    async def consumer():
        while True:
            msg = await queue.get()
            print("apply", msg)

    await asyncio.gather(producer(), consumer())
```

Then experiment:

1. Set the queue size to 1 and slow the consumer to trigger backpressure.
2. Deliver an older sequence after a newer one and confirm it is dropped.
3. Simulate a client reconnect with `last_seen = 5` and replay the next few deltas.
4. Simulate a long gap and force a snapshot instead of a delta replay.
5. Cancel the producer task and confirm the queue and consumer shutdown path is explicit.

## Checkpoint questions

- Why does cancellation need design in a push service?
- What is the difference between a stale delta and a valid out-of-order event?
- Why is a snapshot fallback necessary after reconnect?
- What is the cost of an unbounded queue during a slow-client outage?
- Why should the client treat the stream as sequence-aware rather than best-effort?

## Further reading

- [Python asyncio docs](https://docs.python.org/3/library/asyncio.html)
- [WebSockets in Python](https://websockets.readthedocs.io/)
- [MDN: WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455.html)
