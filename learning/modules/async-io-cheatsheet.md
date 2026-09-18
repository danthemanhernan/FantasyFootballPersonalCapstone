# Async I/O cheat sheet

## The mental model

```text
coroutine = recipe
task      = scheduled job
future    = result placeholder
event loop = dispatcher
```

## When to use what

| Tool | Use it when |
|---|---|
| `async def` | The function awaits async work or is part of an async API |
| `await` | You need the result of an awaitable and want to yield while waiting |
| `create_task()` | Start independent work before awaiting it |
| `TaskGroup` | Own and coordinate related tasks; preferred for new grouped work |
| `gather()` | Collect a small batch of independent results |
| `asyncio.timeout()` | Bound external work with a deadline |
| `asyncio.Queue` | Build producer/consumer pipelines and backpressure |
| `asyncio.Semaphore` | Limit concurrent requests or resource use |
| `asyncio.Event` | Signal that a condition is ready |
| `asyncio.Lock` | Protect shared async state in one event loop |
| `asyncio.to_thread()` | Run blocking I/O without freezing the event loop |
| process pool | Run CPU-heavy work away from the event loop |
| `asyncio.run()` | Start the top-level async program once |

## Core syntax

```python
async def work():
    return await async_operation()

asyncio.run(work())
```

```python
async with asyncio.TaskGroup() as group:
    task = group.create_task(work())
result = task.result()
```

```python
async with asyncio.timeout(2):
    result = await external_call()
```

```python
async with semaphore:
    await limited_call()
```

## Rules to remember

1. `async def` creates a coroutine function; calling it creates a recipe.
2. `await` executes/waits for an awaitable and yields the current task.
3. `create_task()` schedules work concurrently; it does not mean “ignore it.”
4. Always own tasks and observe their exceptions.
5. Never use `time.sleep()` or blocking client libraries in the event loop.
6. Put timeouts around network, database, cache, and queue operations.
7. Bound task counts, queue sizes, and upstream concurrency.
8. Clean up on `CancelledError`, then usually re-raise it.
9. Asyncio gives concurrency, not automatic CPU parallelism.
10. Keep pure local calculations synchronous unless they truly await I/O.

## Quick translations from Go

```text
goroutine        → asyncio Task
go f()           → asyncio.create_task(f())
channel          → asyncio.Queue
WaitGroup        → TaskGroup
context cancel   → task cancellation / timeout scope
```

## Debugging questions

```text
Did I forget await?
Is this call blocking the event-loop thread?
Who owns this task?
What happens if it is cancelled?
What is the timeout?
Can concurrency be bounded?
Is this I/O-bound or CPU-bound?
```
