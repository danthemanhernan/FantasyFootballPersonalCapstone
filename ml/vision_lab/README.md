# Vision Lab 1: video to tracked people

This lab makes the first complete vision loop observable before any custom
training. It decodes video frames, runs person detection and online tracking,
then writes an annotated video, frame-level JSONL records, and a timing summary.

The generated smoke clip validates plumbing only. Rectangles are not football
players, so its detections are not model-quality evidence.

## 1. Build the lightweight lab

```bash
cd ml/vision_lab
uv sync --group test
uv run pytest -q
uv run vision-lab doctor
```

## 2. Exercise video I/O without a model download

```bash
uv run vision-lab make-smoke --output data/smoke.mp4 --frames 90
uv run vision-lab inspect data/smoke.mp4
```

Observe that a video is discrete frames plus timing metadata: width, height,
frame rate, frame count, and duration. Frame index divided by FPS gives media
time only for constant-frame-rate video.

## 3. Install and run the pretrained baseline

```bash
uv sync --group model --group test
uv run vision-lab track /absolute/path/to/football-clip.mp4 \
  --output-dir runs/football-baseline \
  --model yolo26n.pt \
  --tracker botsort.yaml \
  --device auto \
  --max-frames 900
```

The first run downloads model weights. Class `0` is COCO `person`; the baseline
does not yet know player, official, team, jersey number, or identity.

Inspect these artifacts:

- `annotated.mp4`: visual diagnostic, never the only evidence.
- `frames.jsonl`: replayable boxes, confidences, track IDs, and media times.
- `summary.json`: reproducibility metadata and throughput/latency measurements.

## 4. Diagnose three failures

Find one missed player, one false positive, and one identity switch. Record the
timestamp, shot type, occlusion, subject size, blur, and likely cause. Do not
tune yet. The purpose is to learn whether the problem came from detection,
association, scene handling, or the data distribution.

## Stop point

Stop when tests pass, the I/O smoke clip is inspectable, and one real clip has
produced all three artifacts. This is a learning baseline, not the V15 model
selection decision.

## Evaluate the AFMOT baseline

AFMOT stores identity indices in column eight of its `gt.txt`; they map to the
one-based lines in `labels.txt`. Evaluate only the labeled frame range:

```bash
uv run vision-lab evaluate-afmot \
  --source data/afmot/videos/kh_wide_005.mp4 \
  --ground-truth data/afmot/ver20/kh_wide_005/gt.txt \
  --labels data/afmot/ver20/kh_wide_005/labels.txt \
  --predictions runs/afmot-kh-wide-005-baseline/frames.jsonl \
  --output runs/afmot-kh-wide-005-baseline/evaluation.json
```

This sequence's downloadable video is 30 FPS while its 451 annotation frames
represent the same 18 seconds at 25 FPS. `--source` samples predictions onto the
annotation timebase. Omitting it incorrectly compares frame numbers rather than
media times and produces increasingly displaced boxes.

The detection metrics use one-to-one IoU matching at 0.5. Fragmentation and ID
switch counts are diagnostics derived from those matches; they are not official
HOTA, AssA, MOTA, or IDF1. Those require the TrackEval integration in the next
evaluation lab.

The downloaded AFMOT export stores `-1` in the standard MOT track-ID column,
and some IDs from its label column occur more than once in a frame. The evaluator
reports those IDs as ambiguous and excludes them from its approximate association
diagnostics. Do not convert this file to TrackEval and call the result official;
use an export containing persistent track IDs or create a clean CVAT benchmark.

Before trusting the aggregate score, render the labeled range beside the model
output and confirm that frame 1 in the video is frame 1 in the annotations:

```bash
uv run vision-lab render-afmot \
  --source data/afmot/videos/kh_wide_005.mp4 \
  --ground-truth data/afmot/ver20/kh_wide_005/gt.txt \
  --labels data/afmot/ver20/kh_wide_005/labels.txt \
  --predictions runs/afmot-kh-wide-005-baseline/frames.jsonl \
  --output runs/afmot-kh-wide-005-baseline/truth-vs-predictions.mp4
```

The left panel marks matched ground-truth boxes green and missed boxes red. The
right panel marks matched predictions green and unmatched predictions orange.
This makes synchronization, localization, detection, and association failures
visually separable.

## Build the broadcast golden set

The first CVAT-ready clip is
`data/annotation_candidates/trim6-golden-30s-48s.mp4`. Follow the repository's
[broadcast annotation protocol](../../docs/vision-broadcast-annotation-protocol.md)
to create persistent player, official, and sideline-person tracks without
turning the first exercise into jersey recognition or long-term re-identification.
