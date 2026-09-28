# Real-time vision system decision rubric

Use this rubric whenever selecting or replacing a detector, tracker, identity
model, runtime, or complete vision pipeline for the Fantasy Football HUD.

Metric definitions and acronym explanations are available in the
[vision and tracking metrics cheat sheet](vision-metrics-cheat-sheet.md).

The objective is not to choose the model with the best headline benchmark. The
objective is to produce trustworthy, stable, timely player overlays on
authorized NFL footage while preserving an explainable path from visual
evidence to identity.

## Product priorities

In descending order:

1. Do not confidently label the wrong player.
2. Remain timely enough to follow live action.
3. Maintain tracks through normal motion, camera movement, and occlusion.
4. Identify useful players often enough to improve the viewing experience.
5. Make failures observable, reproducible, and explainable.
6. Fit the available hardware, operational budget, and licensing constraints.

## Hard gates

A candidate that fails any hard gate is not eligible, regardless of its total
score. Initial targets should be refined using complete-game experiments.

| Gate | Initial requirement | Why it is mandatory |
|---|---:|---|
| Displayed identity precision | At least 99% on held-out games | A false label damages trust more than an omitted marker. |
| False confident identities | No more than one per full game | Converts an abstract percentage into a visible product failure budget. |
| End-to-end latency | p95 at or below 500 ms; p99 below 1 second | The marker must describe the action currently on screen. |
| Queue behavior | Bounded queues with no increasing frame age | High throughput is meaningless if the system falls progressively behind. |
| Broadcast cuts | Old tracks and markers cleared within 250 ms of a detected cut | Prevents labels from surviving into replays, commercials, or new camera views. |
| Resource fit | Fits target VRAM/RAM with at least 20% headroom | Prevents instability when all stages run together. |
| Reproducibility | Model, configuration, dataset version, and run results recorded | A result that cannot be reproduced cannot guide architecture. |
| Legal and licensing | Footage, model, weights, and runtime are permitted for intended use | Technical success does not override rights or license obligations. |
| Safe uncertainty | The system can emit `unknown` and suppress a marker | Forced classification is unacceptable when evidence is ambiguous. |

## Scoring scale

Score every category from 0 to 4. Do not use decimals until the underlying
measurements are recorded.

| Score | Meaning |
|---:|---|
| 0 | Missing, unusable, unmeasured, or fails badly. |
| 1 | Works only in favorable demos; serious failures remain. |
| 2 | Meets a minimal prototype standard with known limitations. |
| 3 | Meets the target across representative held-out games. |
| 4 | Exceeds the target consistently, including difficult scenarios. |

Calculate each weighted contribution as:

```text
weighted contribution = (score / 4) * category weight
```

The maximum total is 100.

## Weighted rubric

### 1. Identity safety and uncertainty — 25 points

| Criterion | Evidence to collect |
|---|---|
| Displayed identity precision | Correct displayed identities divided by all displayed identities. |
| False labels per game | Count confidently incorrect identities in complete-game replays. |
| Precision–coverage curve | Identity precision at increasing display thresholds, with corresponding coverage. |
| Calibration | Reliability diagram, ECE or D-ECE, Brier score, and negative log-likelihood. |
| Abstention behavior | Accuracy of `unknown` decisions and behavior when the top candidates are close. |
| Evidence trace | Jersey, team, roster, field position, track history, and play context recorded for each decision. |

Scoring guidance:

- **0:** Cannot represent uncertainty or frequently assigns the wrong identity.
- **1:** Confidence exists but is uncalibrated; false labels are common.
- **2:** Supports abstention and meets precision only on easy shots.
- **3:** Meets the 99% precision gate across representative held-out games.
- **4:** Maintains the gate on difficult slices with calibrated confidence and a clear evidence trace.

### 2. Tracking and temporal continuity — 20 points

| Criterion | Evidence to collect |
|---|---|
| HOTA and AssA | Overall tracking quality and association accuracy. |
| IDF1 | Long-term identity consistency. |
| ID switches | Switches per player-minute and per full game. |
| Fragmentation | Number of times one player becomes multiple tracks. |
| Occlusion recovery | Reacquisition time and correct-player recovery rate. |
| Camera-motion robustness | Results during pans, zooms, shakes, and angle changes. |

Scoring guidance:

- **0:** Tracks are not stable enough to aggregate identity evidence.
- **1:** Works in static or sparse scenes but fails during normal plays.
- **2:** Adequate baseline with measurable fragmentation and ID switches.
- **3:** Stable through ordinary motion, short occlusions, and camera pans.
- **4:** Rare wrong-player handoffs and reliable recovery across difficult game situations.

### 3. Detection quality — 15 points

| Criterion | Evidence to collect |
|---|---|
| Player precision and recall | Measured at the intended production threshold. |
| Small-player recall | Wide-shot performance, reported separately from aggregate recall. |
| Crowded-scene recall | Line-of-scrimmage and pile-up performance. |
| False positives per minute | Include coaches, fans, officials, graphics, and sideline personnel. |
| Localization quality | AP50–95 plus application-specific head/torso anchor accuracy. |
| Class confusion | Player versus official, sideline personnel, and non-person graphics. |

Scoring guidance:

- **0:** Misses or invents enough players that tracking cannot operate.
- **1:** Works mainly on close-ups and clean shots.
- **2:** Reasonable aggregate performance but weak small-player or crowded-scene recall.
- **3:** Meets targets across wide, medium, close-up, and crowded shots.
- **4:** Strong performance across difficult slices without an unacceptable false-positive rate.

### 4. Jersey and player evidence — 10 points

| Criterion | Evidence to collect |
|---|---|
| Exact number accuracy | Full one- or two-digit number must be correct. |
| Visible-number recall | Recognition rate only when a number is genuinely readable. |
| Tracklet aggregation gain | Difference between single-frame and temporal recognition. |
| Team classification | Accuracy by uniform combination and lighting condition. |
| Ambiguity handling | Similar numbers, folded jerseys, partial digits, and front/back/shoulder views. |

Scoring guidance:

- **0:** Generic OCR output is accepted without temporal or visibility logic.
- **1:** Reads clear close-ups only and frequently guesses from partial evidence.
- **2:** Uses temporal voting but remains unreliable on common broadcast views.
- **3:** Produces useful calibrated number evidence and abstains when unreadable.
- **4:** Reliable across uniform combinations and substantially improves identity coverage without reducing precision.

### 5. Real-time performance — 15 points

| Criterion | Evidence to collect |
|---|---|
| End-to-end latency | Capture-to-overlay p50, p95, and p99. |
| Stage latency | Decode, preprocess, detect, track, recognize, resolve, transport, and render. |
| Frame age | Age of each result when rendered. |
| Throughput | Sustained processed frames per second, not an isolated model benchmark. |
| Dropped frames | Rate and reason for intentional and accidental drops. |
| Tail stalls | Longest observed pause during a full-game run. |

Scoring guidance:

- **0:** Cannot process representative footage near real time.
- **1:** Average speed looks acceptable but queues or tail latency grow.
- **2:** Prototype remains live with occasional visible delay.
- **3:** Meets all latency gates through a complete game without backlog.
- **4:** Maintains substantial latency headroom while recording all required telemetry.

### 6. Overlay and geometric stability — 5 points

| Criterion | Evidence to collect |
|---|---|
| Normalized anchor error | Pixel anchor error divided by player-box height. |
| Marker jitter | Frame-to-frame error after accounting for actual player motion. |
| Coordinate correctness | Results through scaling, letterboxing, fullscreen, and browser resizing. |
| Stale-marker duration | Time a marker remains after track loss or a cut. |
| Occlusion behavior | Whether markers hide, fade, or remain stable appropriately. |

### 7. Robustness and generalization — 5 points

Evaluate each candidate separately on:

- Wide, medium, and close-up shots
- Live plays, replays, sidelines, commercials, and studio segments
- Line of scrimmage, open field, and pile-ups
- Partial and full occlusion
- Fast pans, zooms, and motion blur
- 1080p, 720p, reduced bitrate, and compression artifacts
- Day, night, indoor, rain, and snow
- Home, away, alternate, and visually similar uniforms
- Scoreboards and other broadcast graphics

Score based on the worst meaningful scenario, not only the overall average.

### 8. Engineering and operational fit — 5 points

| Criterion | Evidence to collect |
|---|---|
| Hardware use | Peak and sustained VRAM, RAM, CPU, GPU, and power. |
| Portability | PyTorch, ONNX, TensorRT, operating-system, and hardware support. |
| Operability | Startup time, warm-up, health checks, logs, metrics, traces, and failure recovery. |
| Maintainability | Testability, community health, documentation, model-version discipline, and debugging tools. |
| Cost and license | Training/inference cost, API dependence, data rights, and commercial-license implications. |

## Evaluation dataset rules

The rubric is valid only if the evaluation data is representative.

1. Split by **game**, not random frames. Adjacent frames are nearly duplicates.
2. Keep a final test set untouched until design choices are frozen.
3. Include entire drives and games so temporal and queue behavior are measured.
4. Label `unknown`, invisible jersey numbers, occlusion, shot type, and camera cuts.
5. Preserve timestamps so capture-to-overlay latency can be reproduced.
6. Report overall results and scenario slices.
7. Version footage, annotations, preprocessing, model weights, and configuration.
8. Use only footage that is licensed, self-recorded, or otherwise authorized.

## Decision process

Follow this order for every comparison:

1. State the decision: for example, “ByteTrack versus BoT-SORT for online player tracking.”
2. Freeze the dataset, hardware, input resolution, and latency budget.
3. Define hard gates before running the experiment.
4. Tune each candidate on the validation set, not the test set.
5. Run complete-game replay at least three times to expose timing variance.
6. Reject candidates that fail a hard gate.
7. Score remaining candidates using the weighted rubric.
8. Inspect scenario slices and the highest-severity failures.
9. Prefer the simpler candidate when scores are effectively tied.
10. Record the decision, evidence, limitations, and conditions that should trigger reconsideration.

## Candidate scorecard template

| Category | Weight | Score 0–4 | Weighted points | Evidence/run link | Important failure |
|---|---:|---:|---:|---|---|
| Identity safety and uncertainty | 25 |  |  |  |  |
| Tracking and temporal continuity | 20 |  |  |  |  |
| Detection quality | 15 |  |  |  |  |
| Jersey and player evidence | 10 |  |  |  |  |
| Real-time performance | 15 |  |  |  |  |
| Overlay and geometric stability | 5 |  |  |  |  |
| Robustness and generalization | 5 |  |  |  |  |
| Engineering and operational fit | 5 |  |  |  |  |
| **Total** | **100** |  |  |  |  |

Hard-gate result: `PASS / FAIL`

## Decision record template

```markdown
# Vision decision: <decision name>

Date:
Owner:
Candidates:
Git commit:
Dataset version:
Hardware/runtime:

## Intended use

What pipeline stage and operating conditions does this decision cover?

## Hard gates

| Gate | Target | Candidate A | Candidate B |
|---|---:|---:|---:|

## Weighted results

Paste the completed scorecard.

## Scenario failures

List wide-shot, occlusion, camera-motion, jersey, latency, and overlay failures.

## Decision

Chosen candidate and the evidence that justifies it.

## Known limitations

What remains unsafe, unsupported, or unmeasured?

## Reconsider when

Examples: new hardware, new model release, different capture path, latency
regression, new uniform distribution, or identity precision below its gate.
```

## Focus rule

Change one major pipeline component at a time. If the detector, tracker, OCR
model, thresholds, and runtime all change together, the result cannot explain
which change helped. Preserve a simple baseline and require every added
component to demonstrate a measurable product-level improvement.
