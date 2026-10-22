from __future__ import annotations

from collections.abc import Sequence

from .pipeline import Detection, Frame, normalize_box


def choose_device() -> str:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "Model dependencies are missing. Run `uv sync --group model --group test`."
        ) from exc
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class UltralyticsTracker:
    def __init__(
        self,
        model: str,
        tracker: str,
        device: str,
        confidence: float,
        classes: Sequence[int],
    ) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "Ultralytics is missing. Run `uv sync --group model --group test`."
            ) from exc
        self.model_name = model
        self.tracker_name = tracker
        self.device_name = choose_device() if device == "auto" else device
        self._confidence = confidence
        self._classes = list(classes)
        self._model = YOLO(model)

    def process(self, frame: Frame) -> tuple[Frame, list[Detection]]:
        result = self._model.track(
            frame,
            persist=True,
            tracker=self.tracker_name,
            classes=self._classes,
            conf=self._confidence,
            device=self.device_name,
            verbose=False,
        )[0]
        detections: list[Detection] = []
        boxes = result.boxes
        if boxes is not None:
            coordinates = boxes.xyxy.detach().cpu().tolist()
            confidences = boxes.conf.detach().cpu().tolist()
            class_ids = boxes.cls.detach().cpu().tolist()
            raw_track_ids = (
                boxes.id.detach().cpu().tolist()
                if boxes.id is not None
                else [None] * len(coordinates)
            )
            height, width = frame.shape[:2]
            for box, confidence, class_id, track_id in zip(
                coordinates, confidences, class_ids, raw_track_ids, strict=True
            ):
                integer_class = int(class_id)
                detections.append(
                    Detection(
                        class_id=integer_class,
                        class_name=result.names[integer_class],
                        confidence=float(confidence),
                        box_xyxy=tuple(float(value) for value in box),
                        box_normalized=normalize_box(box, width, height),
                        track_id=int(track_id) if track_id is not None else None,
                    )
                )
        return result.plot(), detections
