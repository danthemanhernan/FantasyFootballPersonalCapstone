from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from .afmot_evaluator import (
    GroundTruth,
    Prediction,
    load_afmot_ground_truth,
    load_predictions,
    match_frame,
)
from .pipeline import inspect_video

Frame = NDArray[np.uint8]


@dataclass(frozen=True)
class DiagnosticSummary:
    output: str
    frames: int
    ground_truth_boxes: int
    predicted_boxes: int
    matches: int
    missed_ground_truth: int
    unmatched_predictions: int
    iou_threshold: float


def _draw_box(
    frame: Frame,
    box: tuple[float, float, float, float],
    color: tuple[int, int, int],
    label: str,
) -> None:
    x1, y1, x2, y2 = (int(round(value)) for value in box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3, cv2.LINE_AA)
    label_y = max(22, y1 - 7)
    cv2.putText(
        frame,
        label,
        (x1, label_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2,
        cv2.LINE_AA,
    )


def _panel_title(frame: Frame, title: str) -> None:
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 42), (16, 16, 16), -1)
    cv2.putText(
        frame,
        title,
        (14, 29),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


def render_diagnostic(
    source_path: Path,
    ground_truth: list[GroundTruth],
    predictions: list[Prediction],
    output_path: Path,
    *,
    iou_threshold: float = 0.5,
    annotation_fps: float = 25.0,
) -> DiagnosticSummary:
    metadata = inspect_video(source_path)
    truths_by_frame: dict[int, list[GroundTruth]] = defaultdict(list)
    predictions_by_frame: dict[int, list[Prediction]] = defaultdict(list)
    for record in ground_truth:
        truths_by_frame[record.frame].append(record)
    for record in predictions:
        predictions_by_frame[record.frame].append(record)

    last_frame = max(truths_by_frame)
    panel_width = max(1, metadata.width // 2)
    panel_height = max(1, metadata.height // 2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(source_path))
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        annotation_fps,
        (panel_width * 2, panel_height),
    )
    if not capture.isOpened() or not writer.isOpened():
        capture.release()
        writer.release()
        raise RuntimeError("Could not initialize the diagnostic video reader or writer")

    match_count = 0
    annotation_frame = 1
    source_frame = 0
    try:
        while annotation_frame <= last_frame:
            ok, frame = capture.read()
            if not ok:
                break
            source_frame += 1
            wanted_source_frame = (
                round((annotation_frame - 1) * metadata.fps / annotation_fps) + 1
            )
            if source_frame < wanted_source_frame:
                continue
            truths = truths_by_frame.get(annotation_frame, [])
            frame_predictions = predictions_by_frame.get(annotation_frame, [])
            matches = match_frame(truths, frame_predictions, iou_threshold)
            match_count += len(matches)
            matched_truths = {truth_index for truth_index, _, _ in matches}
            matched_predictions = {prediction_index for _, prediction_index, _ in matches}

            truth_panel = frame.copy()
            prediction_panel = frame.copy()
            for index, truth in enumerate(truths):
                matched = index in matched_truths
                color = (40, 200, 40) if matched else (30, 30, 230)
                status = "MATCH" if matched else "MISS"
                _draw_box(
                    truth_panel,
                    truth.box_xyxy,
                    color,
                    f"{status} {truth.label} id={truth.identity}",
                )
            for index, prediction in enumerate(frame_predictions):
                matched = index in matched_predictions
                color = (40, 200, 40) if matched else (0, 165, 255)
                status = "MATCH" if matched else "UNMATCHED"
                track_id = "?" if prediction.track_id is None else prediction.track_id
                _draw_box(
                    prediction_panel,
                    prediction.box_xyxy,
                    color,
                    f"{status} track={track_id} {prediction.confidence:.2f}",
                )

            _panel_title(
                truth_panel,
                f"Annotation truth | frame {annotation_frame} | green=matched red=missed",
            )
            _panel_title(
                prediction_panel,
                f"YOLO + BoT-SORT | IoU >= {iou_threshold:.2f} | orange=unmatched",
            )
            left = cv2.resize(truth_panel, (panel_width, panel_height))
            right = cv2.resize(prediction_panel, (panel_width, panel_height))
            writer.write(np.hstack((left, right)))
            annotation_frame += 1
    finally:
        capture.release()
        writer.release()

    rendered_frames = annotation_frame - 1
    if rendered_frames != last_frame:
        raise ValueError(
            f"Video ended at frame {rendered_frames}, before annotation frame {last_frame}"
        )
    return DiagnosticSummary(
        output=str(output_path.resolve()),
        frames=rendered_frames,
        ground_truth_boxes=len(ground_truth),
        predicted_boxes=len(predictions),
        matches=match_count,
        missed_ground_truth=len(ground_truth) - match_count,
        unmatched_predictions=len(predictions) - match_count,
        iou_threshold=iou_threshold,
    )


def render_diagnostic_files(
    source_path: Path,
    gt_path: Path,
    labels_path: Path,
    predictions_path: Path,
    output_path: Path,
    iou_threshold: float,
    annotation_fps: float,
) -> DiagnosticSummary:
    ground_truth = load_afmot_ground_truth(gt_path, labels_path)
    max_frame = max(record.frame for record in ground_truth)
    source_fps = inspect_video(source_path).fps
    predictions = load_predictions(
        predictions_path,
        max_frame,
        source_fps=source_fps,
        annotation_fps=annotation_fps,
    )
    return render_diagnostic(
        source_path,
        ground_truth,
        predictions,
        output_path,
        iou_threshold=iou_threshold,
        annotation_fps=annotation_fps,
    )


def render_cvat_diagnostic_files(
    source_path: Path,
    annotations_path: Path,
    predictions_path: Path,
    output_path: Path,
    iou_threshold: float,
) -> DiagnosticSummary:
    from .cvat_annotations import load_cvat_ground_truth

    ground_truth = load_cvat_ground_truth(annotations_path)
    max_frame = max(record.frame for record in ground_truth)
    predictions = load_predictions(predictions_path, max_frame)
    return render_diagnostic(
        source_path,
        ground_truth,
        predictions,
        output_path,
        iou_threshold=iou_threshold,
        annotation_fps=inspect_video(source_path).fps,
    )


def diagnostic_summary_dict(summary: DiagnosticSummary) -> dict[str, object]:
    return asdict(summary)
