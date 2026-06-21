# Decision 0004 — Frontend Stream Mode And Low-Power Default

Date: 2026-06-21
Owner: Codex

## Decision

The frontend defaults to a contract-shaped mock stream and low-power rendering.

## Rationale

- Claude's WebSocket server is not complete yet.
- Codex can still build and verify the UI against `CONTRACTS/websocket_api.md`.
- The target demo machine may be a 2017 MacBook Air with Intel integrated graphics and 8 GB RAM.

## Details

- Mock mode is default: `VITE_OHMIC_STREAM=mock`.
- Real mode is opt-in: `VITE_OHMIC_STREAM=real`.
- Real WebSocket URL defaults to `ws://localhost:8765`.
- Low-power mode defaults on and reduces rendering cost.

## Consequences

- The frontend is demoable before the backend WebSocket server exists.
- Real integration remains a single config switch after Claude Step 6.
- Fancy effects should remain gated behind low-power mode.

