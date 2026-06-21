# Codex — Build Log (Codex writes; Claude does not edit)

<!-- Newest entries on top. Template:

## [date-time] <title>
- What I did:
- Files touched (frontend/ only):
- Decisions/assumptions (+ defaults):
- Anything I need from Claude / the contract:
- Next step:
-->

## [2026-06-20 23:13:33 PDT] Frontend scaffold + contract-shaped dashboard
- What I did:
  - Scaffolded `frontend/` as a Vite + React + TypeScript app.
  - Installed `three`, `@react-three/fiber`, `@react-three/drei`, `recharts`, `zustand`, and `lucide-react`.
  - Built TypeScript types directly from `CONTRACTS/websocket_api.md`.
  - Added a contract-shaped mock stream, a real WebSocket client switch, Zustand telemetry state, a 3D microgrid scene, metric panels, demand chart, alerts banner, low-power mode, and Kill/Restore Solar controls using the contract command shape.
  - Verified desktop and narrow viewport rendering in the browser.
- Files touched (frontend/ only):
  - `frontend/`
  - `vault/Agent Logs/Codex Log.md`
- Decisions/assumptions (+ defaults):
  - Default stream is mock via `VITE_OHMIC_STREAM=mock`; set `VITE_OHMIC_STREAM=real` to connect to `ws://localhost:8765`.
  - Low-power mode defaults on for the 2017 MacBook Air target.
  - The frontend sends `{ "type": "chaos", "target": "PV_01", "action": "kill" | "restore" }` exactly as specified by the WebSocket contract.
- Anything I need from Claude / the contract:
  - Backend WebSocket server at `ws://localhost:8765` to verify real frames.
  - Confirm whether live command failures should produce an explicit error frame in a future contract revision; v1 says unknown commands are ignored.
- Next step:
  - When Claude's WebSocket server is running, launch the frontend with `VITE_OHMIC_STREAM=real npm run dev -- --host 127.0.0.1` and verify live frames match the mock behavior.
