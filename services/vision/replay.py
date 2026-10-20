"""Recorded-video adapter and replayable, timestamped cut log.

Install: pip install opencv-python numpy
Run: python -m services.vision.replay --input permitted-game.mp4 --output cuts.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .shot_gate import ShotGate


def replay(input_path: str, output_path: str, threshold: float = 0.55, sample_fps: float = 10.0) -> dict:
    import cv2

    if sample_fps <= 0:
        raise ValueError("sample_fps must be positive")
    capture = cv2.VideoCapture(input_path)
    if not capture.isOpened():
        raise FileNotFoundError(f"Cannot open video: {input_path}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        capture.release()
        raise ValueError("Video does not expose a valid FPS")
    gate = ShotGate(threshold=threshold)
    decoded = sampled = cuts = 0
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    next_sample_time = 0.0
    try:
        with output.open("w", encoding="utf-8") as log:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                timestamp_s = decoded / fps
                decoded += 1
                if timestamp_s + 1e-9 < next_sample_time:
                    continue
                next_sample_time = timestamp_s + 1.0 / sample_fps
                decision = gate.update(frame)
                sampled += 1
                cuts += int(decision.cut)
                log.write(json.dumps({
                    "frame_id": decoded - 1, "timestamp_s": round(timestamp_s, 6),
                    "shot_id": decision.shot_id, "camera_cut": decision.cut,
                    "cut_distance": round(decision.distance, 5),
                }) + "\n")
    finally:
        capture.release()
    return {"decoded_frames": decoded, "sampled_frames": sampled, "camera_cuts": cuts, "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Authorized recorded video")
    parser.add_argument("--output", default="artifacts/vision/cuts.jsonl")
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--sample-fps", type=float, default=10.0)
    args = parser.parse_args()
    print(json.dumps(replay(args.input, args.output, args.threshold, args.sample_fps), indent=2))


if __name__ == "__main__":
    main()
