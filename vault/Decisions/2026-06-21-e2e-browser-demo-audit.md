# v1 End-to-End Browser Demo Audit — 2026-06-21

> Acceptance test, not a build session. Posture: operate the **real running
> system in a real browser** (Claude in Chrome, Meet's browser) and try to make
> it misbehave. Every claim cross-checked against the live WebSocket payload via
> an independent frame logger. No mocks. The auditor changed **zero** project
> files (frontend was read-only; only `/tmp/ws_logger.py` + `/tmp` harnesses and
> direct-WS probes were used).

## 1. VERDICT

**PASS-WITH-CAVEATS.** The full v1 slice runs end-to-end live in a real browser:
the 3D dashboard renders all four nodes, the rendered numbers match the WebSocket
stream tick-for-tick, the market/forecast/feasibility are real, and the
**Kill-Solar self-heal arc was observed live with the scene and the numbers moving
together** through every stage (CRITICAL → load shed → battery grid-forming →
SoC-floor → honest unmet → Restore → ALL_CLEAR → market). The caveats are real and
demo-relevant — chiefly a **stale alert-banner text during CRITICAL**, **no
WebSocket auto-reconnect**, and a **~15–18-tick delay (plus a lost-command race on
rapid clicks) on the browser's Kill/Restore control** — but none of them break the
core demo when driven deliberately.

The previous audit's single biggest "honest unknown" — **the 3D pixels** — is now
**resolved: the scene renders correctly** in this browser (WebGL works here).

## 2. Environment / method

- Stack (all real, no mocks): Mosquitto `:1883`, backend sim + WebSocket server
  `:8765` (`backend/main.py`), Vite frontend `:5173` with `VITE_OHMIC_STREAM=real`.
- Cross-check rig: `/tmp/ws_logger.py` — an **independent** WS client logging every
  frame as a one-liner keyed by tick, so any rendered value can be checked against
  the exact-tick payload. Direct-WS probe scripts used to isolate frontend vs
  backend behavior.
- Browser: Claude in Chrome driving Meet's browser; screenshots captured inline at
  each claim (Chrome-MCP screenshot IDs noted; images shown live in-session, not
  saved to repo).
- Machine note: ran on this Mac without WebGL stutter; no frame drops attributable
  to the laptop were observed. Findings below are **app** behavior, not laptop
  limits.

## 3. Core demo result (§3) — the centerpiece

| Stage | Result | Evidence (rendered ↔ stream) |
|---|---|---|
| 3.1 Cold load | **PASS** | Scene renders; PV_01 / GRID_OP / BESS_01 / LOAD_CAMPUS all present + labeled; gold power-flow line drawn. Console clean except one benign `THREE.Clock deprecated` warning. |
| 3.2 Steady-state | **PASS** | 3 independent cross-checks, all exact: **tick 541** rendered PV 52.6kW / LOAD 41.9kW / 70% ↔ WS pv=52.6 / served=41.9 / soc=70.0; **tick 75** LOAD 60.0 / BESS 90.6% ↔ served=60.0 / soc=90.6 (teal line = battery discharging 24.7kW at SoC>75%); **tick 138** LOAD 40.0 / 70% ↔ served=40.0 / soc=70.0. Price stable $0.020, never NaN. |
| 3.3 Forecast sanity | **PASS** | `predicted_demand_kw` tracks `actual` within ~1 kW continuously (e.g. 76.9 vs 78.0; 66.1 vs 66.6). Bell-shaped daily curve renders; not flat, not wild. |
| 3.4 Kill-Solar arc | **PASS (with banner defect D1)** | Full arc proven live — see below. |

### Kill-Solar self-heal arc (driven through the real browser button)

| Stage | Tick | Stream evidence | Scene evidence |
|---|---|---|---|
| Kill clicked | ~814 | — | button press captured |
| Solar dies (output freezes) | ~833 | pv frozen at 39.8, still alive=True | — |
| **CRITICAL** | 843 | backend log "PV_01 missed 3 heartbeats"; alive→False | header chip → CRITICAL (red); **PV_01 OFFLINE**; GRID_OP → red |
| Battery grid-forming → SoC floor | →20% | soc 70%→**20.0%** (floor, never negative), mode `grid_forming` | **BESS 20.0%**, node red |
| Load fully shed | — | demand 64.7 / **shed 64.7** / served 0.0, health degraded | **LOAD 0.0 kW**, node red |
| Honest unmet | — | batt flow=0 at floor, **unmet=27.6 kW** reported; market unmet=45.6 | numbers show shed, not faked supply |
| Restore clicked | 1057 | — | button press |
| **Solar revives** | 1073 | alive→True; `alerts:[{ALL_CLEAR, "PV_01 heartbeats resumed"}]` | PV back online |
| **NORMAL + recovery** | 1074→ | mode NORMAL, battery→`market`, shed→0; later SoC recharges 20%→70%→90% | GRID_OP blue, flow lines restored |

**Both layers moved together** — this is the bar, and it passes. The system also
correctly reflected an **externally**-induced CRITICAL (kill sent over a direct WS
client) — the browser rendered OFFLINE/red without any local action, proving the UI
faithfully renders the broadcast rather than local optimism.

## 4. Permutation matrix

| # | Permutation | Result | Evidence |
|---|---|---|---|
| 4A-1 | Rapid Kill ×4 | **FAIL → D2** | 4 fast clicks produced **no** CRITICAL in 82 ticks. Single clicks work; rapid clicks drop the command (race). |
| 4A-2 | Kill↔Restore cycles | **PASS (×2)** | 2 full cycles clean; each returned to `market`, shed→0, ALL_CLEAR fired. (Not ×3 — the ~15-tick control latency makes cycles slow; 2 were enough to show repeatability.) |
| 4A-3 | Kill near demand peak | **PASS (partial)** | The main arc kill landed at 11:30 with solar ~79kW and load ramping; critical load handled via grid-forming until SoC floor, then honest unmet. |
| 4A-4 | Reload mid-sim | **PASS** | Reload reconnected, scene re-rendered, live values resumed; only benign THREE.Clock warning. |
| 4A-5 | Reload during alert | **PASS (partial)** | Reload during a fault recovered to the true current state (not a stale alert, not a crash). |
| 4A-6 | Window resize 699→1280 | **PASS** | Layout reflows: stacked at narrow width, proper left-scene / right-sidebar control-room layout at 1280×800. Canvas resizes; no break; no WebGL context-lost; no console errors. |
| 4A-7 | Second tab / multi-client | **PASS (by equivalent evidence)** | Throughout the audit, the WS logger + browser + direct-WS clients all observed **identical** frames concurrently (server broadcasts to all). A literal 2nd tab was not opened. |
| 4A-8 | Low-power toggle | **PASS** | Toggled on→off; scene stayed legible, no crash, data still correct. |
| 4A-9 | Long soak (~18 min) | **PASS (no FPS/mem instrumentation)** | Ran ~18 min across many sim-days; no value freeze, no console-error accumulation, forecast stayed accurate. FPS/memory not numerically profiled — see §7 recipe. |
| 4A-10 | Idle then interact | **UNVERIFIED** | Not run. Recipe in §7. |
| 4B-11 | Backend restart | **PASS (data) → D4** | On WS close UI shows "Waiting for the first telemetry frame…" (honest, **not** a zombie). But it does **not auto-reconnect** when the backend returns — stuck until manual reload. Reload then fully recovers. |
| 4B-12 | Broker (Mosquitto) drop | **UNVERIFIED** | Not run. Recipe in §7. |
| 4B-13 | Battery depletion | **PASS** | During sustained CRITICAL the battery drained 70%→**20.0% floor**, stopped (never negative), price went to null/no-clear, and **unmet_kw reported honestly** (never faked served power). |
| 4B-14 | High vs low SoC behavior | **PASS (observed)** | Distinct, real behavior by SoC: **90.6%** → battery discharges 24.7kW into market (teal flow); **70%** → holds (deadband, flow 0); **20%** → at floor, refuses to discharge, reports unmet. Proves degradation-priced two-sided market is live. |
| 4B-15 | Ridge drift / re-anchor | **PASS** | Condition number climbed 50k→37M over the run, then **re-anchored back to ~346** (cond reset observed live at recovery). Forecast stayed accurate throughout — **no garbage drift**. |
| 4B-16 | Real-CSV data path | **PRESENT** | Profiles config has a CSV source; curves render as realistic daily solar/load shapes. |
| 4B-17 | Network throttling | **UNVERIFIED** | Not run. Recipe in §7. |

## 5. Browser-specific failure hunt (§5)

- **UI lying (rendered ≠ stream):** **None found.** Three exact cross-checks
  matched. The one initial suspicion ("price n/a" vs logged 0.020) was resolved: at
  that tick the stream genuinely had `clearing_price=null`, and the UI **correctly**
  maps null→"n/a". UI is faithful, including for null fields and externally-induced
  state.
- **Zombie state (stale-as-live):** **Not present.** On disconnect the UI drops to a
  no-data screen rather than pretending the last frame is live.
- **Console errors / React warnings / WebGL context-lost:** **None** across cold
  load, the full arc, resize, and reconnect. Only a benign `THREE.Clock deprecated`
  warning (Three.js internal), repeated once during a brief Canvas remount burst.
- **Race on rapid input:** **Found (D2)** — rapid Kill clicks drop the command.
- **Memory/FPS decay:** none observed over ~18 min, but not numerically profiled.
- **Layout break (resize):** none.
- **Self-heal visual-only or data-only:** the heal moves **both** layers together
  (good), **except** the alert-banner text, which is visually stale (D1).

## 6. Defect list (prioritized)

**Blocks-polish for the demo (fix before showing):**

- **D1 [HIGH] — Alert-banner text is stale during CRITICAL.** While `mode` is
  CRITICAL, the status banner keeps reading *"NORMAL: Market and physical
  constraints are steady"* (only its border turns red). Confirmed 3×.
  **Root cause:** the WS `alerts` array is a **one-tick transient** — it is populated
  only on the transition tick (CRITICAL / ALL_CLEAR) and is `[]` for the entire
  sustained CRITICAL period. The mode chip reads `mode` directly (correct); the
  banner text falls back to the NORMAL copy when `alerts` is empty.
  **Smallest fix:** drive the banner text from `frame.mode` (and/or a latched
  "current alert"), not from the transient `alerts` array — or have the backend keep
  the active alert in `alerts` for the duration of the state rather than one tick.

- **D2 [MED] — Rapid clicks on Kill drop the command.** 4 fast clicks → 0 effect
  (no CRITICAL in 82 ticks), whereas a single click reliably works. A race in the
  button → WS-send path swallows the command under rapid input.
  **Smallest fix:** ensure each click enqueues an independent send (and/or debounce
  to exactly one guaranteed send); verify the socket is OPEN before `send`.

- **D3 [MED] — Browser control latency ~15–18 ticks slower than a direct WS client.**
  A **direct** WS `kill` stops the solar agent ~immediately (CRITICAL then follows
  only the expected ~12-tick heartbeat-detection window). The **browser button**
  didn't stop the agent for ~19 ticks (CRITICAL at +29). So the extra delay is in the
  **frontend → server** delivery, not backend chaos handling. For a live demo, "click
  and nothing happens for ~15s" reads as broken.
  **Smallest fix:** investigate the real-mode `stream.ts` send path / server
  client-message handling for buffering; confirm the chaos frame is sent on click,
  not on a tick/animation boundary.

- **D4 [MED] — No WebSocket auto-reconnect.** `frontend/src/stream.ts` opens the
  socket once; on `close` it only sets a status string ("Disconnected from …") with
  **no retry**. After any backend hiccup the dashboard is stuck on "Waiting for the
  first telemetry frame…" until a manual reload.
  **Smallest fix:** add a reconnect loop with backoff in `stream.ts` (mirror the
  trivial loop the audit logger used); and show a visible "reconnecting…" indicator
  instead of the cold-start "first frame" copy.

**Low / notes:**

- **D5 [LOW] — One-tick stale market flow at the dusk transition.** At the moment
  solar output crosses to 0, a single frame can still show a `flows` entry sourced
  from `PV_01` (cached `market/clearing`) while the PV node already reads 0. Self-
  corrects next tick. Cause: `market/clearing` and `node/PV_01/state` are cached
  independently in the superset-frame assembly.
- **D6 [INFO] — `served_kw` semantics.** In NORMAL mode `served_kw` (microgrid-
  cleared) can be below `demand_kw` with `shed_kw=0` (feeder import covers the gap),
  and can briefly exceed demand during battery charging. Contract-consistent but
  worth a one-line doc so it isn't misread as an accounting bug.
- **D7 [LOW] — Canvas remount burst.** A short burst (~8 Canvas mounts in ~1s,
  visible as repeated `[vite] connecting/connected` + `THREE.Clock`) occurred once
  after a reload, alongside a flurry of server "connection open" log lines. No crash,
  no context-lost; likely a reconnect/StrictMode cascade. Worth a glance.

## 7. Manual-verify recipes (items not driven here)

- **4A-10 Idle then interact:** background the tab 60s, return, click Kill. *Watch:*
  WS still live (frames advancing) and the kill lands. *Expect:* responsive, not a
  frozen/throttled socket.
- **4B-12 Broker drop:** `brew services stop mosquitto`, watch ~10s, then
  `brew services start mosquitto`. *Watch:* agents stall, **no NaN/garbage rendered**;
  on return the sim resumes (note: with D4, the frontend will need a reload).
- **4B-17 Network throttling:** DevTools → Network → Slow 3G with the WS open.
  *Expect:* graceful lag, no crash, no stale-but-pretending UI.
- **4A-9 FPS/memory soak (numeric):** DevTools Performance monitor, leave 10+ min.
  *Watch:* FPS steady, JS heap not climbing unbounded, no Three object leak.

## 8. Honest unknowns

- FPS/memory were eyeballed over ~18 min (stable) but **not numerically profiled**.
- Broker-drop, network-throttling, and idle-then-interact were **not executed** (see
  §7 recipes).
- The browser-control latency/race (D2/D3) was characterized empirically (browser vs
  direct-WS) but the exact line in `stream.ts` / server client-handling responsible
  was not pinpointed (frontend is read-only for this auditor).

## 9. What the auditor changed

Nothing in `backend/`, `frontend/`, or `CONTRACTS/`. Only `/tmp` harnesses
(`ws_logger.py`, direct-WS probes) and this vault report + Status update. Backend was
restarted once (deliberate, for the reconnect test) and left running healthy.
