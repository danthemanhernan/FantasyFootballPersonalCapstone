from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from .afmot_evaluator import (
    GroundTruth,
    evaluate,
    intersection_over_union,
    load_predictions,
)


@dataclass(frozen=True)
class CvatValidationReport:
    annotation_file: str
    frame_count: int
    track_count: int
    visible_box_count: int
    labels: dict[str, int]
    track_sources: dict[str, int]
    empty_frames: list[int]
    invalid_boxes: int
    short_tracks_at_most_3_frames: int
    short_tracks_at_most_10_frames: int
    tracks_with_internal_visibility_gaps: int
    alternating_visibility_suspects: list[int]
    tracks_crossing_shot_boundaries: list[int]
    same_label_overlap_pairs_iou_50: int
    same_label_overlap_pairs_iou_75: int
    cross_label_overlap_pairs_iou_50: int
    player_team_values: dict[str, int]
    player_jersey_visible_values: dict[str, int]
    warnings: list[str]


def _root(path: Path) -> ET.Element:
    return ET.parse(path).getroot()


def load_cvat_ground_truth(path: Path) -> list[GroundTruth]:
    """Load visible CVAT video boxes, converting zero-based CVAT frames to one-based."""
    records: list[GroundTruth] = []
    for track in _root(path).findall(".//track"):
        identity = int(track.attrib["id"])
        label = track.attrib["label"]
        for box in track.findall("box"):
            if box.attrib.get("outside", "0") == "1":
                continue
            records.append(
                GroundTruth(
                    frame=int(box.attrib["frame"]) + 1,
                    identity=identity,
                    label=label,
                    category=label,
                    box_xyxy=tuple(
                        float(box.attrib[key])
                        for key in ("xtl", "ytl", "xbr", "ybr")
                    ),
                )
            )
    return records


def validate_cvat(
    path: Path,
    *,
    shot_start_frames: tuple[int, ...] = (),
) -> CvatValidationReport:
    root = _root(path)
    tracks = root.findall(".//track")
    size_text = root.findtext("./meta/job/size")
    frame_count = int(size_text) if size_text else 0
    width = float(root.findtext("./meta/original_size/width", "0"))
    height = float(root.findtext("./meta/original_size/height", "0"))

    labels: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    team_values: Counter[str] = Counter()
    jersey_values: Counter[str] = Counter()
    boxes_by_frame: dict[int, list[GroundTruth]] = defaultdict(list)
    track_lengths: list[int] = []
    gap_tracks = 0
    alternating_suspects: list[int] = []
    crossing_tracks: list[int] = []
    invalid_boxes = 0

    for track in tracks:
        track_id = int(track.attrib["id"])
        label = track.attrib["label"]
        labels[label] += 1
        sources[track.attrib.get("source", "unknown")] += 1
        visible_frames: list[int] = []
        for box in track.findall("box"):
            if box.attrib.get("outside", "0") == "1":
                continue
            frame = int(box.attrib["frame"])
            coords = tuple(
                float(box.attrib[key]) for key in ("xtl", "ytl", "xbr", "ybr")
            )
            if (
                coords[0] < 0
                or coords[1] < 0
                or coords[2] > width
                or coords[3] > height
                or coords[2] <= coords[0]
                or coords[3] <= coords[1]
            ):
                invalid_boxes += 1
            visible_frames.append(frame)
            record = GroundTruth(frame + 1, track_id, label, label, coords)
            boxes_by_frame[frame].append(record)
            if label == "player":
                attributes = {
                    item.attrib.get("name", ""): (item.text or "").strip()
                    for item in box.findall("attribute")
                }
                team_values[attributes.get("team", "missing")] += 1
                jersey_values[attributes.get("jersey_visible", "missing")] += 1

        track_lengths.append(len(visible_frames))
        if visible_frames:
            gaps = [
                right - left
                for left, right in zip(visible_frames, visible_frames[1:])
                if right - left > 1
            ]
            if gaps:
                gap_tracks += 1
            if sum(gap == 2 for gap in gaps) >= 3:
                alternating_suspects.append(track_id)
            if any(
                min(visible_frames) < boundary <= max(visible_frames)
                for boundary in shot_start_frames
            ):
                crossing_tracks.append(track_id)

    overlaps = {0.5: [0, 0], 0.75: [0, 0]}
    for records in boxes_by_frame.values():
        for index, left in enumerate(records):
            for right in records[index + 1 :]:
                score = intersection_over_union(left.box_xyxy, right.box_xyxy)
                for threshold, counts in overlaps.items():
                    if score >= threshold:
                        counts[0 if left.label == right.label else 1] += 1

    empty_frames = [
        frame for frame in range(frame_count) if not boxes_by_frame.get(frame)
    ]
    warnings: list[str] = []
    if alternating_suspects:
        warnings.append(
            "Some tracks alternate visible/outside across nearby frames; review them in CVAT."
        )
    if crossing_tracks:
        warnings.append(
            "Some identities span a declared camera cut; split them unless identity is certain."
        )
    if overlaps[0.75][0] or overlaps[0.75][1]:
        warnings.append("Near-duplicate boxes with IoU >= 0.75 need review.")
    if team_values.get("unknown", 0):
        warnings.append("Player team attributes are still mostly or entirely unknown.")

    return CvatValidationReport(
        annotation_file=str(path.resolve()),
        frame_count=frame_count,
        track_count=len(tracks),
        visible_box_count=sum(track_lengths),
        labels=dict(sorted(labels.items())),
        track_sources=dict(sorted(sources.items())),
        empty_frames=empty_frames,
        invalid_boxes=invalid_boxes,
        short_tracks_at_most_3_frames=sum(length <= 3 for length in track_lengths),
        short_tracks_at_most_10_frames=sum(length <= 10 for length in track_lengths),
        tracks_with_internal_visibility_gaps=gap_tracks,
        alternating_visibility_suspects=sorted(alternating_suspects),
        tracks_crossing_shot_boundaries=sorted(crossing_tracks),
        same_label_overlap_pairs_iou_50=overlaps[0.5][0],
        same_label_overlap_pairs_iou_75=overlaps[0.75][0],
        cross_label_overlap_pairs_iou_50=overlaps[0.5][1],
        player_team_values=dict(sorted(team_values.items())),
        player_jersey_visible_values=dict(sorted(jersey_values.items())),
        warnings=warnings,
    )


def write_validation_report(
    path: Path,
    output_path: Path,
    *,
    shot_start_frames: tuple[int, ...] = (),
) -> CvatValidationReport:
    report = validate_cvat(path, shot_start_frames=shot_start_frames)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(report), indent=2) + "\n")
    return report


def evaluate_cvat_files(
    annotations_path: Path,
    predictions_path: Path,
    output_path: Path | None,
    iou_threshold: float,
):
    ground_truth = load_cvat_ground_truth(annotations_path)
    max_frame = max(record.frame for record in ground_truth)
    predictions = load_predictions(predictions_path, max_frame)
    report = evaluate(ground_truth, predictions, iou_threshold=iou_threshold)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(asdict(report), indent=2) + "\n")
    return report
