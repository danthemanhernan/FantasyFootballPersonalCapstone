from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class GroundTruth:
    frame: int
    identity: int
    label: str
    category: str
    box_xyxy: tuple[float, float, float, float]


@dataclass(frozen=True)
class Prediction:
    frame: int
    track_id: int | None
    confidence: float
    box_xyxy: tuple[float, float, float, float]


@dataclass(frozen=True)
class EvaluationReport:
    iou_threshold: float
    evaluated_frames: int
    ground_truth_boxes: int
    predicted_boxes: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    mean_matched_iou: float
    recall_by_category: dict[str, float]
    ground_truth_identities: int
    trackable_ground_truth_identities: int
    ambiguous_ground_truth_identities: int
    predicted_track_ids: int
    approximate_id_switches: int
    identities_with_fragmented_tracks: int
    mean_predicted_tracks_per_identity: float


def category_for_label(label: str) -> str:
    if label.startswith("ref_"):
        return "official"
    if label.startswith(("k", "h")):
        return "player"
    if label.startswith("unseen_"):
        return "unseen"
    return "other"


def load_afmot_ground_truth(gt_path: Path, labels_path: Path) -> list[GroundTruth]:
    labels = [line.strip() for line in labels_path.read_text().splitlines() if line.strip()]
    records: list[GroundTruth] = []
    for line_number, line in enumerate(gt_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split(",")
        if len(fields) != 9:
            raise ValueError(f"AFMOT row {line_number} has {len(fields)} columns, expected 9")
        frame = int(fields[0])
        x, y, width, height = (float(value) for value in fields[2:6])
        identity = int(fields[7])
        if not 1 <= identity <= len(labels):
            raise ValueError(f"AFMOT row {line_number} references unknown identity {identity}")
        label = labels[identity - 1]
        records.append(
            GroundTruth(
                frame=frame,
                identity=identity,
                label=label,
                category=category_for_label(label),
                box_xyxy=(x, y, x + width, y + height),
            )
        )
    return records


def load_predictions(
    path: Path,
    max_frame: int,
    *,
    source_fps: float | None = None,
    annotation_fps: float | None = None,
) -> list[Prediction]:
    source_to_annotation: dict[int, int] | None = None
    if source_fps is not None or annotation_fps is not None:
        if source_fps is None or annotation_fps is None:
            raise ValueError("source_fps and annotation_fps must be provided together")
        if source_fps <= 0 or annotation_fps <= 0:
            raise ValueError("frame rates must be positive")
        source_to_annotation = {
            round((frame - 1) * source_fps / annotation_fps) + 1: frame
            for frame in range(1, max_frame + 1)
        }
    records: list[Prediction] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        source_frame = int(payload["frame_index"]) + 1
        frame = (
            source_to_annotation.get(source_frame)
            if source_to_annotation is not None
            else source_frame
        )
        if frame is None or frame > max_frame:
            continue
        for detection in payload["detections"]:
            records.append(
                Prediction(
                    frame=frame,
                    track_id=detection["track_id"],
                    confidence=float(detection["confidence"]),
                    box_xyxy=tuple(float(value) for value in detection["box_xyxy"]),
                )
            )
    return records


def intersection_over_union(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union else 0.0


def match_frame(
    ground_truth: list[GroundTruth],
    predictions: list[Prediction],
    threshold: float,
) -> list[tuple[int, int, float]]:
    """Maximum-cardinality bipartite matching with IoU-prioritized edges."""
    adjacency: list[list[tuple[int, float]]] = []
    for truth in ground_truth:
        candidates = [
            (index, intersection_over_union(truth.box_xyxy, prediction.box_xyxy))
            for index, prediction in enumerate(predictions)
        ]
        adjacency.append(
            sorted(
                ((index, score) for index, score in candidates if score >= threshold),
                key=lambda item: item[1],
                reverse=True,
            )
        )

    prediction_to_truth: dict[int, tuple[int, float]] = {}

    def augment(truth_index: int, visited: set[int]) -> bool:
        for prediction_index, score in adjacency[truth_index]:
            if prediction_index in visited:
                continue
            visited.add(prediction_index)
            previous = prediction_to_truth.get(prediction_index)
            if previous is None or augment(previous[0], visited):
                prediction_to_truth[prediction_index] = (truth_index, score)
                return True
        return False

    for truth_index in range(len(ground_truth)):
        augment(truth_index, set())
    return [
        (truth_index, prediction_index, score)
        for prediction_index, (truth_index, score) in prediction_to_truth.items()
    ]


def safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def evaluate(
    ground_truth: list[GroundTruth],
    predictions: list[Prediction],
    *,
    iou_threshold: float = 0.5,
) -> EvaluationReport:
    truths_by_frame: dict[int, list[GroundTruth]] = defaultdict(list)
    predictions_by_frame: dict[int, list[Prediction]] = defaultdict(list)
    for record in ground_truth:
        truths_by_frame[record.frame].append(record)
    for record in predictions:
        predictions_by_frame[record.frame].append(record)

    matched_truths = 0
    matched_iou: list[float] = []
    category_totals: dict[str, int] = defaultdict(int)
    category_matches: dict[str, int] = defaultdict(int)
    identity_history: dict[int, list[tuple[int, int]]] = defaultdict(list)
    identity_counts_by_frame: dict[tuple[int, int], int] = defaultdict(int)
    for record in ground_truth:
        identity_counts_by_frame[(record.frame, record.identity)] += 1
    ambiguous_identities = {
        identity
        for (_, identity), count in identity_counts_by_frame.items()
        if count > 1
    }

    for frame in sorted(truths_by_frame):
        truths = truths_by_frame[frame]
        frame_predictions = predictions_by_frame.get(frame, [])
        matches = match_frame(truths, frame_predictions, iou_threshold)
        matched_truths += len(matches)
        matched_iou.extend(score for _, _, score in matches)
        for truth in truths:
            category_totals[truth.category] += 1
        for truth_index, prediction_index, _ in matches:
            truth = truths[truth_index]
            prediction = frame_predictions[prediction_index]
            category_matches[truth.category] += 1
            if (
                prediction.track_id is not None
                and truth.identity not in ambiguous_identities
            ):
                identity_history[truth.identity].append((frame, prediction.track_id))

    false_positives = len(predictions) - matched_truths
    false_negatives = len(ground_truth) - matched_truths
    precision = safe_ratio(matched_truths, len(predictions))
    recall = safe_ratio(matched_truths, len(ground_truth))
    track_sets = [set(track_id for _, track_id in history) for history in identity_history.values()]
    approximate_switches = 0
    for history in identity_history.values():
        ordered = sorted(history)
        approximate_switches += sum(
            current_track != previous_track
            for (_, previous_track), (_, current_track) in zip(ordered, ordered[1:])
        )

    return EvaluationReport(
        iou_threshold=iou_threshold,
        evaluated_frames=len(truths_by_frame),
        ground_truth_boxes=len(ground_truth),
        predicted_boxes=len(predictions),
        true_positives=matched_truths,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=safe_ratio(2 * precision * recall, precision + recall),
        mean_matched_iou=safe_ratio(sum(matched_iou), len(matched_iou)),
        recall_by_category={
            category: safe_ratio(category_matches[category], total)
            for category, total in sorted(category_totals.items())
        },
        ground_truth_identities=len({record.identity for record in ground_truth}),
        trackable_ground_truth_identities=len(
            {record.identity for record in ground_truth} - ambiguous_identities
        ),
        ambiguous_ground_truth_identities=len(ambiguous_identities),
        predicted_track_ids=len(
            {record.track_id for record in predictions if record.track_id is not None}
        ),
        approximate_id_switches=approximate_switches,
        identities_with_fragmented_tracks=sum(len(track_ids) > 1 for track_ids in track_sets),
        mean_predicted_tracks_per_identity=safe_ratio(
            sum(len(track_ids) for track_ids in track_sets), len(track_sets)
        ),
    )


def evaluate_files(
    gt_path: Path,
    labels_path: Path,
    predictions_path: Path,
    output_path: Path | None,
    iou_threshold: float,
    source_fps: float | None = None,
    annotation_fps: float | None = None,
) -> EvaluationReport:
    ground_truth = load_afmot_ground_truth(gt_path, labels_path)
    max_frame = max(record.frame for record in ground_truth)
    predictions = load_predictions(
        predictions_path,
        max_frame,
        source_fps=source_fps,
        annotation_fps=annotation_fps,
    )
    report = evaluate(ground_truth, predictions, iou_threshold=iou_threshold)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(asdict(report), indent=2) + "\n")
    return report
