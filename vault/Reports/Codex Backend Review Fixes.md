# Codex Backend Review Fixes

Date: 2026-06-21
Owner: Codex
Commit: `f69f9a1 backend: harden mqtt run isolation and gates`
Status: Fixed and pushed.

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

