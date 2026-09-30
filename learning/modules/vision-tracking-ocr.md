# Real-time computer vision, tracking, and identity

## What to learn

- Dataset provenance, game-level splits, annotation agreement, and leakage
- Broadcast shot classification and camera-cut state resets
- Detection precision/recall, small-player slices, and error analysis
- Multi-object tracking, HOTA, AssA, IDF1, switches, and fragmentation
- Field geometry, homography, camera motion, and coordinate transforms
- Team/role evidence and calibrated `unknown` behavior
- Jersey visibility, crop quality, temporal recognition, and abstention
- Evidence fusion, calibration, precision–coverage, and identity revocation
- Bounded asynchronous pipelines, tail latency, frame age, and backpressure
- Replay, shadow mode, drift, model lineage, canaries, and rollback

## Lab and failure exercise

Work through V12–V25 using the same versioned corpus and experiment manifest.
Every version must produce a replayable artifact, metrics by scenario, a failure
injection, and a decision record. Refuse ambiguous identities throughout.

## Checkpoint

When should the product refuse to label a player, discard a frame, reset a
track, fall back to text-only mode, or roll back a model?

## Deepen your understanding

For each milestone, explain the key metric in your own words, predict the likely
failure before running the experiment, compare the prediction with evidence,
and add primary references plus the experiment result to `learning/REFERENCES.md`.

## Core project references

- `docs/vision-roadmap.md`
- `docs/vision-system-design.md`
- `docs/vision-model-candidates.md`
- `docs/vision-decision-rubric.md`
- `docs/vision-metrics-cheat-sheet.md`
