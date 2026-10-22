from __future__ import annotations

import json
import math
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
from numpy.typing import NDArray

Frame = NDArray[np.uint8]


@dataclass(frozen=True)
class VideoMetadata:
    path: str
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float


@dataclass(frozen=True)
class Detection:
    class_id: int
    class_name: str
    confidence: float
    box_xyxy: tuple[float, float, float, float]
    box_normalized: tuple[float, float, float, float]
    track_id: int | None = None


@dataclass(frozen=True)
class RunSummary:
    source: VideoMetadata
    model: str
    tracker: str
    device: str
    processed_frames: int
    detections: int
    unique_track_ids: int
    wall_seconds: float
    effective_fps: float
    mean_stage_ms: float
    p95_stage_ms: float
    annotated_video: str
    frame_records: str


class FrameDetector(Protocol):
    model_name: str
    tracker_name: str
    device_name: str

    def process(self, frame: Frame) -> tuple[Frame, Sequence[Detection]]: ...


def inspect_video(path: str | Path) -> VideoMetadata:
    source = Path(path)
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {source}")
    try:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        capture.release()
    if width <= 0 or height <= 0 or fps <= 0:
        raise ValueError(f"Video has invalid metadata: {source}")
    return VideoMetadata(
        path=str(source.resolve()),
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_count,
        duration_seconds=frame_count / fps,
    )


def normalize_box(
    box: Sequence[float], width: int, height: int
) -> tuple[float, float, float, float]:
    if len(box) != 4 or width <= 0 or height <= 0:
        raise ValueError("A box needs four coordinates and positive frame dimensions")
    x1, y1, x2, y2 = box
    return (
        min(max(float(x1) / width, 0.0), 1.0),
        min(max(float(y1) / height, 0.0), 1.0),
        min(max(float(x2) / width, 0.0), 1.0),
        min(max(float(y2) / height, 0.0), 1.0),
    )


def percentile(values: Sequence[float], quantile: float) -> float:
    if not values:
        return 0.0
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between zero and one")
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def run_video(
    source: str | Path,
    output_dir: str | Path,
    detector: FrameDetector,
    *,
    max_frames: int | None = None,
) -> RunSummary:
    metadata = inspect_video(source)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    video_path = destination / "annotated.mp4"
    records_path = destination / "frames.jsonl"
    summary_path = destination / "summary.json"

    capture = cv2.VideoCapture(metadata.path)
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        metadata.fps,
        (metadata.width, metadata.height),
    )
    if not capture.isOpened() or not writer.isOpened():
        capture.release()
        writer.release()
        raise RuntimeError("Could not initialize the video reader or writer")

    frame_index = 0
    detection_count = 0
    track_ids: set[int] = set()
    stage_times_ms: list[float] = []
    run_started = time.perf_counter()
    try:
        with records_path.open("w", encoding="utf-8") as records:
            while max_frames is None or frame_index < max_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                stage_started = time.perf_counter()
                annotated, detections = detector.process(frame)
                stage_times_ms.append((time.perf_counter() - stage_started) * 1000)
                writer.write(annotated)
                detection_count += len(detections)
                track_ids.update(
                    detection.track_id
                    for detection in detections
                    if detection.track_id is not None
                )
                record = {
                    "frame_index": frame_index,
                    "video_time_seconds": frame_index / metadata.fps,
                    "detections": [asdict(detection) for detection in detections],
                }
                records.write(json.dumps(record, separators=(",", ":")) + "\n")
                frame_index += 1
    finally:
        capture.release()
        writer.release()

    wall_seconds = time.perf_counter() - run_started
    summary = RunSummary(
        source=metadata,
        model=detector.model_name,
        tracker=detector.tracker_name,
        device=detector.device_name,
        processed_frames=frame_index,
        detections=detection_count,
        unique_track_ids=len(track_ids),
        wall_seconds=wall_seconds,
        effective_fps=frame_index / wall_seconds if wall_seconds else 0.0,
        mean_stage_ms=sum(stage_times_ms) / len(stage_times_ms) if stage_times_ms else 0.0,
        p95_stage_ms=percentile(stage_times_ms, 0.95),
        annotated_video=str(video_path.resolve()),
        frame_records=str(records_path.resolve()),
    )
    summary_path.write_text(json.dumps(asdict(summary), indent=2) + "\n", encoding="utf-8")
    return summary
