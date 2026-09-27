# Vision system learning platform

## Objective

Place a player marker over a broadcast image only when visual evidence maps to
one rostered player with sufficient confidence. Unknown and ambiguous players
must remain unlabeled.

## Pipeline

```text
video frame
  → player detector (person bounding boxes)
  → multi-object tracker (stable track IDs)
  → team classifier (uniform colors)
  → jersey-number detector + OCR
  → roster identity resolver
  → screen-coordinate projection
  → browser marker overlay
```

The fantasy roster narrows the identity search space, but it does not prove an
identity. A marker requires explicit evidence such as team plus jersey number,
and carries confidence and evidence fields for debugging.

## Learning progression

1. Inject synthetic detections into the YouTube marker layer.
2. Run detection and tracking on licensed or self-recorded football clips.
3. Add team-color classification and measure a confusion matrix.
4. Crop jersey regions, run OCR, and save failure examples.
5. Fuse evidence across multiple frames instead of trusting one frame.
6. Calibrate confidence and evaluate false-positive marker rate.
7. Optimize inference and coordinate projection for live latency.

## Evaluation

Track detector precision/recall, identity accuracy, unknown rate, false marker
rate, track fragmentation, end-to-end latency, and confidence calibration.
False confident labels are more harmful than missing labels, so the resolver
abstains when multiple roster candidates remain.

## Broadcast constraint

The overlay is ordinary DOM rendered above YouTube. Access to protected video
pixels is a separate concern: the product must not bypass DRM or platform
protections. Vision experiments should begin with licensed, self-recorded, or
otherwise authorized clips, then use a permitted capture path if one is
available for live testing.
