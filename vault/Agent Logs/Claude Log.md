# Claude Code — Build Log (Claude writes; Codex does not edit)

<!-- Newest entries on top. Template:

## [date-time] <title>
- What I did:
- Files touched (backend/ or CONTRACTS/ only):
- Decisions/assumptions (+ defaults):
- Open questions / risks for the human:
- Next step:
-->

## [2026-06-20] Market loop — real agents, steady-state (Step 4)
- What I did: Built the four real agents (`solar.py`, `battery.py`, `load.py`, `grid_operator.py`), a `runner.py` to wire the sim, and `check_market.py`. The operator clears the CDA + feasibility and publishes `market/clearing` each settled tick. `check_market` passes deterministically (trades + curtailment + energy conservation, all line flows ≤ rating, stable over repeated runs). All 34 unit tests still green.
- Files touched (backend/ only): `backend/sim/agents/{solar,battery,load,grid_operator}.py`, `backend/sim/runner.py`, `backend/scripts/check_market.py`, `backend/sim/physics/network.py` (additive per-match breakdown), `backend/config.yaml`, `backend/sim/physics/{degradation,recursive_ridge}.py` (float casts).
- Decisions/assumptions (+ defaults): See `vault/Decisions/0002-market-loop-design.md` — (1) 2-tick settlement grace for reliable pub/sub clearing; (2) orders are QoS 0, clearing/alerts QoS 1; (3) battery is a two-sided participant (charge below SoC target band, discharge above) so curtailment is exercised; (4) fixed a PyYAML scientific-notation-as-string trap + added defensive numeric casts. Feeder rating lowered to 60 kW (< 80 kW solar peak) so midday curtailment triggers.
- Open questions / risks for the human: Night ticks legitimately have no trades (no generation; battery below discharge threshold) — load shows `unmet` at night, which is physically correct, not a bug.
- Next step: Step 5 — self-healing (chaos kill, alert, shed, grid-forming, recovery). Heartbeat detection + fault-mode hooks are already in place.

## [2026-06-20] The math — 4 modules + 5 ridge rails (Step 3)
- What I did: Implemented all four pure math modules and tested them (34 pytest total). `degradation.py` (quadratic-DoD marginal cost, floor + non-negative clamp). `recursive_ridge.py` (Sherman-Morrison + forgetting, with all 5 rails: Welford standardization w/ unstandardized bias, condition watchdog + numpy closed-form re-anchor, denom-underflow skip, prediction clamp, bounded rolling buffer). `clearing.py` (real CDA, uniform price = marginal ask). `network.py` (line-capacity curtailment of marginal matches; `route` callable = v2 OPF seam). Forced the underflow and re-anchor rails to fire in tests.
- Files touched (backend/ only): `backend/sim/physics/{degradation,recursive_ridge,clearing,network}.py`, `backend/tests/test_{degradation,recursive_ridge,clearing,network}.py`.
- Decisions/assumptions (+ defaults): Re-anchor uses numpy closed-form ridge (`solve(XᵀX+αI, Xᵀy)`) as PRIMARY — scikit-learn is installed but intentionally not a hard dependency, removing the Python-3.14 wheel risk. Ridge logs re-anchors/skips via an injected `log` callable (no I/O in the pure module); the Load agent will wire it to the vault.
- Open questions / risks for the human: Degradation coefficients are empirical stand-ins (documented in config), not a specific cell datasheet.
- Next step: Step 4 — wire real agents and the market loop; assert energy conservation.

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
