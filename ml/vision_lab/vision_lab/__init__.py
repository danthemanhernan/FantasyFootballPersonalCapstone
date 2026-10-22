"""Small, inspectable building blocks for the Fantasy HUD vision lab."""

from .dataset_preparation import PreparationSummary, PreparedClip, prepare_shot_clips
from .pipeline import Detection, RunSummary, VideoMetadata, inspect_video, run_video
from .shot_detection import ShotDecision, ShotGate, ShotScanSummary, scan_shots

__all__ = [
    "Detection",
    "PreparationSummary",
    "PreparedClip",
    "RunSummary",
    "ShotDecision",
    "ShotGate",
    "ShotScanSummary",
    "VideoMetadata",
    "inspect_video",
    "prepare_shot_clips",
    "run_video",
    "scan_shots",
]
