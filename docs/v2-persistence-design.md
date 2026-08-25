# V2 persistence design

## Goal

Reloading the extension preserves the league scoring settings and the current
simulation position. Persistence is deliberately local and credential-free;
the browser is not treated as an authoritative source for future league data.

## Contract

The stored value is a JSON object with an explicit `version`:

```text
PersistedSnapshot {
  version: 2
  scoringRules: ScoringRules
  simulator: { eventIndex: non-negative integer }
}
```

The React component owns live state. `storage.ts` owns the boundary between
that state and an external string store. Serialization, validation, and
migration happen at that boundary so the UI never trusts parsed JSON.

Version 1 stored `scoringRules` and a top-level `eventIndex`. Version 2 moves
the cursor under `simulator`, making the simulator-specific boundary explicit.
The migration is pure and only accepts a valid V1 shape. Unknown scoring-rule
fields are ignored during validation because the current rules object is
rebuilt from its known fields.

## Recovery policy

- Missing data uses standard scoring and cursor zero.
- Corrupt JSON, invalid shapes, unsupported versions, and storage read errors
  use safe defaults and are quarantined by removing the unusable value.
- Storage write failures do not crash or stop the simulation; the app remains
  usable in memory.
- A reset writes the safe default snapshot after resetting live state.

Quarantine is intentionally deletion for this local demo. A production
implementation would preserve the rejected payload in a bounded diagnostic
channel, avoid leaking user data, and expose telemetry.

## Deliberate limitations

Only scoring rules and the deterministic cursor are persisted. The current
event text, touchdown notification, running state, and generated timestamps
are transient UI state. Player totals are reconstructed by replaying events
from the cursor, which keeps the snapshot small and avoids persisting a
second source of truth.

```text
React state -> snapshot serializer -> storage boundary -> browser storage
browser storage -> parser/migrator -> validated snapshot -> React state
```

## Failure experiment

The tests inject malformed JSON, missing fields, an unsupported version, and a
throwing storage adapter. Each case returns defaults without throwing. The
migration test demonstrates that a V1 cursor is restored under the V2
simulator shape.

## Learning checkpoint

Storage is a contract because it is an external boundary with its own schema,
failure modes, and compatibility history. `localStorage` only stores strings;
the application still has to decide which fields are authoritative, how to
validate them, and how an older snapshot becomes a current one. Here, the
cursor is authoritative for the deterministic simulator, while player totals
remain derived data.
