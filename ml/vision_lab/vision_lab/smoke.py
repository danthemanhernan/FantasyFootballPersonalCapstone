from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def make_smoke_video(
    path: str | Path,
    *,
    frame_count: int = 60,
    width: int = 640,
    height: int = 360,
    fps: float = 30.0,
) -> Path:
    """Create an I/O fixture, not a realistic detector benchmark."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(destination), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not create smoke video: {destination}")
    try:
        for index in range(frame_count):
            frame = np.full((height, width, 3), (45, 115, 45), dtype=np.uint8)
            x = 30 + int((width - 100) * index / max(frame_count - 1, 1))
            cv2.rectangle(frame, (x, 120), (x + 40, 230), (245, 245, 245), -1)
            cv2.putText(
                frame,
                f"I/O smoke frame {index:03d}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )
            writer.write(frame)
    finally:
        writer.release()
    return destination
