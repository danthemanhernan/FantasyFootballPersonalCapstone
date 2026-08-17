# References and further reading

Replace placeholders with the exact source, date read, and takeaway. Categories: Manifest V3; HTTP/API design; domain/events; asyncio/WebSockets; broker guarantees; Postgres/Redis; Monte Carlo/calibration; observability/SRE; containers/Kubernetes; detection/tracking/OCR/entity resolution. Check current documentation and licensing before copying examples.

## Domain modeling

- Martin Fowler, [Value Object](https://martinfowler.com/bliki/ValueObject.html), read 2026-08-16. Takeaway: value objects are identified by their values rather than by a separate identity; this supports treating `PlayerStats`, `ScoringRules`, and `ScoringBreakdown` as calculation inputs and outputs.
