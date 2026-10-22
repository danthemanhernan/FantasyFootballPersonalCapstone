"""Small, inspectable building blocks for the Fantasy HUD vision lab."""

from .pipeline import Detection, RunSummary, VideoMetadata, inspect_video, run_video
from .shot_detection import ShotDecision, ShotGate, ShotScanSummary, scan_shots

__all__ = [
    "Detection",
    "RunSummary",
    "ShotDecision",
    "ShotGate",
    "ShotScanSummary",
    "VideoMetadata",
    "inspect_video",
    "run_video",
    "scan_shots",
]
