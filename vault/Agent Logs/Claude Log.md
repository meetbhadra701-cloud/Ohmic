# Claude Code — Build Log (Claude writes; Codex does not edit)

<!-- Newest entries on top. Template:

## [date-time] <title>
- What I did:
- Files touched (backend/ or CONTRACTS/ only):
- Decisions/assumptions (+ defaults):
- Open questions / risks for the human:
- Next step:
-->

## [2026-06-20] Physical models — synthetic curves (Step 2)
- What I did: `physics/profiles.py` — pure deterministic curves: `solar_output_kw` (sin bell over a dawn-0.25/dusk-0.75 daylight window, capped at inverter limit), `load_demand_kw` (morning+evening Gaussian peaks over a base, optional seeded noise), `split_load` (critical/non-critical). `conftest.py` makes `sim` importable in tests. 12 pytest assertions green.
- Files touched (backend/ only): `backend/sim/physics/profiles.py`, `backend/conftest.py`, `backend/tests/test_profiles.py`.
- Decisions/assumptions (+ defaults): Curves are pure functions so Step 7 swaps a CSV source behind the same signatures with no agent change. Noise is injected via a numpy Generator for reproducibility.
- Open questions / risks for the human: none.
- Next step: Step 3 — the four math modules with full safety rails.

## [2026-06-20] Clock + bus + dummy nodes (Step 1)
- What I did: Built the core plumbing — `config.py` (YAML loader), `bus.py` (the single aiomqtt+JSON seam; stamps schema_version/ts; skips malformed messages; `FakeBus`-swappable interface), `clock.py` (publishes `grid/tick` with sim_time/day_phase; monotonic tick is the only clock), `agents/base.py` (common async agent shape, dispatch by topic), `agents/dummy.py` (fixed-state node). `check_tick.py` runs clock + 2 dummy nodes + verifier and passed (20 contiguous ticks, both nodes publishing state).
- Files touched (backend/ only): `backend/sim/config.py`, `backend/sim/bus.py`, `backend/sim/clock.py`, `backend/sim/agents/base.py`, `backend/sim/agents/dummy.py`, `backend/scripts/check_tick.py`.
- Decisions/assumptions (+ defaults): Each agent owns its own Bus/connection (broker = bus; no direct agent calls). Agents edge-trigger on `grid/tick` (deterministic, pausable). aiomqtt `identifier=` is the 2.x client-id kwarg.
- Open questions / risks for the human: none.
- Next step: Step 2 — synthetic solar irradiance curve + load demand profile (critical/non-critical split), pytest (no broker).

## [2026-06-20] Backend skeleton + deps + broker + MQTT smoke test (Step 0)
- What I did: Created the `backend/` package skeleton, pinned `requirements.txt`, `config.yaml` with all labeled defaults, a repo-owned `mosquitto.conf`, and the Step-0 MQTT smoke test. Created a venv, installed deps on Python 3.14, brought up Mosquitto, and passed the smoke test (round-tripped one message).
- Files touched (backend/ or CONTRACTS/ only): `backend/requirements.txt`, `backend/config.yaml`, `backend/mosquitto.conf`, `backend/sim/__init__.py`, `backend/sim/agents/__init__.py`, `backend/sim/physics/__init__.py`, `backend/scripts/smoke_mqtt.py`.
- Decisions/assumptions (+ defaults): All deps install on Python 3.14 with cp314 wheels (numpy 2.4.6, scipy 1.18, scikit-learn 1.9.0, aiomqtt 2.5.1 pure-Python) — the 3.14 wheel risk did not materialize. Mosquitto 2.1.2 ships no default `mosquitto.conf` (only `.example`), so the brew service errored; fixed by installing a minimal localhost-only config (`listener 1883 localhost`, `allow_anonymous true` — safe for single-machine sim). Config defaults per `config.yaml` (line FEEDER_1 rating 80 kW < load peak 120 kW so curtailment will trigger).
- Open questions / risks for the human: `allow_anonymous true` is fine for a localhost sim but should never be used if the broker is ever exposed beyond localhost. The brew service config lives at `/usr/local/etc/mosquitto/mosquitto.conf` (copied from the repo) — re-copy if you change the repo version.
- Next step: Step 1 — clock + bus + dummy nodes; `scripts/check_tick.py` asserts monotonic ticks.

## [2026-06-20] CONTRACTS published v1
- What I did: Authored the three contract files that Codex (frontend) was blocked on, and added the HTTPS git remote (SSH currently fails with publickey).
- Files touched (backend/ or CONTRACTS/ only): `CONTRACTS/mqtt_topics.md`, `CONTRACTS/message_schemas.md`, `CONTRACTS/websocket_api.md`.
- Decisions/assumptions (+ defaults): Froze four spec gaps (see `vault/Decisions/0001-contract-spec-gaps.md`): (1) uniform clearing price = last matched ask price; (2) curtailed trades settle on delivered kW at cleared price; (3) sign convention generation/discharge +, load/charge −; (4) heartbeat clears after ≥2 consecutive good beats (anti-flap). Dedicated `node/<id>/heartbeat` topic separate from state. WebSocket frame is a render-complete superset at `ws://localhost:8765`, one frame per tick, with a client→server `chaos` command for the Kill-Solar control.
- Open questions / risks for the human: Python 3.14.2 on the Intel Air — numpy/scikit-learn/paho wheels resolve, but to de-risk, the ridge re-anchor will use a numpy closed-form fallback (sklearn optional). Mosquitto not yet installed (will `brew install` in Step 0.5).
- Next step: Backend skeleton, requirements.txt, venv, install + start Mosquitto, MQTT smoke test.
