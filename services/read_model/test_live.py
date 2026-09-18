import pytest

from live import Delta, ReplayWindow, Snapshot, apply_message


def test_replays_contiguous_deltas_after_reconnect():
    stream = ReplayWindow({"points": 0}, max_size=3)
    stream.publish({"points": 1}, {"points": 1})
    stream.publish({"points": 2}, {"points": 2})

    assert stream.replay_after(1) == [Delta(2, {"points": 2})]


def test_overflow_requires_a_fresh_snapshot():
    stream = ReplayWindow({"points": 0}, max_size=2)
    for points in range(1, 4):
        stream.publish({"points": points}, {"points": points})

    assert stream.replay_after(0) is None
    assert stream.snapshot() == Snapshot(3, {"points": 3})


def test_duplicate_and_stale_deltas_are_ignored():
    sequence, state, resync = apply_message(4, Delta(4, {"points": 4}))

    assert (sequence, state, resync) == (4, None, False)


def test_sequence_gap_requests_snapshot():
    assert apply_message(4, Delta(6, {"points": 6})) == (4, None, True)


def test_snapshot_resets_client_sequence():
    assert apply_message(4, Snapshot(9, {"points": 9})) == (9, {"points": 9}, False)


def test_rejects_empty_replay_window():
    with pytest.raises(ValueError):
        ReplayWindow({}, max_size=0)
