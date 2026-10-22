from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from .pipeline import inspect_video, run_video
from .smoke import make_smoke_video


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vision-lab")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="Report the local vision runtime")

    smoke = commands.add_parser("make-smoke", help="Create a deterministic I/O fixture")
    smoke.add_argument("--output", type=Path, default=Path("data/smoke.mp4"))
    smoke.add_argument("--frames", type=int, default=60)

    inspect = commands.add_parser("inspect", help="Read video metadata without inference")
    inspect.add_argument("source", type=Path)

    track = commands.add_parser("track", help="Detect and track people in a video")
    track.add_argument("source", type=Path)
    track.add_argument("--output-dir", type=Path, default=Path("runs/baseline"))
    track.add_argument("--model", default="yolo26n.pt")
    track.add_argument("--tracker", default="botsort.yaml")
    track.add_argument("--device", default="auto")
    track.add_argument("--confidence", type=float, default=0.25)
    track.add_argument("--max-frames", type=int)

    evaluate = commands.add_parser(
        "evaluate-afmot", help="Compare JSONL predictions with AFMOT annotations"
    )
    evaluate.add_argument("--ground-truth", type=Path, required=True)
    evaluate.add_argument("--labels", type=Path, required=True)
    evaluate.add_argument("--predictions", type=Path, required=True)
    evaluate.add_argument("--output", type=Path)
    evaluate.add_argument("--iou-threshold", type=float, default=0.5)
    evaluate.add_argument(
        "--source", type=Path, help="Video used to align prediction and annotation rates"
    )
    evaluate.add_argument("--annotation-fps", type=float, default=25.0)

    render = commands.add_parser(
        "render-afmot", help="Render AFMOT truth beside JSONL predictions"
    )
    render.add_argument("--source", type=Path, required=True)
    render.add_argument("--ground-truth", type=Path, required=True)
    render.add_argument("--labels", type=Path, required=True)
    render.add_argument("--predictions", type=Path, required=True)
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--iou-threshold", type=float, default=0.5)
    render.add_argument("--annotation-fps", type=float, default=25.0)

    cvat = commands.add_parser(
        "export-cvat-mot", help="Convert tracked JSONL predictions to a CVAT MOT archive"
    )
    cvat.add_argument("--predictions", type=Path, required=True)
    cvat.add_argument("--output", type=Path, required=True)

    validate_cvat = commands.add_parser(
        "validate-cvat", help="Check CVAT video annotations for structural issues"
    )
    validate_cvat.add_argument("--annotations", type=Path, required=True)
    validate_cvat.add_argument("--output", type=Path, required=True)
    validate_cvat.add_argument(
        "--shot-start-frame", type=int, action="append", default=[]
    )

    evaluate_cvat = commands.add_parser(
        "evaluate-cvat", help="Compare JSONL predictions with CVAT video annotations"
    )
    evaluate_cvat.add_argument("--annotations", type=Path, required=True)
    evaluate_cvat.add_argument("--predictions", type=Path, required=True)
    evaluate_cvat.add_argument("--output", type=Path, required=True)
    evaluate_cvat.add_argument("--iou-threshold", type=float, default=0.5)

    render_cvat = commands.add_parser(
        "render-cvat", help="Render CVAT truth beside JSONL predictions"
    )
    render_cvat.add_argument("--source", type=Path, required=True)
    render_cvat.add_argument("--annotations", type=Path, required=True)
    render_cvat.add_argument("--predictions", type=Path, required=True)
    render_cvat.add_argument("--output", type=Path, required=True)
    render_cvat.add_argument("--iou-threshold", type=float, default=0.5)
    return parser


def doctor() -> dict[str, object]:
    report: dict[str, object] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "ffmpeg": shutil.which("ffmpeg"),
    }
    try:
        from .ultralytics_adapter import choose_device

        report["model_dependencies"] = "installed"
        report["automatic_device"] = choose_device()
    except RuntimeError as error:
        report["model_dependencies"] = "not installed"
        report["automatic_device"] = None
        report["next_action"] = str(error)
    return report


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "doctor":
        payload = doctor()
    elif args.command == "make-smoke":
        payload = {"created": str(make_smoke_video(args.output, frame_count=args.frames))}
    elif args.command == "inspect":
        payload = asdict(inspect_video(args.source))
    elif args.command == "track":
        from .ultralytics_adapter import UltralyticsTracker

        detector = UltralyticsTracker(
            model=args.model,
            tracker=args.tracker,
            device=args.device,
            confidence=args.confidence,
            classes=[0],
        )
        payload = asdict(
            run_video(args.source, args.output_dir, detector, max_frames=args.max_frames)
        )
    elif args.command == "evaluate-afmot":
        from .afmot_evaluator import evaluate_files

        source_fps = inspect_video(args.source).fps if args.source else None
        annotation_fps = args.annotation_fps if args.source else None

        payload = asdict(
            evaluate_files(
                args.ground_truth,
                args.labels,
                args.predictions,
                args.output,
                args.iou_threshold,
                source_fps,
                annotation_fps,
            )
        )
    elif args.command == "render-afmot":
        from .afmot_diagnostics import render_diagnostic_files

        payload = asdict(
            render_diagnostic_files(
                args.source,
                args.ground_truth,
                args.labels,
                args.predictions,
                args.output,
                args.iou_threshold,
                args.annotation_fps,
            )
        )
    elif args.command == "export-cvat-mot":
        from .cvat_export import export_cvat_mot

        payload = export_cvat_mot(args.predictions, args.output)
    elif args.command == "validate-cvat":
        from .cvat_annotations import write_validation_report

        payload = asdict(
            write_validation_report(
                args.annotations,
                args.output,
                shot_start_frames=tuple(args.shot_start_frame),
            )
        )
    elif args.command == "evaluate-cvat":
        from .cvat_annotations import evaluate_cvat_files

        payload = asdict(
            evaluate_cvat_files(
                args.annotations,
                args.predictions,
                args.output,
                args.iou_threshold,
            )
        )
    else:
        from .afmot_diagnostics import render_cvat_diagnostic_files

        payload = asdict(
            render_cvat_diagnostic_files(
                args.source,
                args.annotations,
                args.predictions,
                args.output,
                args.iou_threshold,
            )
        )
    print(json.dumps(payload, indent=2))
