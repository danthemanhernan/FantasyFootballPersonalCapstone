# V3 learning lab: provider boundaries in practice

This note is a guided walkthrough of the V3 implementation. Read it with the
code open, then run the tests and deliberately break one assumption at a time.

## Learning goals

By the end, you should be able to:

1. Explain why external JSON must be treated as `unknown` at the boundary.
2. Separate transport errors, HTTP status errors, and contract errors.
3. Map provider DTOs into a canonical model without leaking provider details.
4. Place retries at the layer that owns the policy and test them without real delays.
5. State what this adapter does not prove about production integration.

## Deep dive 1: ports and anti-corruption boundaries

`ProviderPort` is a small port: `loadRoster(LeagueRef) -> CanonicalRoster`.
It says what the application needs, not how ESPN happens to provide it. The
ESPN adapter is an anti-corruption layer: it translates `fullName`, numeric
position IDs, and ESPN identifiers into the canonical `name`, `position`, and
`source` fields.

Why this matters:

- The HUD can render a player without importing ESPN types.
- A second provider implements the same port instead of changing scoring.
- Provider changes are localized to the adapter and its tests.
- Source IDs remain available for traceability without becoming domain IDs.

Ask yourself: if ESPN renamed `fullName` to `displayName`, which files should
change? The correct answer is the DTO/mapper boundary and its fixtures/tests,
not the HUD.

## Deep dive 2: compile-time types are not runtime validation

The result of `response.json()` is untrusted runtime data. TypeScript types do
not inspect the bytes returned by ESPN, so the HTTP client deliberately passes
the value into `mapEspnRoster(payload: unknown, ...)`.

The mapper narrows in stages:

```text
unknown
  -> record with teams
  -> team with roster entries
  -> entry with playerPoolEntry.player
  -> player with valid id and non-empty fullName
  -> CanonicalRoster
```

The type assertion in a test fixture is acceptable because the fixture is
controlled test input. The production response is not asserted into an ESPN
type before validation. This distinction is the practical difference between
“the compiler accepts it” and “the program has checked it.”

## Deep dive 3: three kinds of failure

V3 keeps these failures separate because they lead to different operator and
retry decisions:

| Failure | Example | Classification | Retry? |
|---|---|---|---|
| Transport | DNS failure or connection drop | `UNAVAILABLE` | bounded retry |
| HTTP policy | 401, 403, 404, 429 | auth/not-found/rate-limit | no automatic retry |
| Contract | malformed JSON or missing field | `INVALID_PAYLOAD` | no |

`fetch()` resolving does not mean the request succeeded; HTTP 404 and 503 are
still fulfilled responses, so the adapter checks `response.ok` and classifies
the status. A rejected fetch is a transport failure. A successful response
whose body cannot be parsed or mapped is a contract failure.

## Deep dive 4: why timeouts use AbortController

A request that waits forever is a resource and user-experience problem. The
adapter creates an `AbortController`, passes its signal to `fetch`, and aborts
after five seconds. The `finally` block clears the timer on both success and
failure.

The important invariant is not “every timeout throws the same browser error.”
It is “after the controller is aborted, the adapter reports a stable domain
error: `UNAVAILABLE` with a timeout message.” That makes tests and callers
independent of browser-specific exception wording.

## Deep dive 5: retry ownership and idempotency

The ESPN adapter knows how to make one request. The application layer knows
whether retrying fits the user experience, budget, and operation semantics.
That is why `loadRosterWithRetry` wraps a `ProviderPort` instead of putting a
loop inside the mapper.

Roster loading is read-only, so retrying transient unavailability is generally
safe. Even so, the policy is bounded. Infinite retries can turn an outage into
an extension that never settles. Rate limits are intentionally terminal here:
the future policy may honor `Retry-After`, but V3 does not pretend to have
implemented that behavior.

The injected `sleep` function is a testing seam. Tests can prove “three
attempts, two waits” instantly without waiting 750 milliseconds.

## Lab exercises

Run the tests first:

```bash
npm test
```

Then try these changes one at a time:

1. Rename `fullName` in the fixture. Observe `INVALID_PAYLOAD`.
2. Change the mocked response from 503 to 429. Confirm the retry wrapper makes
   only one provider call.
3. Make the fake provider fail twice with `UNAVAILABLE`, then succeed. Confirm
   three calls and two sleeps.
4. Set `timeoutMs` to `1` and use the hanging fetch test. Observe the stable
   timeout classification.
5. Add a second fake provider that returns the same `CanonicalRoster`. Verify
   that no HUD or scoring code changes.

## Checkpoint questions

- Where is the first point at which untrusted data becomes trusted data?
- Why is malformed JSON different from a 503?
- Why is retry policy outside `mapEspnRoster`?
- Which fields are domain data, and which are traceability metadata?
- What evidence would you need before claiming live ESPN support?

## Further reading

- [TypeScript narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)
  — user-defined type guards and discriminated unions.
- [TypeScript basic types](https://www.typescriptlang.org/docs/handbook/basic-types)
  — why `unknown` is safer than `any` for external data.
- [MDN Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
  — fulfilled responses versus rejected network requests.
- [MDN AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort)
  — aborting fetches and response-body consumption.
- [RFC 9110, HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
  — normative status-code semantics.
- [Chrome extension host permissions](https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions)
  — why future live cross-origin access is a security and permission boundary.

## Reflection prompt

Write a short paragraph answering: “What would break first if we skipped the
canonical model?” Include one concrete ESPN field leaking into the HUD and one
failure that would become incorrectly retryable.
