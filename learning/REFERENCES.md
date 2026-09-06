# References and further reading

Replace placeholders with the exact source, date read, and takeaway. Categories: Manifest V3; HTTP/API design; domain/events; asyncio/WebSockets; broker guarantees; Postgres/Redis; Monte Carlo/calibration; observability/SRE; containers/Kubernetes; detection/tracking/OCR/entity resolution. Check current documentation and licensing before copying examples.

## Domain modeling

- Martin Fowler, [Value Object](https://martinfowler.com/bliki/ValueObject.html), read 2026-08-16. Takeaway: value objects are identified by their values rather than by a separate identity; this supports treating `PlayerStats`, `ScoringRules`, and `ScoringBreakdown` as calculation inputs and outputs.

## HTTP and APIs

- MDN, [Using the Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch), read 2026-08-24. Takeaway: HTTP status handling and network failure handling are separate concerns, so the provider client classifies both rather than treating every failure as a retryable error.
- IETF, [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html), read 2026-09-05. Takeaway: status-code classes describe different semantics; this supports separating authentication, missing resources, rate limits, and server unavailability.
- MDN, [AbortController: abort()](https://developer.mozilla.org/en-US/docs/Web/API/AbortController/abort), read 2026-09-05. Takeaway: an abort signal can cancel fetch work, which is the mechanism used by the bounded ESPN request.
- TypeScript, [Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html), read 2026-09-05. Takeaway: type guards narrow `unknown` after runtime checks; a compile-time DTO type alone cannot validate network JSON.
- Chrome for Developers, [Declare permissions](https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions), read 2026-09-05. Takeaway: extension host permissions enable cross-origin fetches but are also a security and user-trust boundary.
- MDN, [Web Storage API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API), read 2026-08-24. Takeaway: browser storage is a string-based client-side boundary, so application data needs explicit serialization, validation, and failure handling.
