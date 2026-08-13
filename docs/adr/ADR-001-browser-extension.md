# ADR-001: Use a browser extension for the first product surface

- Status: Accepted
- Date: 2026-08-12

## Context

The product goal is a fantasy football HUD that appears while a user watches an NFL broadcast. A separate dashboard would force the user to leave the broadcast, while a desktop app would add installation and platform complexity before we understand the interaction.

The first learning milestone should also stay close to the user-visible product. We need a small surface that can render a HUD, receive future live events, and be loaded locally without a backend.

## Decision

Start with a Chrome Manifest V3 browser extension built with React and TypeScript.

The extension gives us:

- A fast feedback loop: build, load unpacked, and see the HUD.
- A natural path to content scripts and overlays on supported pages.
- A clear boundary between UI, event ingestion, and future backend services.
- A realistic introduction to permissions, packaging, and browser APIs.

## Consequences

Positive:

- The product is visible in the same browser where the broadcast may be playing.
- Chrome storage and messaging can be introduced when the current in-memory model becomes limiting.
- The extension can later consume a backend stream without changing the core HUD.

Trade-offs:

- Browser extension policies and host permissions become part of the system.
- A full overlay will require careful handling of content-script isolation and site compatibility.
- Chrome is the initial target; cross-browser support is deferred.

## Revisit when

We should revisit this decision if the main viewing experience moves to a native TV app, if browser overlays are blocked by target sites, or if the product requires coordinated multi-user state before the extension surface is mature.
