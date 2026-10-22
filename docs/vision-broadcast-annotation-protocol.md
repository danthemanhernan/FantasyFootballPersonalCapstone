# Broadcast tracking annotation protocol

This protocol creates a small, trustworthy benchmark for the Fantasy Football
HUD. It is intentionally narrower than the eventual product: first measure
player detection, role separation, and short-term tracking in broadcast video.

## First golden clip

Use:

```text
ml/vision_lab/data/annotation_candidates/trim6-golden-30s-48s.mp4
```

The clip is 18 seconds, 1280 x 720, 30 FPS, and 540 frames. It contains a wide
broadcast view, formation/play motion, occlusion, camera motion, and a shot
transition. Keep it as a **development benchmark** for now; do not train on it.

## CVAT task

The quickest route is [CVAT Online](https://app.cvat.ai/). A local installation
is also available through the official
[CVAT Docker guide](https://docs.cvat.ai/docs/administration/basics/installation/),
but it is a separate development service and should not be added to this app's
Docker Compose stack.

Create one video/interpolation task named `broadcast-golden-trim6-v1` and upload
the clip above. Use rectangle tracks with these labels:

| Label | Definition | Box rule |
|---|---|---|
| `player` | Uniformed player participating in the game | Full visible body; estimate through partial occlusion |
| `official` | On-field or sideline game official in officiating uniform | Full visible body |
| `sideline_person` | Coach, staff, camera operator, or other field-level non-player | Label when visually separable; do not label the crowd |

Add these attributes to `player`:

- `team`: `home`, `away`, or `unknown`
- `jersey_visible`: checkbox

Do not add player names or jersey numbers yet. Those are recognition attributes,
not tracking identities, and would turn this first exercise into a much larger
re-identification project.

## Tracking rules

1. Use **Track**, not Shape, mode. CVAT assigns the persistent track ID.
2. Begin a track when the person becomes visible and mark it outside after the
   person leaves the frame.
3. Add a keyframe at motion/direction changes, before and after occlusion, and
   roughly every 5–10 frames during fast camera or player motion.
4. Keep one track through a short occlusion only when the reappearance is
   unambiguous. Otherwise end it and create a new track.
5. End all active tracks at a hard camera cut. A real-time tracker should reset
   or deliberately re-associate across that boundary, so the benchmark should
   not pretend continuity is certain.
6. Label partially visible people when a reasonable full-person box can be
   estimated. Mark the keyframe occluded in CVAT.
7. Ignore spectators in the stands and tiny background people below about 20
   pixels in height. Apply this rule consistently.

CVAT interpolates tracked rectangles between keyframes; review every interpolated
box around collisions, piles, crossings, camera pans, and cut boundaries. See
CVAT's [track-mode guide](https://docs.cvat.ai/docs/annotation/tools/track-mode-advanced/)
for the keyframe workflow.

## Two-pass quality check

Pass 1 establishes all tracks. Pass 2 starts from the end and works backward,
checking:

- no player silently changes track ID after an occlusion;
- officials are never labeled as players;
- sideline people are consistently included or excluded by the 20-pixel rule;
- boxes enclose the same body extent over time;
- no track crosses a hard camera cut;
- every visible on-field player has a label.

Export the finished task as **MOT 1.1** and keep the archive under:

```text
ml/vision_lab/data/annotations/cvat/broadcast-golden-trim6-v1/
```

The data directory is ignored by Git. Store an exported copy somewhere backed
up; the repository should contain only the protocol and future conversion code,
not the recording or annotations.

## What this benchmark answers

- **Detection:** are players found, and are false positives controlled?
- **Classification:** are players, officials, and sideline people separated?
- **Association:** does a player keep one track through crossings and occlusion?
- **Runtime relevance:** does performance hold on the exact broadcast imagery the
  HUD will consume?

It does not yet answer long-term player identity, jersey OCR, ball tracking,
field calibration, or cross-camera re-identification. Add those as separate,
measurable layers after this benchmark is stable.

## Expansion plan

After completing this clip, annotate two more clips rather than more of the same
game:

1. a sealed clip from another game for final evaluation;
2. a hard-example clip rich in piles, sideline overlap, and fast pans for model
   development.

Use AFMOT for domain pretraining and broad experiments. Use these broadcast
clips to measure and close the final domain gap.
