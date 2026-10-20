"""Lightweight, model-independent broadcast cut detection for authorized footage."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class ShotDecision:
    cut: bool
    distance: float
    shot_id: int


class ShotGate:
    """Histogram-based candidate cut gate. Calibrate threshold on NFL footage.

    Input frames are BGR uint8 arrays; the first frame starts shot zero.
    """

    def __init__(self, threshold: float = 0.55, bins: int = 32):
        if not 0 < threshold <= 1:
            raise ValueError("threshold must be in (0, 1]")
        if bins < 2:
            raise ValueError("bins must be >= 2")
        self.threshold = threshold
        self.bins = bins
        self.previous: np.ndarray | None = None
        self.shot_id = 0

    def update(self, frame: np.ndarray) -> ShotDecision:
        if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
            raise ValueError("Expected HxWx3 uint8 BGR frame")
        histograms = []
        for channel in range(3):
            histogram, _ = np.histogram(frame[:, :, channel], bins=self.bins, range=(0, 256))
            histogram = histogram.astype(np.float64)
            histogram /= max(histogram.sum(), 1)
            histograms.append(histogram)
        current = np.concatenate(histograms)
        distance = 0.0 if self.previous is None else float(
            np.abs(current - self.previous).sum() / 6.0
        )
        cut = self.previous is not None and distance >= self.threshold
        if cut:
            self.shot_id += 1
        self.previous = current
        return ShotDecision(cut=bool(cut), distance=distance, shot_id=self.shot_id)
