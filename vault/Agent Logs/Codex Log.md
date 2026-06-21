# Codex — Build Log (Codex writes; Claude does not edit)

<!-- Newest entries on top. Template:

## [date-time] <title>
- What I did:
- Files touched (frontend/ only):
- Decisions/assumptions (+ defaults):
- Anything I need from Claude / the contract:
- Next step:
-->

## [2026-06-21 00:14:31 PDT] Populated Obsidian vault reports
- What I did:
  - Added readable report pages for the frontend dashboard and backend review fixes.
  - Added decision notes for frontend stream defaults and MQTT run isolation.
  - Added a Claude request about Step 6 WebSocket `run_id` handling.
  - Updated `vault/Home.md` with links to the new pages.
  - Added pointer files in the stale `/Users/meetbhadra/Ohmic/vault` folder so Obsidian users know to open `/Users/meetbhadra/Projects/microgrid/vault`.
- Files touched (frontend/ only):
  - None; vault population only.
- Decisions/assumptions (+ defaults):
  - The active Obsidian vault is `/Users/meetbhadra/Projects/microgrid/vault`.
  - `/Users/meetbhadra/Ohmic/vault` is stale and should only point to the active vault.
- Anything I need from Claude / the contract:
  - Claude should read `vault/Requests/2026-06-21-websocket-run-id-followup.md` before implementing Step 6.
- Next step:
  - Continue Step 6 integration after Claude ships the WebSocket server.

## [2026-06-21 00:01:20 PDT] Backend review fixes
- What I did:
  - Fixed retained MQTT cross-run contamination by adding `run_id` envelope stamping/filtering and unique per-run client ids.
  - Added `FakeBus`/`FakeBroker` for deterministic broker-free tests.
  - Aligned market bids/asks with contract QoS 1 and documented heartbeat QoS 1.
  - Updated gate scripts to use run ids and wait for both ticks and state messages.
  - Updated `market/clearing.unmet_kw` to include curtailed demand.
  - Updated MQTT schemas for `run_id` and load forecast telemetry.
  - Verified backend tests and gates.
- Files touched (frontend/ only):
  - None; this was a user-requested backend/contracts repair pass.
- Decisions/assumptions (+ defaults):
  - `run_id` is now part of the common MQTT envelope and is required for retained-frame safety.
  - `check_market.py` uses a 0.20 s tick period so QoS 1 order round-trips arrive before settlement on the Intel Air.
  - Operator settle/heartbeat grace is 8 ticks to avoid false empty-books and false liveness misses under async MQTT scheduling.
- Anything I need from Claude / the contract:
  - Future WebSocket server should include or preserve `run_id` internally when relaying chaos commands onto MQTT.
  - If WebSocket frames expose `run_id`, `CONTRACTS/websocket_api.md` and frontend types need a Contract Lock update.
- Next step:
  - Build Step 6 WebSocket server against the updated MQTT envelope and verify live frontend mode with `VITE_OHMIC_STREAM=real`.

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
