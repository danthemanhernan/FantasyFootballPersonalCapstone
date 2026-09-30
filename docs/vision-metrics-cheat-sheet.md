# Vision and tracking metrics cheat sheet

This cheat sheet explains the detection, tracking, identity, calibration, and
runtime metrics used by the Fantasy Football HUD. It focuses on what each metric
means operationally rather than only its mathematical definition.

## Start with the pipeline

Different metrics evaluate different stages:

```text
frame
  -> detector       precision, recall, AP, IoU
  -> tracker        HOTA, AssA, IDF1, MOTA, ID switches
  -> jersey reader  exact accuracy, CER, visible-number recall
  -> identity       identity precision, coverage, calibration
  -> overlay        anchor error, jitter, stale-marker time
  -> full system    p50/p95/p99 latency, frame age, dropped frames
```

No single metric describes the complete system.

## The tracking acronyms that matter most

| Acronym | Full name | Plain-language meaning | Direction | Important limitation |
|---|---|---|---|---|
| **HOTA** | Higher Order Tracking Accuracy | A balanced summary of whether objects were detected and whether their identities stayed associated correctly over time. | Higher is better | A summary can hide whether the weakness is detection or association; always inspect DetA and AssA too. |
| **DetA** | Detection Accuracy | Whether the tracker found the correct objects without too many misses or false detections. | Higher is better | Does not describe whether identities remained consistent. |
| **AssA** | Association Accuracy | Whether matched detections were connected to the correct track across time. | Higher is better | Can look good even if many players were never detected; read it with DetA. |
| **LocA** | Localization Accuracy | How closely matched predicted boxes overlap their ground-truth boxes. | Higher is better | Measures box placement only for matched objects. |
| **IDF1** | Identity F1 Score | The harmonic mean of identity precision and identity recall over all detections. It rewards keeping the correct identity attached over time. | Higher is better | Does not expose when or why switches occurred. Also depends on detection quality. |
| **IDP** | Identity Precision | Of detections assigned to identities, how many identity assignments were correct? | Higher is better | Can be made high by assigning identities rarely. Read with IDR. |
| **IDR** | Identity Recall | Of all identity-labeled ground-truth detections, how many were recovered with the correct identity? | Higher is better | Can improve by labeling more aggressively, possibly reducing precision. |
| **MOTA** | Multiple Object Tracking Accuracy | A legacy summary based on false negatives, false positives, and identity switches relative to the number of ground-truth objects. | Higher is better | Often dominated by detector performance and can underrepresent association quality. It can also be negative. |
| **MOTP** | Multiple Object Tracking Precision | Average localization overlap or distance for matched predictions. Despite its name, it is not classification precision. | Higher is generally better when expressed as overlap | Different implementations may report distance or overlap, so confirm the convention. |
| **IDSW** | Identity Switches | Number of times a tracked identity changes from one real person to another. | Lower is better | Raw counts are unfair across videos of different lengths; also report switches per player-minute or game. |
| **Frag** | Fragmentations | Number of times a ground-truth trajectory is interrupted and later resumed as a track. | Lower is better | A fragmented track does not always become the wrong player, but it resets accumulated evidence. |
| **MT** | Mostly Tracked | Ground-truth trajectories successfully tracked for most of their lifespan, commonly at least 80%. | Higher is better | Threshold-based and does not prove identity consistency. |
| **ML** | Mostly Lost | Ground-truth trajectories tracked for only a small part of their lifespan, commonly less than 20%. | Lower is better | Does not explain whether loss came from detection, cuts, or occlusion. |

Use the capitalization **AssA**, not `ASSA`. It is a component of the HOTA
metric family.

## How HOTA is organized

Conceptually, HOTA balances two questions:

```text
DetA: Did the system find the correct players?
AssA: Did it connect each player's detections correctly over time?
```

At a given matching threshold, HOTA is based on the geometric balance between
detection and association accuracy:

```text
HOTA approximately balances sqrt(DetA * AssA)
```

The final result is averaged across localization thresholds. This means a
tracker should not score extremely well by excelling at detection while failing
association, or vice versa.

Example:

| Candidate | DetA | AssA | Interpretation |
|---|---:|---:|---|
| A | 85 | 45 | Finds most players but frequently mixes or breaks identities. |
| B | 70 | 75 | Misses more players, but its tracks are substantially more consistent. |
| C | 82 | 80 | Strong detection and association; likely the better tracking foundation. |

For this HUD, **AssA and ID switches are especially important** because one
wrong association can move a fantasy-player label onto an opponent.

## Why MOTA can be misleading

MOTA is approximately:

```text
MOTA = 1 - (false negatives + false positives + identity switches)
           / number of ground-truth detections
```

Suppose a tracker has:

```text
1,000 ground-truth player detections
100 misses
30 false detections
10 identity switches
```

Then:

```text
MOTA = 1 - (100 + 30 + 10) / 1,000
     = 0.86
```

Because misses and false detections can greatly outnumber identity switches,
MOTA often behaves more like a detector score than a player-identity continuity
score. Use it as supporting evidence, not as the primary tracker-selection
metric.

## Detection metrics

| Acronym | Full name | Plain-language meaning | Direction |
|---|---|---|---|
| **TP** | True Positive | A predicted player correctly matches a real player. | More is generally better |
| **FP** | False Positive | The model reports a player where there is not one. | Lower is better |
| **FN** | False Negative | A real player was missed. | Lower is better |
| **TN** | True Negative | Correctly recognizing the absence of an object. | Rarely enumerated in object detection because possible background boxes are effectively unlimited. |
| **IoU** | Intersection over Union | Predicted-box overlap with the ground-truth box: intersection area divided by union area. | Higher is better |
| **P** | Precision | `TP / (TP + FP)`: of reported players, how many were real? | Higher is better |
| **R** | Recall | `TP / (TP + FN)`: of real players, how many were found? | Higher is better |
| **F1** | F1 Score | Harmonic mean of precision and recall at one operating threshold. | Higher is better |
| **AP** | Average Precision | Area under the precision–recall curve for a class, usually under a defined IoU rule. | Higher is better |
| **mAP** | Mean Average Precision | AP averaged across classes, IoU thresholds, or both, depending on the benchmark. | Higher is better |
| **AP50** | Average Precision at IoU 0.50 | Detection AP using a forgiving 50% overlap requirement. | Higher is better |
| **AP75** | Average Precision at IoU 0.75 | Detection AP with stricter localization. | Higher is better |
| **AP50–95** | COCO-style AP | AP averaged over IoU thresholds from 0.50 to 0.95 in increments of 0.05. | Higher is better |
| **AP-S/M/L** | AP for Small, Medium, or Large objects | Performance broken down by object size. | Higher is better |
| **AR** | Average Recall | Recall averaged over benchmark settings such as IoU thresholds and detection limits. | Higher is better |
| **NMS** | Non-Maximum Suppression | Post-processing that removes duplicate overlapping detections. It is an algorithm, not an accuracy metric. | Not applicable |

### Precision versus recall example

If the detector reports 100 players, 90 are correct, and it missed 30 real
players:

```text
precision = 90 / 100 = 90%
recall    = 90 / 120 = 75%
```

The detector is usually correct when it reports a player, but it misses one in
four real players.

For the HUD, report these application-specific versions too:

- Small-player recall in wide shots
- Crowded-player recall at the line of scrimmage
- False player detections per video minute
- Player-versus-official confusion rate
- Missed roster-player seconds

## Jersey and identity metrics

| Acronym or term | Full name | Plain-language meaning | Direction |
|---|---|---|---|
| **EM** | Exact Match | The entire predicted jersey number equals the ground truth. `8` instead of `88` is wrong. | Higher is better |
| **CER** | Character Error Rate | Digit insertions, deletions, and substitutions divided by ground-truth digit count. | Lower is better |
| **Top-1** | Top-1 Accuracy | The highest-scoring identity candidate is correct. | Higher is better |
| **Top-k** | Top-k Accuracy | The correct identity appears among the highest `k` candidates. | Higher is better, but it is not sufficient for display decisions. |
| **Coverage** | Display or identity coverage | Percentage of eligible visible-player time for which the system displays an identity. | Higher is useful only while precision remains safe. |
| **Abstention rate** | Unknown rate | Percentage of opportunities where the system intentionally refuses to identify a player. | Neither inherently good nor bad |
| **Time to identify** | Identification delay | Time from a track becoming visible until a safe identity is established. | Lower is better |

The key product curve is **identity precision versus coverage**:

```text
high threshold -> higher precision, lower coverage
low threshold  -> lower precision, higher coverage
```

Choose a threshold that satisfies the false-label budget first, then maximize
coverage without violating it.

## Confidence and calibration metrics

| Acronym | Full name | Plain-language meaning | Direction |
|---|---|---|---|
| **ECE** | Expected Calibration Error | Average mismatch between predicted confidence and observed correctness across confidence bins. | Lower is better |
| **D-ECE** | Detection Expected Calibration Error | ECE adapted to object detection, potentially accounting for class and localization behavior. | Lower is better |
| **NLL** | Negative Log-Likelihood | Strongly penalizes confident incorrect probability predictions. | Lower is better |
| **BS** | Brier Score | Mean squared difference between predicted probabilities and actual outcomes. | Lower is better |

A calibrated system behaves like this:

```text
Among decisions reported at approximately 80% confidence,
approximately 80% should be correct.
```

Accuracy and calibration are different. A highly accurate system may still be
overconfident when wrong.

## Segmentation metrics

| Acronym | Full name | Plain-language meaning | Direction |
|---|---|---|---|
| **mIoU** | Mean Intersection over Union | Average mask overlap across classes. | Higher is better |
| **J** | Jaccard Index | Mask IoU: intersection divided by union. | Higher is better |
| **F** | Contour F-measure | Accuracy of the predicted mask boundary. | Higher is better |
| **J&F** | Combined region and contour score | Average of region overlap and boundary quality, commonly used for video segmentation. | Higher is better |

For player markers based on boxes rather than masks, segmentation metrics are
secondary. They become important if masks are used for occlusion, body-region
cropping, or precise overlay placement.

## Runtime and deployment acronyms

| Acronym | Full name | Plain-language meaning | Direction |
|---|---|---|---|
| **FPS** | Frames Per Second | Number of frames processed each second. | Higher is generally better, but does not prove low latency. |
| **p50** | 50th Percentile | Median latency: half of results are faster and half slower. | Lower is better |
| **p95** | 95th Percentile | 95% of results complete at or below this latency. | Lower is better |
| **p99** | 99th Percentile | Tail latency experienced by the slowest 1% of results. | Lower is better |
| **E2E** | End to End | Total latency from frame capture to rendered overlay. | Lower is better |
| **VRAM** | Video Random Access Memory | GPU memory consumed by models, tensors, video frames, and runtime engines. | Must fit with headroom |
| **RAM** | Random Access Memory | System memory consumption. | Must fit with headroom |
| **FLOPs** | Floating-Point Operations | Approximate amount of model computation. Often reported per inference. | Lower can be faster, but hardware and operators matter. |
| **Params** | Parameters | Number of learned model weights. | Lower generally reduces storage, but does not guarantee lower latency. |
| **FP32** | 32-bit Floating Point | Standard high-precision inference representation. | Baseline accuracy, higher compute/memory |
| **FP16** | 16-bit Floating Point | Reduced precision commonly used to accelerate GPU inference. | Usually faster with modest accuracy risk |
| **BF16** | Brain Floating Point 16 | Reduced precision with FP32-like numeric range. | Hardware-dependent |
| **INT8** | 8-bit Integer | Quantized inference representation for speed and memory savings. | Faster/smaller, but requires calibration and accuracy checks |

### Why FPS is not enough

A pipeline can process 30 FPS while displaying frames that are several seconds
old if work accumulates in a queue. Always measure:

```text
capture-to-overlay p50, p95, and p99
frame age at render
queue waiting time
dropped-frame rate
```

## Overlay metrics

| Term | Meaning | Direction |
|---|---|---|
| **Anchor error** | Pixel distance between the desired player anchor and the rendered marker. | Lower is better |
| **Normalized anchor error** | Anchor error divided by player-box height, allowing fair comparisons across shot scales. | Lower is better |
| **Jitter** | Unwanted frame-to-frame marker movement after accounting for real player motion. | Lower is better |
| **Stale-marker time** | How long a marker remains after its track disappears or a broadcast cut occurs. | Lower is better |
| **Cut-reset latency** | Time required to discard the old scene's tracks after a camera cut. | Lower is better |

## Metric relationships at a glance

| If this is poor... | Likely symptom | Inspect next |
|---|---|---|
| Precision | Labels appear on fans, coaches, graphics, or officials. | False positives by shot type and class confusion. |
| Recall or DetA | Players disappear or tracks never start. | Small-player and crowded-scene recall. |
| AssA or IDF1 | Markers jump between players despite good boxes. | ID switches, ReID features, camera-motion compensation. |
| HOTA | Overall tracking is weak. | Compare DetA against AssA to locate the weakness. |
| MOTA | Many misses or false detections, possibly some switches. | FP, FN, and IDSW separately; do not diagnose from MOTA alone. |
| Exact jersey accuracy | Wrong or incomplete jersey numbers. | Visibility classifier, crop quality, temporal voting, CER. |
| Calibration | Confidence thresholds do not produce predictable correctness. | Reliability diagrams, ECE, NLL, post-hoc calibration. |
| p95/p99 latency | HUD occasionally feels far behind despite good average speed. | Queue time, decode stalls, warm-up, GPU contention. |
| Jitter | Correct player marker shakes or swims around. | Track smoothing, coordinate transforms, camera motion. |

## Recommended dashboard

For each complete-game evaluation, record at least:

```text
Detection:
  precision, recall, AP50-95, small-player recall, false positives/minute

Tracking:
  HOTA, DetA, AssA, IDF1, IDSW/player-minute, fragmentation

Identity:
  displayed identity precision, coverage, false labels/game,
  exact jersey accuracy, time to identify, ECE

System:
  E2E p50/p95/p99, frame age, dropped frames, peak VRAM/RAM

Overlay:
  normalized anchor error, jitter, stale-marker time, cut-reset latency
```

## What to optimize for this application

Use metrics in this priority order:

1. Displayed identity precision and false labels per game
2. End-to-end p95/p99 latency and bounded frame age
3. AssA, IDF1, and identity switches
4. Identity coverage and time to identify
5. Small-player and crowded-scene recall
6. Marker stability and stale-marker behavior
7. Resource use, maintainability, cost, and licensing
8. General benchmark scores such as COCO AP

The guiding rule is:

> First make displayed identities safe, then make them timely, then increase how
> often they can be displayed.

## References

- [HOTA paper](https://arxiv.org/abs/2009.07736)
- [TrackEval: official HOTA, CLEAR MOT, and identity-metric implementation](https://github.com/JonathonLuiten/TrackEval)
- [COCO evaluation format](https://cocodataset.org/#detection-eval)
- [Confidence calibration for object detection and segmentation](https://arxiv.org/abs/2202.12785)
- [Object detector calibration pitfalls and baselines](https://arxiv.org/abs/2405.20459)
