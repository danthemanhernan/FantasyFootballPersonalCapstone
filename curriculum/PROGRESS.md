# Progress tracker

| Version | Evidence | Status |
|---|---|---|
| V0 | Fake event updates HUD | ✅ |
| V1 | Scoring tests pass | ✅ |
| V2 | Snapshot survives reload | ✅ |
| V3 | Adapter returns canonical roster; classified failures and bounded caller retry tested | ✅ |
| V4 | Replay emits canonical events with deterministic validation and source metadata | ✅ |
| V5 | Duplicate delivery is safe; audit, ordering, retries, and dead letters tested | ✅ |
| V6 | API returns read model; dependency-aware health and container path added | ✅ |
| V7 | Reconnect gets an authorized snapshot and broker-backed projection deltas | ✅ |
| V8 | Accounts, encrypted connections, and per-user league isolation are tested | ✅ |
| V9 | JSON logs, Prometheus, OTLP hooks, CI, migrations, and restore drills exist | ✅ |
| V10 | Probability includes calibration evidence | ☐ |
| V11 | Bottleneck and recovery are measured | ☐ |
| V12 | Vision contracts, safety gates, experiment schemas, and authorized-input policy are frozen | ☐ |
| V13 | A versioned, game-split evaluation corpus can be reproduced | ☐ |
| V14 | Broadcast shots and cuts are classified; stale tracks reset deterministically | ☐ |
| V15 | Player/official detector candidates are evaluated on application slices | ☐ |
| V16 | Online tracking reports HOTA, AssA, IDF1, switches, and fragmentation | ☐ |
| V17 | Field/camera geometry produces measured, stable overlay coordinates | ☐ |
| V18 | Team and role evidence includes calibrated `unknown` behavior | ☐ |
| V19 | Jersey visibility and crop quality are measured before recognition | ☐ |
| V20 | Temporal jersey recognition beats a single-frame baseline | ☐ |
| V21 | Identity fusion meets a predeclared precision–coverage safety gate | ☐ |
| V22 | The full graph meets p95/p99 latency and bounded-queue requirements | ☐ |
| V23 | Recorded vision events replay through the broker into the real HUD | ☐ |
| V24 | A permitted live source runs in shadow mode with reviewed disagreements | ☐ |
| V25 | Drift, model promotion, canary, rollback, and release evidence are exercised | ☐ |

For every milestone record: product change, disproved assumption, injected failure, evidence, and deliberate deferrals. Done means you can explain the trade-offs and reproduce the result—not that every aspirational service is production-ready.
