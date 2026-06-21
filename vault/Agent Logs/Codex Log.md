# Codex — Build Log (Codex writes; Claude does not edit)

<!-- Newest entries on top. Template:

## [date-time] <title>
- What I did:
- Files touched (frontend/ only):
- Decisions/assumptions (+ defaults):
- Anything I need from Claude / the contract:
- Next step:
-->

## [2026-06-21 11:48:03 PDT] Fixed audit caveats G1 and G4
- What I did:
  - Read Claude's v1 audit and verified the two actionable caveats.
  - Added fresh-clone run instructions to `README.md` for backend setup, `make run`, real frontend mode, mock frontend mode, and verification commands.
  - Updated the frontend telemetry contract so `forecast.cond` is `number | null`, matching the WebSocket server's pre-warm behavior.
  - Added a safe UI rendering path that shows ridge condition as `warming` until a numeric condition value exists.
  - Ran frontend build and lint.
- Files touched (frontend/ only):
  - `frontend/src/types.ts`
  - `frontend/src/App.tsx`
  - `README.md` and this vault log were touched to resolve audit/documentation caveats.
- Decisions/assumptions (+ defaults):
  - Claude's `DONE-WITH-CAVEATS` audit remains historically accurate; this entry records that G1 and G4 were addressed afterward.
  - The README is now the source for fresh-clone run instructions; the vault remains the deeper project notebook.
- Anything I need from Claude / the contract:
  - None.
- Next step:
  - Hand back the caveat cleanup and pushed audit vault files.

## [2026-06-21 11:13:53 PDT] Step 6/7 backend review and repair
- What I did:
  - Reviewed Claude's completed Step 6 WebSocket server and Step 7 CSV swap against live behavior, not only schemas.
  - Found that Kill Solar produced a CRITICAL frame, but the battery could already be drained by market offers and the emergency path still behaved like a delayed market participant.
  - Fixed battery reserve handling so normal market asks preserve emergency SoC and pending offers cannot overcommit the same stored energy.
  - Fixed grid-forming so it bypasses the market, discharges immediately to critical load, and reports unmet critical load honestly at the SoC floor.
  - Fixed the WebSocket server's CRITICAL frame assembly so the frontend sees served critical load and shed non-critical load during emergency mode.
  - Fixed chaos relay validation so WebSocket commands only target `PV_01` and MQTT `chaos/command` includes the current tick.
  - Made operator settle/heartbeat grace configurable and raised it in fast verification scripts to avoid empty books and false heartbeat misses.
  - Removed the frontend's hardcoded feeder `/ 80.0 kW` display because backend config now rates `FEEDER_1` at 60 kW.
  - Verified a live WebSocket Kill Solar probe: CRITICAL at tick 14, battery `grid_forming` at tick 15 with positive flow and load shedding visible.
- Files touched (frontend/ only):
  - `frontend/src/App.tsx`
  - Backend/test/vault files were touched because the user explicitly asked Codex to review and fix Claude's backend work.
- Decisions/assumptions (+ defaults):
  - Live demo keeps operator grace at 8 ticks so Kill Solar remains watchable at 1 second per tick.
  - Fast gates override operator grace to 32 ticks because local MQTT clients lag under 0.1-0.2 second tick cadence.
  - Emergency battery reserve is the configured target SoC band, not the absolute SoC floor.
- Anything I need from Claude / the contract:
  - If Step 6 evolves, preserve the immediate grid-forming semantics; do not route emergency discharge through the auction.
- Next step:
  - Hand back the verified repair pass.

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
