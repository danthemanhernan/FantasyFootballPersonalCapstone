# NFL recording -> shot clips -> CVAT correction

This workflow is **offline** and operates only on recordings you are permitted to process. No DRM bypass or live streaming capture is included.

## M4 MacBook setup

From the repository root, in a Python virtual environment:

```bash
brew install ffmpeg
pip install "scenedetect[opencv]" ultralytics
python -m services.vision.prepare_dataset --input /path/to/game.mp4 --output artifacts/game1 --model /path/to/best.pt --sample-fps 2
```

The `--model` flag is optional. Without it, images and empty label files are generated for manual annotation. With it, YOLO predictions are exported in YOLO bounding-box format. Use your **fine-tuned** player/referee weights where possible; a generic COCO model detects people but cannot distinguish referees from players. Model class names are normalized to `player` (0) and `referee` (1). Review these predictions before treating them as ground truth.

Output:
- `clips/shot_XXXX.mp4`: frame-accurate, re-encoded camera-shot clips for later tracking annotation.
- `images/*.jpg`: sampled detection images.
- `labels/*.txt`: corresponding YOLO box annotations, including empty files.
- `classes.txt`: exported class order.
- `manifest.json` and `scenes.csv`: original source, scene timestamps, sample counts, and filtering decisions.

To import into CVAT, create an **image** task from `images/`, define labels `player` and `referee` in that order, then upload annotations in CVAT's **Ultralytics YOLO Detection** format. Depending on your CVAT version, package `images/`, `labels/`, and a matching `data.yaml` into the expected dataset archive; alternatively import the labels using the task's supported YOLO annotation import. Confirm the exact CVAT version's expected archive layout before bulk importing. For **tracking**, create separate video tasks from the `clips/` files; do not expect image-sample annotations to supply persistent track IDs.

Optional `--gameplay-only` uses a crude >=2 detected players heuristic across at least one third of sampled frames. It can reject real gameplay and accept sidelines, so inspect the manifest and keep the default (no filtering) until validated.

Shot detection is imperfect around replay wipes, zooms, fast pans and score graphics. Review scene boundaries. Preserve original recordings. Split train/validation by **game**, not by frame or clip from the same game. Log annotation time per 100 reviewed images to quantify the benefit.
