from __future__ import annotations

import json
import zipfile
from pathlib import Path


def export_cvat_mot(predictions_path: Path, output_path: Path) -> dict[str, object]:
    rows: list[str] = []
    track_ids: set[int] = set()
    for line in predictions_path.read_text().splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        frame = int(payload["frame_index"]) + 1
        for detection in payload["detections"]:
            track_id = detection.get("track_id")
            if track_id is None:
                continue
            x1, y1, x2, y2 = (float(value) for value in detection["box_xyxy"])
            width = max(0.0, x2 - x1)
            height = max(0.0, y2 - y1)
            if width == 0 or height == 0:
                continue
            track_ids.add(int(track_id))
            rows.append(
                f"{frame},{int(track_id)},{x1:.2f},{y1:.2f},"
                f"{width:.2f},{height:.2f},1,1,1.0"
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("gt/gt.txt", "\n".join(rows) + "\n")
        archive.writestr("gt/labels.txt", "player\n")
    return {
        "output": str(output_path.resolve()),
        "boxes": len(rows),
        "tracks": len(track_ids),
    }
