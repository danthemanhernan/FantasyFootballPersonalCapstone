# Real-time broadcast vision crash course

For a detailed side-by-side model, tracker, and deployment-runtime comparison,
see [Vision model and runtime candidates](vision-model-candidates.md).
Use the [real-time vision system decision rubric](vision-decision-rubric.md) to
evaluate candidates consistently and record the evidence behind each choice.
Keep the [vision and tracking metrics cheat sheet](vision-metrics-cheat-sheet.md)
nearby when interpreting HOTA, AssA, IDF1, MOTA, calibration, and latency results.
The [granular vision roadmap](vision-roadmap.md) maps these concepts to V12–V25
implementation milestones and evidence gates.

## The actual problem

The product does not need generic face recognition. It needs to answer a harder,
temporal question: **which visible track, if any, maps to a rostered player, and
where should a marker be drawn now?** A correct system is a graph of uncertain
signals. It abstains when the evidence is weak.

```text
authorized frame source
  -> shot/field gate
  -> player + official detector
  -> multi-object tracks
  -> team / role classifier
  -> jersey region + number recognizer
  -> field calibration and location
  -> roster + lineup + play context resolver
  -> calibrated identity belief over time
  -> latency-compensated screen marker
```

The browser overlay can remain ordinary DOM. Video pixels must come from an
authorized capture path; do not bypass DRM or platform protections. Train and
test first on licensed, self-recorded, or research-permitted clips.

## Current model map (September 2026)

Treat release-page speed claims as candidates, then benchmark on your exact
resolution, hardware, runtime, and camera distribution.

| Job | Strong current candidates | Why / caveat |
|---|---|---|
| Edge detector | YOLO26, RT-DETRv3, D-FINE | YOLO26 offers end-to-end/NMS-free deployment plus detection, pose, segmentation, depth, and open-vocabulary variants. Check AGPL versus enterprise licensing. RT-DETR descendants and D-FINE are strong transformer baselines with simpler end-to-end post-processing. |
| Prompted discovery | Grounding DINO 1.5 / open-vocabulary YOLOE-26 | Excellent for bootstrapping labels and finding new visual concepts; usually distill or replace with a closed-set edge model for the hot path. |
| Video masks | SAM 2 | Promptable video segmentation with memory. Powerful annotation/occlusion tool, but often too expensive to run over every object on every live frame. |
| Dense point tracks | CoTracker3 | Tracks visible and occluded points jointly; useful for research, camera motion, and difficult occlusion analysis. It is not itself player identity. |
| Online box tracking | ByteTrack, BoT-SORT, OC-SORT-style baselines | Mature low-latency choices. Start with one and measure ID switches; do not assume a larger detector fixes association. |
| Jersey recognition | dedicated jersey detector + sequence recognizer; SoccerNet baselines/datasets | Tiny, blurred, folded digits need a domain-specific cropper and temporal voting. Generic OCR alone is a baseline, not the destination. |
| Runtime | TensorRT/ONNX Runtime; NVIDIA DeepStream for NVIDIA pipelines | FP16/INT8, batching, zero-copy decode, and asynchronous stages usually matter more than another point of offline accuracy. DeepStream supplies production video plumbing but adds platform coupling. |

References:

- [YOLO26 documentation](https://docs.ultralytics.com/models/yolo26) and [paper](https://arxiv.org/abs/2606.03748)
- [D-FINE](https://github.com/Peterande/D-FINE), [RT-DETRv3](https://github.com/clxia12/RT-DETRv3), and the [RT-DETR research family](https://github.com/RT-DETRs)
- [SAM 2](https://github.com/facebookresearch/sam2) and [CoTracker3](https://github.com/facebookresearch/co-tracker)
- [Grounding DINO 1.5](https://github.com/IDEA-Research/Grounding-DINO-1.5-API)
- [SoccerNet jersey recognition](https://github.com/SoccerNet/sn-jersey), [2025 uncertainty-aware JNR](https://openaccess.thecvf.com/content/CVPR2025W/CVSPORTS/papers/Grad_Single-Stage_Uncertainty-Aware_Jersey_Number_Recognition_in_Soccer_CVPRW_2025_paper.pdf), and a [general JNR framework](https://arxiv.org/abs/2405.13896)
- [NVIDIA DeepStream 8 overview](https://docs.nvidia.com/metropolis/deepstream/8.0/text/DS_Overview.html)
- [SoccerTrack v2](https://arxiv.org/abs/2508.01802) for modern sports-tracking evaluation ideas

## The newest useful trends

1. **End-to-end, NMS-free detectors.** Deployment is simpler and latency is more predictable, but validate crowded-player recall and duplicate behavior.
2. **Foundation models as teachers and annotators.** Grounded detection and promptable video segmentation can label data and expose edge cases. Small, specialized models still win the live budget.
3. **Temporal evidence, not frame OCR.** Pool number logits, team class, track appearance, and field location over a track. One clean back-facing frame can resolve ten poor frames.
4. **Uncertainty-aware recognition and abstention.** Output a distribution over digits/identities, calibrate it, and display nothing below threshold.
5. **Joint geometry and tracking.** Estimate field homography and camera motion; impossible movement and wrong-side alignment become useful rejection rules.
6. **Hardware-aware design.** Decode, resize, memory copies, serialization, and overlay synchronization are first-class model components.
7. **Replayable evaluation.** Preserve timestamps and intermediate artifacts so a model/runtime change can be compared against the same broadcast segments.

## How to design it

### 1. Write the latency and error contract first

For a learning prototype, target capture-to-marker p95 below 500 ms. Break the
budget into capture/decode, inference, association, identity, transport, and
rendering. Define a much tighter false-label budget than miss budget: a hidden
marker is usually better than confidently labeling the wrong player.

### 2. Build an evaluation corpus before optimizing

Use multiple games, camera types, replay graphics, lighting, uniforms, motion
blur, occlusions, and resolutions. Split by game—not random frame—so near-
duplicate frames cannot leak into validation. Annotate boxes, stable track IDs,
team/role, visible jersey digits, identity when genuinely knowable, and
`unknown` otherwise.

### 3. Establish independent baselines

- Detector: precision/recall and mAP by player size and shot type.
- Tracker: HOTA/IDF1, ID switches, fragmentation, reacquisition time.
- Jersey recognizer: exact number accuracy, character error, coverage.
- Identity resolver: top-1 accuracy, false-label rate, abstention/coverage.
- System: p50/p95 latency, dropped frames, marker jitter, stale-marker time.

### 4. Fuse evidence explicitly

For track `t` and candidate player `p`, start with an explainable score or
Bayesian log-odds model:

```text
belief(p | t) <- jersey likelihood
               + team compatibility
               + active roster prior
               + field/formation compatibility
               + play-by-play participation evidence
               + temporal continuity
```

Never make roster membership proof of identity. Require a margin between the
top two candidates, calibrate probabilities on held-out games, and decay belief
after occlusion or a broadcast cut.

### 5. Engineer the real-time graph

Use bounded queues and timestamps. Drop stale frames instead of building delay.
Detect at a lower cadence, track between detections, and run expensive jersey
recognition only on promising high-resolution crops. Keep every coordinate
transform explicit: source frame -> model letterbox -> decoded frame -> CSS
video rectangle. Smooth marker positions, but reset on shot changes.

### 6. Make failures observable

For every emitted identity, record model versions, track ID, candidate scores,
evidence, capture timestamp, inference timestamps, and final coordinates. Save
privacy-safe hard examples by policy. A debug replay should reproduce the exact
decision without calling live services.

## Practical implementation ladder

1. Keep the existing synthetic markers and add timestamped replay fixtures.
2. Detect players in authorized clips; draw boxes and benchmark end-to-end FPS.
3. Add an online tracker and shot-change reset; measure ID switches.
4. Classify teams/officials and fit field homography from lines/keypoints.
5. Train a jersey cropper and number recognizer; aggregate logits per track.
6. Join only to the active roster and lineup; implement calibrated abstention.
7. Replay complete games and create a failure taxonomy/dashboard.
8. Export to ONNX/TensorRT, test FP16 then INT8 with calibration data.
9. Integrate a permitted live capture path and measure glass-to-glass latency.
10. Shadow-run during games before showing labels; compare predictions to manually reviewed truth and live play-by-play.

The first worthwhile experiment is **detector + tracker + synthetic roster
identity**, not end-to-end player recognition. It teaches the system boundaries,
latency, coordinates, and evaluation without hiding mistakes inside a giant
model.

## Curriculum crosswalk

| Versions | System outcome |
|---|---|
| V12–V13 | Reproducible contracts and an authorized, versioned evaluation corpus |
| V14–V17 | Scene-aware player detection, tracking, and stable geometry |
| V18–V21 | Team, jersey, and calibrated canonical identity evidence |
| V22–V23 | Bounded real-time execution and authenticated HUD replay |
| V24–V25 | Permitted live shadow validation and controlled model operations |
