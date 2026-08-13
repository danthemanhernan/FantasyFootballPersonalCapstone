# Fantasy Football HUD

A project-based engineering capstone that puts a live fantasy football scoreboard on top of an NFL broadcast. Sprint 0 establishes the smallest useful vertical slice: a Chrome Manifest V3 extension, a fake football event stream, three sample fantasy players, and a React HUD with touchdown notifications.

## Sprint 0 goals

- Run a React + TypeScript Chrome extension locally.
- Model football events as typed data.
- Simulate a drive without an external NFL provider.
- Translate events into fantasy points.
- Render a compact HUD and celebrate touchdowns.

## Monorepo layout

    apps/extension/       Manifest V3 React/TypeScript extension
    apps/extension/src/   Simulator, scoring model, HUD, and app shell
    docs/adr/             Architecture Decision Records
    curriculum/           Learning milestones and exercises

## Setup

Requirements: Node.js 20+ and npm 10+.

    npm install
    npm run typecheck
    npm run build

To load the extension in Chrome:

1. Run \`npm run build\`.
2. Open \`chrome://extensions\`.
3. Enable Developer mode.
4. Choose Load unpacked and select \`apps/extension/dist\`.
5. Open the extension popup and press Start simulation.

The simulator advances every 2.5 seconds. It includes a passing touchdown so the notification path is visible immediately.

## V0–V12 roadmap

| Version | Outcome | Engineering focus |
| --- | --- | --- |
| V0 | Working local HUD with fake events | TypeScript, React, browser extension basics |
| V1 | Real scoring rules and configurable league settings | Domain modeling, tests, pure functions |
| V2 | Persist leagues and lineups locally | Chrome storage, schemas, migrations |
| V3 | Ingest a real fantasy platform API | HTTP clients, auth, rate limits |
| V4 | Ingest live play-by-play data | Providers, polling, normalization |
| V5 | Reliable event processing | Idempotency, retries, dead-letter thinking |
| V6 | Backend service for shared state | API design, Postgres, observability |
| V7 | Live updates without polling | WebSockets or server-sent events |
| V8 | Multiple leagues and matchups | Multi-tenancy, caching, authorization |
| V9 | Production deployment | Containers, CI/CD, secrets, environments |
| V10 | Analytics and projections | Feature engineering, evaluation, model boundaries |
| V11 | Scale and resilience | Queues, backpressure, load testing |
| V12 | Broadcast-ready product | UX polish, accessibility, performance, security |

## Learning path

The curriculum is intentionally problem-led. Each version introduces a tool only after the previous version makes its need obvious. Start with [curriculum/sprint-0.md](curriculum/sprint-0.md), and keep the full curriculum index in [curriculum/README.md](curriculum/README.md).

## Architecture decisions

- [ADR-001: Why a browser extension](docs/adr/ADR-001-browser-extension.md)

## Current limitations

This is deliberately fake data. It does not connect to an NFL feed, fantasy platform, or account. The next milestone is to make the scoring engine accurate and testable before adding integrations.
