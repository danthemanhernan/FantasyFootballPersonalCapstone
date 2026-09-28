# System overview

```mermaid
flowchart TB
  V0["V0 simulator"] --> V1["V1 scoring"] --> V3["V3 provider"] --> V4["V4 events"] --> V5["V5 idempotency"]
  V5 --> V6["V6 read model"] --> V7["V7 push"] --> V8["V8 tenancy"] --> V9["V9 operations"]
  V9 --> V10["V10 probability"] --> V11["V11 resilience"]
  V9 --> V12["V12 vision contract"] --> V13["V13 corpus"] --> V14["V14 scene gate"] --> V15["V15 detection"]
  V15 --> V16["V16 tracking"] --> V17["V17 geometry"] --> V18["V18 team/role"] --> V19["V19 jersey evidence"]
  V19 --> V20["V20 jersey recognition"] --> V21["V21 identity"] --> V22["V22 runtime"] --> V23["V23 HUD integration"]
  V23 --> V24["V24 live shadow"] --> V25["V25 vision operations"]
```

```mermaid
flowchart LR
  RAW["External DTO"] --> ADAPTER["Adapter"] --> EVENT["Canonical event"] --> PROJECTION["Projection"] --> API["Read API"] --> HUD["HUD"]
  EVENT --> AUDIT["Replay / audit"]
```

These are teaching boundaries, not claims that every box exists today.
