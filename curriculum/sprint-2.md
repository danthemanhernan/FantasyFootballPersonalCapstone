# Sprint 2 — Persistent league state

## Outcome

The extension can save its scoring settings and current simulation position, reload them, and safely recover when stored data is invalid.

## Concepts

- Persistence versus in-memory state
- Serialization and deserialization
- Snapshots and cursors
- Storage boundaries and contracts
- Schema versions and migrations
- Corrupt or partial data
- Quarantine and safe defaults

## Starting point

Read:

- `curriculum/versions/V2.md`
- `learning/modules/data-modeling.md`
- `apps/extension/src/scoring.ts`
- `apps/extension/src/App.tsx`

## Exercises

1. Write `docs/v2-persistence-design.md` before writing storage code.
2. Define a versioned snapshot containing scoring settings and simulator cursor.
3. Create a storage interface instead of calling `localStorage` throughout React components.
4. Implement a browser-storage adapter using `localStorage` or `chrome.storage.local`.
5. Save the snapshot when scoring settings or simulator progress changes.
6. Restore a valid snapshot when the app starts.
7. Use safe defaults when no snapshot exists.
8. Handle corrupt JSON and invalid snapshot shapes without crashing the app.
9. Add a migration from snapshot version 1 to the current version.
10. Add tests for save, restore, missing data, corrupt JSON, invalid data, and migration.

## Suggested domain shape

```text
React state → snapshot serializer → storage boundary → browser storage
browser storage → storage boundary → parser/migrator → React state
```

The rest of the application should not need to know whether storage is `localStorage`, Chrome storage, or a future backend.

## Failure injection

- Replace the stored value with invalid JSON.
- Remove a required snapshot field.
- Change the snapshot version to an older version.
- Simulate storage quota failure.
- Store an unknown scoring-rule field.

The application should remain usable and should fall back to safe defaults when restoration is unsafe.

## Definition of done

- Reloading preserves valid settings and simulator position.
- Stored data has an explicit schema version.
- Invalid state is rejected or quarantined safely.
- Storage access is isolated behind an interface.
- Tests cover valid restore, invalid restore, and migration.
- The storage format and deliberate limitations are documented.

## Reflection

Why is storage a contract rather than just a `localStorage.setItem` call? What should happen when the saved state is from an older version of the application?

## Deepen your understanding

Read `learning/modules/data-modeling.md`, explain one concept in your own words, connect it to this lab, and add a dated source to `learning/REFERENCES.md`.
