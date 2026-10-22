from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np
from numpy.typing import NDArray

from .pipeline import Frame, inspect_video


@dataclass(frozen=True)
class ShotDecision:
    camera_cut: bool
    distance: float
    shot_id: int


@dataclass(frozen=True)
class ShotRecord:
    frame_index: int
    video_time_seconds: float
    shot_id: int
    camera_cut: bool
    cut_distance: float


@dataclass(frozen=True)
class ShotScanSummary:
    source: str
    source_fps: float
    sample_fps: float
    threshold: float
    histogram_bins: int
    decoded_frames: int
    sampled_frames: int
    camera_cuts: int
    cut_start_frames: tuple[int, ...]
    frame_records: str
    summary: str


class ShotGate:
    """A deterministic histogram gate for candidate broadcast camera cuts."""

    def __init__(self, threshold: float = 0.15, bins: int = 32):
        if not 0 < threshold <= 1:
            raise ValueError("threshold must be in (0, 1]")
        if bins < 2:
            raise ValueError("bins must be at least 2")
        self.threshold = threshold
        self.bins = bins
        self.previous: NDArray[np.float64] | None = None
        self.shot_id = 0

    def _signature(self, frame: Frame) -> NDArray[np.float64]:
        if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
            raise ValueError("Expected an HxWx3 uint8 BGR frame")
        histograms: list[NDArray[np.float64]] = []
        for channel in range(3):
            histogram, _ = np.histogram(
                frame[:, :, channel], bins=self.bins, range=(0, 256)
            )
            normalized = histogram.astype(np.float64)
            normalized /= max(float(normalized.sum()), 1.0)
            histograms.append(normalized)
        return np.concatenate(histograms)

    def update(self, frame: Frame) -> ShotDecision:
        current = self._signature(frame)
        distance = (
            0.0
            if self.previous is None
            else float(np.abs(current - self.previous).sum() / 6.0)
        )
        camera_cut = self.previous is not None and distance >= self.threshold
        if camera_cut:
            self.shot_id += 1
        self.previous = current
        return ShotDecision(bool(camera_cut), distance, self.shot_id)


def sampled_frame_indices(
    frame_count: int, source_fps: float, sample_fps: float
) -> Iterator[int]:
    """Yield an absolute, drift-free sampling schedule for constant-rate video."""
    if frame_count < 0:
        raise ValueError("frame_count must not be negative")
    if source_fps <= 0 or sample_fps <= 0:
        raise ValueError("source_fps and sample_fps must be positive")
    if sample_fps > source_fps:
        raise ValueError("sample_fps must not exceed the source frame rate")

    sample_index = 0
    previous_frame = -1
    while True:
        frame_index = round(sample_index * source_fps / sample_fps)
        if frame_index >= frame_count:
            return
        if frame_index != previous_frame:
            yield frame_index
            previous_frame = frame_index
        sample_index += 1


def scan_shots(
    source: str | Path,
    output_path: str | Path,
    *,
    threshold: float = 0.15,
    bins: int = 32,
    sample_fps: float | None = None,
) -> ShotScanSummary:
    metadata = inspect_video(source)
    effective_sample_fps = metadata.fps if sample_fps is None else sample_fps
    wanted_frames = iter(
        sampled_frame_indices(
            metadata.frame_count, metadata.fps, effective_sample_fps
        )
    )
    wanted = next(wanted_frames, None)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    summary_path = destination.with_suffix(".summary.json")

    capture = cv2.VideoCapture(metadata.path)
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {source}")
    gate = ShotGate(threshold=threshold, bins=bins)
    decoded = 0
    sampled = 0
    cut_start_frames: list[int] = []
    try:
        with destination.open("w", encoding="utf-8") as records:
            while wanted is not None:
                ok, frame = capture.read()
                if not ok:
                    break
                frame_index = decoded
                decoded += 1
                if frame_index < wanted:
                    continue
                decision = gate.update(frame)
                if decision.camera_cut:
                    cut_start_frames.append(frame_index)
                record = ShotRecord(
                    frame_index=frame_index,
                    video_time_seconds=frame_index / metadata.fps,
                    shot_id=decision.shot_id,
                    camera_cut=decision.camera_cut,
                    cut_distance=decision.distance,
                )
                records.write(json.dumps(asdict(record), separators=(",", ":")) + "\n")
                sampled += 1
                wanted = next(wanted_frames, None)
    finally:
        capture.release()

    summary = ShotScanSummary(
        source=metadata.path,
        source_fps=metadata.fps,
        sample_fps=effective_sample_fps,
        threshold=threshold,
        histogram_bins=bins,
        decoded_frames=decoded,
        sampled_frames=sampled,
        camera_cuts=len(cut_start_frames),
        cut_start_frames=tuple(cut_start_frames),
        frame_records=str(destination.resolve()),
        summary=str(summary_path.resolve()),
    )
    summary_path.write_text(json.dumps(asdict(summary), indent=2) + "\n")
    return summary


def load_shot_start_frames(path: str | Path) -> tuple[int, ...]:
    starts: list[int] = []
    for line_number, line in enumerate(Path(path).read_text().splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if "frame_index" not in payload or "camera_cut" not in payload:
            raise ValueError(f"Invalid shot record on line {line_number}")
        if payload["camera_cut"]:
            starts.append(int(payload["frame_index"]))
    return tuple(starts)
