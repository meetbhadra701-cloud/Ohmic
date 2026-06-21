# Codex Backend Review Fixes

Date: 2026-06-21
Owner: Codex
Commit: `f69f9a1 backend: harden mqtt run isolation and gates`
Status: Fixed and pushed.

## 2026-06-21 Step 6/7 Review Addendum

Status: Fixed and verified.

### What Was Wrong

- The Step 6 WebSocket server passed shape checks, but live Kill Solar frames did not prove self-healing. The first CRITICAL frame showed PV down, but the battery could stay in `market` briefly and then grid-form with no useful flow if market participation had drained it.
- The battery's normal market discharge path could repeatedly offer energy above the SoC floor before previous offers settled. That overcommitted the same stored energy and left no emergency reserve.
- Emergency grid-forming still depended on the market ask/clearing loop. That violated the manual requirement to bypass the market and serve critical load immediately during a fault.
- The WebSocket frame cache could show load `served_kw: 0` during CRITICAL even when the battery had begun emergency discharge, so the frontend visual story was wrong.
- WebSocket chaos relay accepted any known node target even though the contract/UI only define Kill/Restore Solar for `PV_01`; it also relayed MQTT `chaos/command` without a tick.
- The fast market gate cleared empty books because the operator's 8-tick grace was too short for 0.1-0.2 second MQTT verification runs.
- The frontend displayed `FEEDER_1` as `/ 80.0 kW`, but backend config rates the feeder at `60.0 kW`.

### How It Was Fixed

- Added battery pending-sell tracking and `_market_dischargeable_kw()` so normal market asks preserve the emergency reserve around `TARGET_SOC`.
- Changed grid-forming to bypass the auction, discharge directly to the latest critical load, decrement SoC immediately, and report `unmet_kw` at the SoC floor.
- Ignored delayed market clearing effects while the battery is in `grid_forming`.
- Made the WebSocket CRITICAL frame derive emergency load served/shed from battery grid-forming flow.
- Restricted WebSocket chaos relay to `PV_01`, validated `kill|restore`, and stamped the current tick on the MQTT command payload.
- Added configurable `operator.settle_grace_ticks` and `operator.heartbeat_grace_ticks`; live defaults remain 8, fast gates override to 32.
- Updated the frontend feeder label to avoid a stale hardcoded rating.

### Verification Completed

```bash
.venv/bin/python -m pytest backend
.venv/bin/python backend/scripts/check_tick.py
.venv/bin/python backend/scripts/check_market.py
.venv/bin/python backend/scripts/check_heal.py
.venv/bin/python backend/scripts/check_ws.py
npm run build
npm run lint
```

Results:

- `46 passed`
- tick gate passed
- market gate passed: 60 clearings, 35 with trades, 19 with curtailment
- self-healing gate passed: `CRITICAL@61 -> shed+grid_forming -> ALL_CLEAR@106`
- WebSocket gate passed: 30 contract-compliant frames
- frontend build and lint passed
- live WebSocket probe passed: after Kill Solar, frame tick 15 showed battery `grid_forming`, `flow_kw` 14.28, load `served_kw` 14.28, and load `shed_kw` 28.33

## Why This Happened

The backend passed its unit tests, but the MQTT integration gates were vulnerable to retained state and async timing. This produced misleading results such as:

- old retained `market/clearing` frames leaking into a fresh run
- dummy tick tests seeing `LOAD_CAMPUS` even when only PV/BESS dummy nodes were started
- market gates sometimes clearing empty books
- contract QoS mismatches for market bids and asks

## Fixes Applied

- Added `run_id` to MQTT message envelopes.
- Made `Bus` filter inbound messages by `run_id`.
- Made MQTT client ids unique per run.
- Added `FakeBroker` and `FakeBus` for deterministic broker-free tests.
- Stopped globally skipping retained messages in agents; retained frames are now made safe by `run_id`.
- Changed market bids and asks to QoS 1 to match the contract.
- Documented heartbeat QoS 1 in `CONTRACTS/mqtt_topics.md`.
- Made `market/clearing.unmet_kw` include curtailed demand.
- Updated `CONTRACTS/message_schemas.md` with:
  - `run_id`
  - load forecast telemetry fields
- Updated gate scripts so each run is isolated.
- Tuned `check_market.py` to `0.20s` ticks so QoS 1 order round-trips are collected before settlement on the Intel Air.

## Verification Completed

```bash
.venv/bin/python -m pytest backend
.venv/bin/python backend/scripts/check_tick.py
.venv/bin/python backend/scripts/check_market.py
.venv/bin/python backend/scripts/check_heal.py
```

Results:

- `36 passed`
- tick gate passed
- market gate passed with trades and curtailment
- self-healing gate passed: kill -> CRITICAL -> shed + grid-forming -> ALL_CLEAR

## Important Follow-Up For Claude Step 6

The WebSocket server should preserve the current `run_id` internally when bridging to MQTT. If Claude chooses to expose `run_id` in WebSocket frames, `CONTRACTS/websocket_api.md` and the frontend types must be updated through the Contract Lock protocol.
