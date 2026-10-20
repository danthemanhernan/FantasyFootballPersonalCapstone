"""Split permitted football recordings and create CVAT-ready YOLO preannotations.

Dependencies: scenedetect, opencv-python, ultralytics, numpy; ffmpeg on PATH.
Usage: python -m services.vision.prepare_dataset --input game.mp4 --output artifacts/game --model best.pt
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path


def detect_scenes(video: Path, threshold: float, min_scene_len: int):
    from scenedetect import detect, ContentDetector
    return detect(str(video), ContentDetector(threshold=threshold, min_scene_len=min_scene_len))


def run_ffmpeg(source: Path, target: Path, start: float, duration: float) -> None:
    """Re-encode for frame-accurate boundaries rather than keyframe-only cuts."""
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{start:.6f}", "-i", str(source), "-t", f"{duration:.6f}",
        "-map", "0:v:0", "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "22", str(target),
    ], check=True)


def prepare(input_path: str, output_path: str, model_path: str | None = None,
            threshold: float = 27.0, sample_fps: float = 2.0,
            min_scene_len: int = 15, confidence: float = 0.25,
            gameplay_only: bool = False) -> dict:
    """Return reproducible scene clips, sampled images and optional YOLO labels.

    When gameplay_only=True, select scenes with at least two player detections
    in sampled frames; this is a *heuristic*, not a trained scene classifier.
    """
    import cv2
    if sample_fps <= 0 or min_scene_len <= 0:
        raise ValueError("sample_fps and min_scene_len must be positive")
    source = Path(input_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    output = Path(output_path).resolve()
    clips, images, labels = (output / name for name in ("clips", "images", "labels"))
    for directory in (clips, images, labels):
        directory.mkdir(parents=True, exist_ok=True)
    detector = None
    if model_path:
        from ultralytics import YOLO
        detector = YOLO(model_path)
    if gameplay_only and detector is None:
        raise ValueError("--gameplay-only requires --model")
    scenes = detect_scenes(source, threshold, min_scene_len)
    if not scenes:
        raise ValueError("No scenes detected; verify the recording and codec")
    manifest = []
    for index, (start, end) in enumerate(scenes):
        start_s, end_s = start.get_seconds(), end.get_seconds()
        if end_s <= start_s:
            continue
        scene_id = f"shot_{index:04d}"
        clip = clips / f"{scene_id}.mp4"
        run_ffmpeg(source, clip, start_s, end_s - start_s)
        capture = cv2.VideoCapture(str(clip))
        if not capture.isOpened():
            raise RuntimeError(f"Could not read generated clip {clip}")
        fps = capture.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            capture.release()
            raise ValueError(f"Invalid FPS in {clip}")
        frame_id = 0
        next_sample = 0.0
        sampled = []
        gameplay_votes = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                elapsed = frame_id / fps
                frame_id += 1
                if elapsed + 1e-9 < next_sample:
                    continue
                next_sample = elapsed + 1 / sample_fps
                detections = []
                if detector is not None:
                    prediction = detector.predict(frame, conf=confidence, verbose=False)[0]
                    for box in prediction.boxes:
                        cls = int(box.cls[0])
                        name = str(detector.names[cls]).lower()
                        # Default COCO models use 'person'; fine-tuned models may
                        # use 'player' or 'referee'. Do not label other COCO classes.
                        if name not in ("person", "player", "referee", "official"):
                            continue
                        x, y, w, h = (float(v) for v in box.xywhn[0].tolist())
                        detections.append((cls, x, y, w, h, name))
                    gameplay_votes += int(sum(d[-1] in ("person", "player") for d in detections) >= 2)
                sampled.append((frame.copy(), detections, elapsed))
        finally:
            capture.release()
        keep = not gameplay_only or gameplay_votes >= max(1, len(sampled) // 3)
        if keep:
            for sample_index, (frame, detections, elapsed) in enumerate(sampled):
                stem = f"{scene_id}_{sample_index:05d}"
                if not cv2.imwrite(str(images / f"{stem}.jpg"), frame):
                    raise IOError(f"Could not write image {stem}")
                # Remap model class IDs to a contiguous export vocabulary.
                # COCO 'person' and fine-tuned 'player' share class 0.
                # 'referee'/'official' use class 1.
                with (labels / f"{stem}.txt").open("w") as handle:
                    for _, x, y, w, h, name in detections:
                        label = 1 if name in ("referee", "official") else 0
                        handle.write(f"{label} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
        manifest.append({
            "scene_id": scene_id, "source": str(source),
            "start_s": round(start_s, 6), "end_s": round(end_s, 6),
            "clip": str(clip.relative_to(output)), "sampled_frames": len(sampled),
            "kept_for_detection": keep, "gameplay_votes": gameplay_votes,
        })
    with (output / "manifest.json").open("w") as handle:
        json.dump({"source": str(source), "model": model_path,
                   "threshold": threshold, "sample_fps": sample_fps,
                   "scenes": manifest}, handle, indent=2)
    with (output / "classes.txt").open("w") as handle:
        handle.write("player\nreferee\n")
    with (output / "scenes.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest[0]) if manifest else [])
        writer.writeheader()
        writer.writerows(manifest)
    return {"scenes": len(manifest), "kept": sum(s["kept_for_detection"] for s in manifest),
            "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default=None, help="YOLO model weights; omit for unlabeled samples")
    parser.add_argument("--threshold", type=float, default=27.0)
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--min-scene-len", type=int, default=15)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--gameplay-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(args.input, args.output, args.model, args.threshold,
                             args.sample_fps, args.min_scene_len, args.confidence,
                             args.gameplay_only), indent=2))


if __name__ == "__main__":
    main()
