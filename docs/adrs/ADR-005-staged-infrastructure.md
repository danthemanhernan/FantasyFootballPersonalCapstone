# ADR-005: Staged infrastructure

- Status: Accepted
- Date: 2026-08-12

Start with in-process simulation and local files, then Postgres/Redis, then a broker, containers, and only afterward Kubernetes/cloud. Each step requires a measured constraint and exit criterion so infrastructure remains explainable.
