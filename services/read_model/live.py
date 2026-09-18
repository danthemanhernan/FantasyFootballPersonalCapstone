from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class Snapshot(Generic[T]):
    sequence: int
    state: T


@dataclass(frozen=True)
class Delta(Generic[T]):
    sequence: int
    change: T


class ReplayWindow(Generic[T]):
    """Keep recent deltas while treating the snapshot as the source of truth."""

    def __init__(self, initial_state: T, max_size: int = 100) -> None:
        if max_size < 1:
            raise ValueError("max_size must be positive")
        self.state = initial_state
        self.sequence = 0
        self._deltas: deque[Delta[T]] = deque(maxlen=max_size)

    def publish(self, change: T, state: T) -> Delta[T]:
        self.sequence += 1
        self.state = state
        delta = Delta(self.sequence, change)
        self._deltas.append(delta)
        return delta

    def snapshot(self) -> Snapshot[T]:
        return Snapshot(self.sequence, self.state)

    def replay_after(self, sequence: int) -> list[Delta[T]] | None:
        if sequence < 0 or sequence > self.sequence:
            return None
        if sequence == self.sequence:
            return []
        if not self._deltas or sequence < self._deltas[0].sequence - 1:
            return None
        return [delta for delta in self._deltas if delta.sequence > sequence]


def apply_message(sequence: int, message: Snapshot[T] | Delta[T]) -> tuple[int, T | None, bool]:
    """Apply a message; return (sequence, state-if-snapshot, needs_resync)."""
    if isinstance(message, Snapshot):
        return message.sequence, message.state, False
    if message.sequence <= sequence:
        return sequence, None, False
    if message.sequence != sequence + 1:
        return sequence, None, True
    return message.sequence, None, False
