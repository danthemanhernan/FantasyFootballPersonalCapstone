import json
from pathlib import Path

import cv2

from vision_lab.pipeline import Detection, inspect_video, normalize_box, percentile, run_video
from vision_lab.smoke import make_smoke_video


class FakeTracker:
    model_name = "fake-person-detector"
    tracker_name = "fake-tracker"
    device_name = "cpu"

    def process(self, frame):
        height, width = frame.shape[:2]
        box = (10.0, 20.0, 50.0, 100.0)
        detection = Detection(
            class_id=0,
            class_name="person",
            confidence=0.9,
            box_xyxy=box,
            box_normalized=normalize_box(box, width, height),
            track_id=7,
        )
        annotated = frame.copy()
        cv2.rectangle(annotated, (10, 20), (50, 100), (0, 0, 255), 2)
        return annotated, [detection]


def test_smoke_video_can_be_inspected(tmp_path: Path):
    video = make_smoke_video(tmp_path / "smoke.mp4", frame_count=12)
    metadata = inspect_video(video)
    assert metadata.width == 640
    assert metadata.height == 360
    assert metadata.frame_count == 12
    assert metadata.duration_seconds == 0.4


def test_pipeline_emits_video_jsonl_and_summary(tmp_path: Path):
    source = make_smoke_video(tmp_path / "source.mp4", frame_count=8)
    summary = run_video(source, tmp_path / "run", FakeTracker())
    records = Path(summary.frame_records).read_text(encoding="utf-8").splitlines()
    first = json.loads(records[0])
    assert summary.processed_frames == 8
    assert summary.detections == 8
    assert summary.unique_track_ids == 1
    assert Path(summary.annotated_video).exists()
    assert first["detections"][0]["track_id"] == 7
    assert json.loads((tmp_path / "run" / "summary.json").read_text())["model"] == "fake-person-detector"


def test_normalization_clips_to_frame():
    assert normalize_box((-10, 25, 220, 75), 200, 100) == (0.0, 0.25, 1.0, 0.75)


def test_percentile_interpolates():
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
