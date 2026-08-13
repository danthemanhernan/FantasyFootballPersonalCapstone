# Sprint 0 — First vertical slice

## Outcome

A browser extension popup renders a fantasy matchup, updates three sample players from fake football events, and celebrates a touchdown.

## Concepts

- Monorepos and npm workspaces
- React component boundaries
- TypeScript union types
- Pure state transitions
- Manifest V3 extension anatomy
- The difference between a simulator and a provider

## Exercises

1. Run the app in development mode and identify the React entry point.
2. Change the scripted event sequence and observe the HUD.
3. Add a fourth sample player without changing the HUD component.
4. Explain why \`applyEvent\` returns a new player array instead of mutating React state.
5. Load the production build as an unpacked Chrome extension.

## Definition of done

- \`npm install\` completes.
- \`npm run typecheck\` passes.
- \`npm run build\` produces \`apps/extension/dist\`.
- The popup can start, pause, and reset the simulator.
- A touchdown event changes fantasy points and shows an accessible notification.

## Reflection

What assumptions are hidden in the fake scoring rules? Which one would cause the largest user-visible bug when we connect a real league?
