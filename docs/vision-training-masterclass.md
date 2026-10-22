# Real-time vision masterclass

This is a build-first course for the Fantasy HUD. Each lab leaves behind a
working artifact, a measurement, and a clear stop point. It follows the project
gates in `vision-roadmap.md`; exploratory work never substitutes for held-out
evaluation evidence.

## Mental model

Training is not the first step. A production vision system is a timed chain:

`video → decode → scene gate → detect → associate → classify evidence → resolve identity → render`

Every stage has inputs, outputs, failure modes, latency, and confidence. Saving
those intermediate records makes failures reproducible and lets us improve one
stage without rerunning everything upstream.

## Lab progression

| Lab | Build | Core lesson | Exit artifact |
|---|---|---|---|
| 1. Baseline loop | OpenCV + pretrained person detector + BoT-SORT | Frames, boxes, track IDs, media time, wall time | Annotated MP4, JSONL tracks, timing summary |
| 2. Data contract | Dataset manifest and annotation schema | Provenance, label ontology, leakage prevention | Validated manifest and game-level splits |
| 3. Evaluation harness | Detection and tracking evaluators | Precision/recall, mAP, HOTA, AssA, IDF1, latency slices | Frozen baseline report |
| 4. Domain adaptation | Fine-tune on existing football annotations | Transfer learning, augmentations, overfitting | Versioned checkpoint and comparison |
| 5. Hard-example loop | Auto-label target clips and correct failures | Active learning and label quality | Small high-value target-domain set |
| 6. Identity evidence | Team, role, jersey visibility and temporal OCR | Evidence fusion and abstention | Calibrated precision–coverage report |
| 7. Real-time runtime | Bounded queues and newest-frame policy | Throughput is not freshness | Full-game latency/resource soak |
| 8. HUD integration | Replay tracks through the broker and overlay | Synchronization, coordinates, safe fallback | Deterministic end-to-end replay |

## Lab 1 — the baseline loop

### Why start here

A detector answers “where is a person in this frame?” A tracker answers “which
recent person does this detection probably belong to?” Neither answers “is this
the fantasy player?” Keeping those questions separate prevents confident-looking
but logically invalid overlays.

### Guided exercise

1. Run the doctor command and write down the runtime and accelerator.
2. Generate and inspect the smoke video. Explain FPS, frame index, media time,
   resolution, and why the smoke clip is not accuracy evidence.
3. Select a 20–30 second permitted football clip containing a wide shot, camera
   motion, and at least one occlusion.
4. Run the pretrained person/BoT-SORT baseline for at most 900 frames.
5. Read one JSONL record and connect each box and track ID to the annotated frame.
6. Compare source FPS, effective FPS, mean stage time, and p95 stage time.
7. Log three failures: missed person, false positive, and track-ID switch.

### Questions you should be able to answer

- Why can a high-confidence person detection still be the wrong HUD target?
- Why does a tracker need persistent state across frames?
- Why is p95 latency more informative than average latency for a live overlay?
- Why do we preserve both pixel and normalized coordinates?
- Which failures belong to detection, tracking, scene gating, or identity?

### Stop point

Do not train or tune until the artifacts are understandable and the three
failure examples are recorded. The next lab defines what data and labels would
actually resolve those failures.

## Working cadence

Use one focused loop per session: orient for 10 minutes, build for 60–90 minutes,
measure for 20 minutes, then write a five-minute lab note. End with the exact
command that reproduces the result and the first action for the next session.
