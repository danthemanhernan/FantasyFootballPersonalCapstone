from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from vision_lab.shot_detection import (
    ShotGate,
    load_shot_start_frames,
    sampled_frame_indices,
    scan_shots,
)


def make_hard_cut_video(path: Path) -> Path:
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (64, 48)
    )
    assert writer.isOpened()
    try:
        for index in range(10):
            value = 0 if index < 5 else 255
            writer.write(np.full((48, 64, 3), value, dtype=np.uint8))
    finally:
        writer.release()
    return path


def test_shot_gate_detects_a_hard_cut() -> None:
    gate = ShotGate(threshold=0.5)
    black = np.zeros((16, 16, 3), dtype=np.uint8)
    white = np.full((16, 16, 3), 255, dtype=np.uint8)

    assert gate.update(black).shot_id == 0
    assert not gate.update(black).camera_cut
    decision = gate.update(white)
    assert decision.camera_cut
    assert decision.shot_id == 1


def test_sampling_schedule_does_not_accumulate_drift() -> None:
    frames = list(sampled_frame_indices(300, 30.0, 7.0))
    assert frames[:5] == [0, 4, 9, 13, 17]
    assert len(frames) == 70
    assert frames[-1] == 296


def test_sampling_rate_cannot_exceed_source_rate() -> None:
    with pytest.raises(ValueError):
        list(sampled_frame_indices(30, 30.0, 60.0))


def test_scan_writes_replayable_cut_records(tmp_path: Path) -> None:
    source = make_hard_cut_video(tmp_path / "hard-cut.mp4")
    output = tmp_path / "shots.jsonl"
    summary = scan_shots(source, output, threshold=0.5)
    records = [json.loads(line) for line in output.read_text().splitlines()]

    assert summary.sampled_frames == 10
    assert summary.cut_start_frames == (5,)
    assert records[5]["camera_cut"] is True
    assert records[5]["shot_id"] == 1
    assert load_shot_start_frames(output) == (5,)
    assert Path(summary.summary).exists()
