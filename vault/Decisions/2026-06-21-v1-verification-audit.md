# v1 Verification Audit — 2026-06-21

> Adversarial audit. Posture: disprove "done," demand reproducible evidence.
> Auditor changed **zero** project files (only `/tmp/audit_*.py` harnesses).

## 1. VERDICT

**DONE-WITH-CAVEATS.** The full v1 vertical slice runs end-to-end live on a real
Mosquitto broker + real WebSocket: real CDA market with line-capacity curtailment,
quadratic-DoD battery pricing, 5-rail online ridge forecast, and the complete
self-heal arc driven **through the real WebSocket control path** (Kill-Solar →
CRITICAL → load shed → battery grid-forming → Restore → ALL_CLEAR → recovery).
Caveats are documentation/polish and one design note — none block the demo.

## 2. Evidence table (IN-scope)

| Component | Status | Evidence (command → observed) | Notes |
|---|---|---|---|
| 4 sim nodes (Solar/Battery/Load/Operator) | PASS | `check_tick` → "20 monotonic contiguous ticks; PV_01:19, BESS_01:19"; live frame shows all 4 acting | Real agents in `backend/sim/agents/` |
| Real MQTT pub/sub, no direct agent calls | PASS | `smoke_mqtt.py` → "round-tripped … on smoke/test"; each agent owns its own `Bus` (aiomqtt) in `runner.py`; broker is the only channel | Real Mosquitto localhost:1883 |
| Tick clock sync | PASS | `check_tick` contiguous ticks; agents edge-triggered on `grid/tick` (`base.py`) | — |
| Quadratic degradation cost | PASS | `degradation.py:41` `b2*dod**2`; `test_quadratic_dod_term_dominates_deep_swings` PASS | Nonlinear term present & dominant |
| Recursive ridge, 5 rails | PASS | `recursive_ridge.py` rails 1-5 all present; `test_rail2/3/4/5` + convergence PASS (pred within 3kW of truth) | Sherman-Morrison + forgetting |
| CDA clearing | PASS | `clearing.py` real sort+walk, uniform=last matched ask; `test_merit_order_uniform_price_is_marginal_ask` PASS | Not an if/else |
| Physical feasibility / curtailment | PASS | Live frame tick 49: FEEDER_1 pinned at **60.0kW = rating**, curtailed 9.28kW; `check_market` → "19 with curtailment"; `test_marginal_match_curtailed_to_rating` PASS | Money cannot violate a wire |
| Self-heal arc (live, via WS) | PASS | `/tmp/audit_live.py` → kill@t19 → CRITICAL@t26 ("missed 3 heartbeats", alive=false) → batt grid_forming flow 24.5kW → load shed 42.5kW → restore@t69 → ALL_CLEAR@t75 → recovered. "ARC COMPLETE: True" | Driven through real WebSocket |
| WebSocket broadcast = contract | PASS | `check_ws` → "30 frames; all fields contract-compliant"; live frame field-diff matches `websocket_api.md` exactly | — |
| Frontend (R3F scene, panels, flows, alerts, Kill-Solar) | PASS (build) / UNVERIFIED (pixels) | `npm run build` → tsc clean, 2875 modules, no type errors; `App.tsx` has Canvas/FlowLine/nodes/Kill+Restore buttons; `types.ts` matches contract | Visual render not verifiable headless — see §8 |
| CONTRACTS = single source of truth | PASS | backend emit ↔ `CONTRACTS/*` ↔ frontend `types.ts` aligned field-for-field | — |
| Synthetic data path | PASS | default profiles; `test_profiles` synthetic suite PASS | — |

**Test suite:** `pytest backend/` → **46 passed, 0 skipped, 0 xfail, 0 failed**.

## 3. Deferred items (correctly handled)

| Item | State | OK? |
|---|---|---|
| Real-CSV swap | **PRESENT** & working (`profiles.load_csv_profiles`, `data/*.csv`); gates green with CSV active | Beyond-min, not a failure |
| ADMM / OPF | Absent; `network.py` keeps the injectable `route` seam for v2 | Correct |
| VCG / McAfee auctions | Absent; uniform CDA only | Correct |
| Docker-per-agent / Kafka | Absent | Correct |
| Real-grid compliance (2030.5/Rule21/CSIP/islanding) | Absent | Correct — no scope creep |

## 4. Failure-mode hunt (§2)

1. **Fake-green tests** — None. 0 skip/xfail; no trivial/mock-echo asserts; no `NotImplementedError`/stub in source (only one benign "placeholder" docstring on the synthetic temp curve).
2. **Mocked-away reality** — Unit tests use an in-memory `FakeBroker` (legit deterministic unit testing). The **integration proof is the gate scripts**, which run against **real Mosquitto + real websockets**. Verified live.
3. **Contract drift** — None found. Live backend frame ≡ `websocket_api.md` ≡ frontend `TelemetryFrame`. One cosmetic nit: frontend types `forecast.cond` non-nullable, server can emit `null` pre-warm (never observed in steady run; live showed 603.5).
4. **Stubbed math** — All four modules genuinely implemented (quadratic DoD, real Sherman-Morrison + 5 rails, real sort/walk CDA, real curtailment). Verified by reading source + passing behavioral tests.
5. **Self-heal that doesn't heal** — Heals. Proven live end-to-end through the WS control path (§2 row).
6. **Ownership / conflict markers** — No `<<<<<<<`/`>>>>>>>` anywhere. Commit `632a37a` edited `backend/` **and** `frontend/src/App.tsx` together (Codex reaching into backend, evidently human-authorized). Boundary technically crossed; no damage.
7. **Gates that don't gate** — All 5 gates assert real behavior (trades cleared, curtailment fired, energy accounting, contract fields), not lint/smoke-only. They constitute real proof.
8. **Won't-run-clean** — Backend runs (`make run` / `python backend/main.py`, auto-starts broker). **Gap:** top-level `README.md` has no run instructions; steps live only in the vault. Fresh clone needs undocumented setup (venv+pip, mosquitto, `VITE_OHMIC_STREAM=real`, `npm install`).

## 5. Live-run transcript (Step D)

`/tmp/audit_live.py` (real broker + sim + WS; auto-chaos disabled; kill/restore sent over the socket):

```
steady (t9, night): mode NORMAL, soc 60%, warm=true
kill_sent           frame20 / tick19   (WebSocket {"type":"chaos","action":"kill"})
critical            frame28 / tick27   alert "PV_01 missed 3 heartbeats", solar alive=false
batt_gridforming    frame29 / tick28   flow 24.5kW, unmet 0.0
load_shed           frame29 / tick28   demand 67.0 / served 24.5 / shed 42.5
restore_sent        frame70 / tick69   (WebSocket {"type":"chaos","action":"restore"})
all_clear           frame77 / tick75   alert "PV_01 heartbeats resumed"
recovered           frame78 / tick77   battery back to market, shed 0
=== SELF-HEAL ARC COMPLETE: True
```

Midday trading frame (`/tmp/audit_frame.py`, default grace=8 / 0.2s tick), tick 49 12:15:
PV_01 79.8kW; flow PV_01→LOAD 60.0kW (curtailed 6.8); FEEDER_1=60.0kW (=rating);
clearing 0.02; forecast warm cond 603.5. Real market + real feasibility.

## 6. Contract diff (backend ↔ contract ↔ frontend)

All top-level keys (`schema_version, tick, sim_time, day_phase, mode, nodes,
market, forecast, alerts`) and every nested field present and aligned across the
live backend frame, `CONTRACTS/websocket_api.md`, and `frontend/src/types.ts`.
Only delta: `forecast.cond` nullable in practice (server) vs non-null (frontend
type) — cosmetic.

## 7. Gap list (prioritized)

**Blocks fresh-clone repro (not the demo itself):**
- **G1 [docs]** `README.md` lacks run instructions. *Fix:* add a Run section — `python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt`, `brew services start mosquitto`, `make run`, then `cd frontend && npm install && VITE_OHMIC_STREAM=real npm run dev`.

**Polish / notes (non-blocking):**
- **G2 [design]** During grid-forming, emergency energy bypasses the auction: `battery._grid_form` serves critical load directly and `server._assemble` reconciles load `served_kw`/`shed_kw` from battery `flow_kw` (server.py special-case). Works and frames are coherent, but "served during fault" is computed in the presentation layer, not cleared by the market. Consider routing emergency supply through a clearing for architectural purity.
- **G3 [coordination]** `632a37a` crossed the backend/frontend ownership boundary in one commit. No conflict, but note for discipline.
- **G4 [cosmetic]** Type `forecast.cond` as `number | null` in `types.ts`, or guarantee server emits a number pre-warm.
- **G5 [robustness]** Market is sensitive to `settle_grace` vs `tick_period` (too-tight grace starves the order book — reproduced). Default grace=8 is safe; keep gates from lowering it below QoS-1 round-trip latency.

## 8. Honest unknowns

- **3D visual render**: not verifiable in this headless environment. The frontend **type-checks and builds clean** (`npm run build` OK) and the scene graph is real R3F, but pixels were not observed. **Verify manually on the stronger Mac:** `cd frontend && npm install && npm run dev` (mock mode shows the self-heal arc immediately), then for live: start `make run` and `VITE_OHMIC_STREAM=real npm run dev`, click Kill Solar, confirm banner→CRITICAL, battery turns red/grid-forming, load shows shed, then Restore → ALL_CLEAR.
