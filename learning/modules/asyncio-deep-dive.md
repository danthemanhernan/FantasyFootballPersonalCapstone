# Asyncio and asynchronous I/O: a durable mental model

This module is a practical guide to Python's `asyncio`, written for someone
who already understands some Go concurrency. It focuses on the concepts that
are easiest to confuse: coroutines, tasks, futures, event loops, cancellation,
blocking work, and concurrency versus parallelism.

## The one-sentence model

`asyncio` is cooperative concurrency: one event-loop thread runs one task at a
time, and a task voluntarily gives control back with `await` while it waits for
I/O, a timer, or another task.

The four words to remember are:

```text
coroutine → recipe
task      → scheduled job
future    → result placeholder
event loop → dispatcher
```

## What problem does asyncio solve?

Imagine a web service handling three requests. Each request spends most of its
life waiting for a database, Redis, another API, or a socket. A thread that
blocks during every wait wastes time and resources.

Asyncio lets the program do this:

```text
request A starts database query
request A waits ───────────────┐
                               │
request B handles cache I/O    │
request B waits ────────┐      │
                         │      │
request C handles HTTP  │      │
database result ready ──┘      │
resume request A ───────────────┘
```

This is concurrency, not necessarily parallelism. The work overlaps because
the program uses waiting time productively.

## `async def`: define a coroutine function

```python
async def load_matchup(matchup_id: str):
    response = await client.get(f"/matchups/{matchup_id}")
    return response.json()
```

`async def` tells Python that calling this function creates a coroutine object.
It does not immediately execute the body.

```python
work = load_matchup("matchup-demo")
```

At this point, `work` is a recipe. To execute it from another coroutine:

```python
result = await load_matchup("matchup-demo")
```

Use `async def` when the function needs to await asynchronous work or is part
of an async API contract. Do not mark a fast, pure calculation async merely to
make it look modern.

## `await`: pause this task, not the whole program

Use `await` when you have an awaitable operation and you want its result before
continuing:

```python
events = await repository.list_events("demo-001", limit=100)
```

While this task waits, the event loop may run other tasks.

`await` is not “run this in the background.” It means:

> Suspend the current task until this operation completes, while allowing the
> event loop to run other ready work.

This is the difference between these two functions:

```python
async def good():
    await asyncio.sleep(1)
    return "done"

async def bad():
    time.sleep(1)
    return "done"
```

`good()` pauses one task. `bad()` blocks the event-loop thread and delays every
other task using that loop.

## The event loop

The event loop is the scheduler and I/O coordinator. Application code usually
does not manipulate it directly.

```python
async def main():
    result = await do_work()
    print(result)

asyncio.run(main())
```

`asyncio.run()` is normally the outermost entry point for a script. It creates
an event loop, runs the top-level coroutine, shuts down async generators and
the default executor, and closes the loop.

Inside an already-running coroutine, use `await`, not another `asyncio.run()`.

## Task: schedule a coroutine

Calling a coroutine creates a recipe. `create_task()` schedules that recipe to
run concurrently with the current task:

```python
roster_task = asyncio.create_task(load_roster())
matchup_task = asyncio.create_task(load_matchup())

roster = await roster_task
matchup = await matchup_task
```

The two operations can overlap while they wait for I/O.

Use a task when:

- the work should begin before you are ready to await it;
- multiple independent operations should overlap;
- you need to cancel or inspect the operation separately.

Do not create a task for every function call automatically. If work is cheap or
dependent, simple `await` is clearer.

## `TaskGroup`: own related tasks

For new code, prefer structured concurrency with `TaskGroup`:

```python
async with asyncio.TaskGroup() as group:
    roster_task = group.create_task(load_roster())
    matchup_task = group.create_task(load_matchup())

roster = roster_task.result()
matchup = matchup_task.result()
```

The context manager does not exit until its tasks finish. If one task fails,
the group coordinates cancellation and propagates the failure. This gives tasks
a clear owner and lifetime.

## `gather()`

`gather()` is convenient when you want several results in positional order:

```python
roster, matchup, events = await asyncio.gather(
    load_roster(),
    load_matchup(),
    load_events(),
)
```

Use it for small, simple batches. Use `TaskGroup` when tasks have a meaningful
shared lifetime, need named handles, or the failure/cancellation relationship
deserves to be explicit.

## Futures: the envelope you wait for

A Future is an empty result envelope:

```text
Future created → result is empty
operation runs → event loop does other work
Future resolved → result or exception is available
```

This code:

```python
result = await future
```

means “wait until the envelope is filled.”

The vocabulary is easier if you remember the roles:

```text
coroutine = recipe for work
task      = scheduled coroutine
future    = eventual result slot
```

A `Task` is Future-like: it represents the eventual result of running a
coroutine. Application code normally creates tasks, not raw Futures. Futures
are mainly useful when adapting callback-style or low-level APIs to async/await.

## Sequential and concurrent work

Sequential:

```python
a = await fetch_a()
b = await fetch_b()
c = await fetch_c()
```

Approximate duration: `time(a) + time(b) + time(c)`.

Concurrent:

```python
a, b, c = await asyncio.gather(fetch_a(), fetch_b(), fetch_c())
```

Approximate duration: `max(time(a), time(b), time(c))`, plus overhead.

Concurrency helps only when the operations are independent and spend time
waiting. If `b` needs the result of `a`, keep them sequential.

## Cancellation

Cancellation is a request for a task to stop. It is delivered by raising
`asyncio.CancelledError` at an await point.

```python
async def worker():
    try:
        while True:
            await consume_event()
    except asyncio.CancelledError:
        await close_resources()
        raise
```

Use `finally` for cleanup and usually re-raise `CancelledError` after cleanup.
Swallowing cancellation can break timeouts and task groups.

Cancellation is cooperative. A task stuck in `time.sleep()` or a CPU loop may
not respond promptly because it is not reaching an await point.

## Timeouts

Every external operation should have a bound:

```python
async with asyncio.timeout(2):
    result = await repository.get_matchup(matchup_id)
```

At the boundary, a timeout should become a stable application error such as
`503 Service Unavailable`, rather than leaving a request hanging forever.

Older code commonly uses:

```python
result = await asyncio.wait_for(operation(), timeout=2)
```

Both mechanisms impose a deadline; the context-manager form is easier to
compose across multiple awaits.

## Blocking work and `to_thread`

Asyncio does not magically make synchronous code non-blocking.

Bad:

```python
async def handler():
    response = requests.get(url)
    return response.json()
```

Better: use an async-native client. If that is impossible:

```python
response = await asyncio.to_thread(requests.get, url)
```

`to_thread()` moves the blocking call to a worker thread. It is useful for
blocking I/O, not a universal solution for CPU-heavy Python code.

## CPU-bound work

This blocks the event loop:

```python
async def bad_probability_calculation():
    for _ in range(100_000_000):
        expensive_calculation()
```

Use a process pool, a job worker, native code that releases the GIL, or a
different service for substantial CPU-bound work.

## Queues and backpressure

`asyncio.Queue` is the closest common Python equivalent to a Go channel:

```python
queue = asyncio.Queue(maxsize=100)

await queue.put(event)
event = await queue.get()
try:
    await process(event)
finally:
    queue.task_done()
```

A bounded queue is important. It makes producers slow down when consumers
cannot keep up instead of allowing unlimited memory growth.

## Semaphores: bounded concurrency

Use a semaphore when many operations are possible but only a limited number
should run at once:

```python
limit = asyncio.Semaphore(20)

async def fetch_player(player_id):
    async with limit:
        return await client.get(f"/players/{player_id}")
```

This protects the upstream API, connection pool, memory, and local scheduler.

## Events and locks

An `asyncio.Event` is a one-way signal:

```python
ready = asyncio.Event()

# producer
ready.set()

# consumer
await ready.wait()
```

An `asyncio.Lock` protects a small critical section among tasks on the same
event loop:

```python
async with lock:
    projection.update(event)
```

Neither replaces a database transaction. Asyncio synchronization primitives
also do not generally coordinate arbitrary OS threads.

## Common pitfalls

### Forgetting `await`

```python
response = client.get(url)  # coroutine, not response
```

### Fire-and-forget without ownership

```python
asyncio.create_task(send_notification())
```

The task may fail without anyone observing the exception. Keep a reference and
await it, or put it in a `TaskGroup`.

### Unbounded task creation

Creating 100,000 tasks can exhaust memory and sockets. Use a queue, workers, or
a semaphore.

### Swallowing cancellation

```python
except asyncio.CancelledError:
    pass
```

Clean up, then normally `raise`.

### Nested event loops

Do not call `asyncio.run()` inside an async function. The event loop is already
running.

### Async code that never awaits

An `async def` function with a long CPU loop is still blocking. Syntax does not
create concurrency; yielding does.

## Asyncio versus Go

The closest translation is:

| Go | Python asyncio |
|---|---|
| goroutine | `asyncio.Task` |
| `go work()` | `asyncio.create_task(work())` |
| channel | `asyncio.Queue` |
| `select` | task/queue/event coordination |
| `context.Context` | cancellation and timeout scopes |
| `sync.WaitGroup` | `TaskGroup` |

Go feels more straightforward because `go` immediately schedules a goroutine
and channels provide a strong default communication model. Python requires
more explicit decisions about whether a coroutine is merely created, scheduled,
awaited, cancelled, or owned by a group.

The tradeoff is flexibility: Python can use async-native libraries, threads,
processes, queues, and structured task groups in one ecosystem, but the rules
must be followed carefully.

## When not to use asyncio

Prefer synchronous code when the program is mostly computation, makes little
concurrent I/O, or uses synchronous libraries throughout.

Prefer threads when you must call blocking I/O libraries. Prefer processes or a
worker service for CPU-heavy work. Asyncio is not automatically faster; it is a
good fit when many operations spend time waiting.

## Optimization checklist

1. Remove blocking calls from the event-loop thread.
2. Add timeouts to external operations.
3. Use connection pools.
4. Bound concurrency with semaphores or worker counts.
5. Use cache-aside reads where appropriate.
6. Batch independent I/O with `TaskGroup` or `gather()`.
7. Use bounded queues for producer/consumer pipelines.
8. Measure before changing event-loop implementations.

## V6 connection

Your V6 service has this shape:

```text
FastAPI request
      ↓
await Redis or Postgres I/O
      ↓
event loop handles other requests
      ↓
return read-model response
```

The route and repository methods are async because they wait on external
systems. The projection and scoring calculations can remain ordinary `def`
functions because they are local and fast.

## Further reading

- [Python asyncio overview](https://docs.python.org/3/library/asyncio.html)
- [Coroutines, tasks, and futures](https://docs.python.org/3/library/asyncio-task.html)
- [Task groups](https://docs.python.org/3/library/asyncio-task.html#task-groups)
- [Event loop documentation](https://docs.python.org/3/library/asyncio-eventloop.html)
- [Go concurrency tour](https://go.dev/tour/concurrency/1)
- [Go context package](https://go.dev/blog/context)
