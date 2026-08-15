# ADR-003: Provider abstraction

- Status: Accepted
- Date: 2026-08-12

External providers differ in IDs, names, pagination, freshness, and failure semantics. Define narrow provider ports and map DTOs to canonical domain models at the boundary; preserve raw payloads for debugging. Revisit if one provider becomes the true domain for every integration.
