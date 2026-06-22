# 2026-06-21 E2E Browser Demo Audit - Codex

Verdict: **PASS-WITH-CAVEATS**.

The real local stack came up and the core v1 demo works in Meet's Chrome against the live WebSocket stream. The Kill-Solar arc was observed end to end with screenshots and WebSocket cross-checks: NORMAL -> Kill -> CRITICAL -> PV offline -> battery grid-forming -> SoC floor and honest unmet -> Restore -> ALL_CLEAR/NORMAL. Caveats are mostly unrun destructive/network permutations and one machine/tooling limitation: Chrome control became unresponsive during a long idle probe, so that item is marked UNVERIFIED instead of guessed.

## Bring-Up

| Component | Result | Evidence |
|---|---:|---|
| Mosquitto | PASS | Existing process `/usr/local/opt/mosquitto/sbin/mosquitto -c /usr/local/etc/mosquitto/mosquitto.conf`. |
| Backend sim + WS | PASS | Started `backend/main.py`; server logged `ws://localhost:8765`. |
| Frontend | PASS | Started Vite at `http://127.0.0.1:5173/` with `VITE_OHMIC_STREAM=real`. |
| Raw WS contract smoke | PASS | `raw_frame_initial.json`: tick 85, `mode`, `nodes`, `market`, `forecast`, and `alerts` present. |

Evidence folder:

```text
vault/Screenshots/2026-06-21-e2e/
```

Raw frame logs:

- `raw_frame_initial.json`
- `ws_frames.jsonl`
- `ws_frames_after_restart.jsonl`

## Core Demo Result

| Stage | Result | Evidence |
|---|---:|---|
| Cold load | PASS | `01-cold-load.png`; tick 353 UI showed NORMAL, PV 39.8 kW, BESS 78.7%, load served 28.8 kW. WS tick 353: PV 39.849, BESS 78.7%, served 28.769, price 0.020. |
| 3D scene | PASS | `01-cold-load.png`; canvas rendered with labeled PV/BESS/LOAD/GRID_OP and visible flow line. |
| Console | PASS-WITH-NOTES | No uncaught errors observed. Dev-mode console showed React DevTools info, Vite debug, and `THREE.Clock` deprecation warning. |
| Daytime steady state | PASS | `05-day-steady-a.png`, `06-day-steady-b.png`, `07-day-steady-c.png`; WS ticks 424, 429, 434 show price 0.020, feeder flow 35.38 -> 56.57 -> 60.0 kW, curtailment 0 -> 0 -> 8.96 kW. UI panel matched rounded values. |
| Forecast sanity | PASS | `08-forecast-chart.png`; WS tick 454 actual 100.92 kW, predicted 99.28 kW, warm=true, cond 21,597. |
| Kill click immediate | PASS | `09-kill-click-immediate.png`; clicked from tick 475, immediate tick 479 remained NORMAL as expected while heartbeat detection caught up. |
| CRITICAL alert/state | PASS | `10-critical-alert.png`; CRITICAL at tick 493, 18 ticks after click. WS transition alert was present at tick 489: `PV_01 missed 3 heartbeats`. Screenshot tick 493: PV offline, BESS grid_forming, load shed. |
| Load shed | PASS | `10-critical-alert.png`; WS tick 493 demand 48.35, served 14.69, shed 33.66. UI banner: `33.7 kW shed`. |
| Battery grid-forming | PASS | `10-critical-alert.png`; WS tick 493 BESS mode `grid_forming`, flow 14.69 kW, SoC 53.0%. |
| Battery floor + honest unmet | PASS | `11-battery-floor-unmet.png`; WS tick 513 BESS SoC 20.0%, flow 0, BESS unmet 42.21 kW, load served 0, shed 123.68. UI did not fake served power. |
| Restore / recovery | PASS | `12-restore-recovered.png`; restore clicked tick 534, recovered NORMAL tick 543. ALL_CLEAR frame appeared at tick 541. WS tick 543 PV alive true, BESS market, load shed 0. |

## Permutation Matrix

| # | Permutation | Result | Evidence |
|---:|---|---:|---|
| 4A-1 | Rapid Kill click | PASS | `13-rapid-kill.png`; four Kill clicks from tick 556 reached CRITICAL at tick 576. No duplicate crash/stuck state observed. |
| 4A-2 | Kill then immediately Restore repeated 3x | PASS | `14-kill-restore-cycles.png`; all 3 cycles returned to NORMAL, final tick 642 NORMAL/PV alive. |
| 4A-3 | Kill during forecast spike | PASS | Core kill happened during high/rising load window; `11-battery-floor-unmet.png` demonstrates worst-case shed/unmet honesty at high demand. |
| 4A-4 | Reload mid-sim steady | PASS | `15-reload-steady.png`; reload recovered live NORMAL at tick 660. |
| 4A-5 | Reload during active alert | PASS | `16-reload-critical.png`; reload during CRITICAL recovered true CRITICAL state, PV offline, banner CRITICAL. |
| 4A-6 | Window resize / fullscreen | UNVERIFIED | Chrome-control API available in this turn did not expose a safe window resize/fullscreen control; manual recipe below. |
| 4A-7 | Second tab | PASS | `18-second-tab.png`; second localhost tab rendered live NORMAL stream. Tick delta was due sequential read timing, not state divergence. |
| 4A-8 | Low-power toggle | PASS | `17-low-power-toggle.png`; checkbox changed true -> false, scene stayed live, WS tick matched mode NORMAL. |
| 4A-9 | Browser-side long soak 5+ min | UNVERIFIED | Attempted long idle/soak; browser-control kernel timed out and reset. Do not claim pass. Manual recipe below. |
| 4A-10 | Idle then interact | UNVERIFIED | Same timeout interrupted the idle-then-Kill probe before evidence could be captured. Manual recipe below. |
| 4B-11 | Backend restart while frontend open | PASS | `19-backend-down.png`: Stream offline/reconnecting, not zombie. `20-backend-reconnected.png`: same open page reconnected to live tick 116 after backend restart. |
| 4B-12 | Mosquitto drop | UNVERIFIED | Not run; stopping broker risks disturbing local services and needs a separate controlled window. Manual recipe below. |
| 4B-13 | Battery depletion run | PASS | `11-battery-floor-unmet.png`; battery stopped at 20% floor, unmet reported honestly. |
| 4B-14 | High-SoC vs low-SoC Kill comparison | PARTIAL | Higher SoC kill: tick 493 SoC 53%, flow 14.69. Low SoC floor: tick 513 SoC 20%, flow 0, unmet. A true 90% kill was not captured. |
| 4B-15 | Ridge drift / re-anchor | PARTIAL | Forecast stayed bounded and accurate in observed run; cond rose from 8k to 728k before restart. No re-anchor observed in this run. Earlier Claude audit reported re-anchor; this run did not last long enough. |
| 4B-16 | Real-data path | PASS | Active `backend/config.yaml` uses `profiles.source: csv`; observed curves were non-flat, daylight/peak shaped, and demo ran. |
| 4B-17 | Network throttling | UNVERIFIED | Chrome-control API in this turn did not expose network throttling safely. Manual recipe below. |

## Failure-Hunt Findings

- UI lying: **None found in captured ticks.** UI rounded values matched the WS payload for PV, battery SoC, load served/shed, clearing price, feeder flow, and curtailment.
- Zombie state: **PASS.** Backend down screenshot showed `Stream: offline ... reconnecting`; UI did not pretend the last frame was live.
- Console errors: **PASS-WITH-NOTES.** No uncaught errors captured. Notes: React DevTools info, Vite debug, and a Three.Clock deprecation warning.
- Memory/FPS decay: **UNVERIFIED.** Long soak was interrupted by browser-control timeout.
- Race on rapid input: **PASS.** Rapid Kill and repeated Kill/Restore recovered cleanly.
- Background/idle responsiveness: **UNVERIFIED.** Timeout interrupted the probe.
- Layout break: **UNVERIFIED for resize/fullscreen** in this run.
- Self-heal visual-only/data-only mismatch: **PASS.** Scene, banner, metrics, and WS payload moved together in the captured arc.

## Defect List

No blocks-demo defects were reproduced after the latest frontend fixes.

Polish / follow-up:

1. **P2 - Three.js deprecation warning.** Console warning: `THREE.Clock: This module has been deprecated. Please use THREE.Timer instead.` This is not a runtime failure, but it is visible in dev console.
2. **P3 - Command-to-CRITICAL delay is longer than a literal 3 ticks.** Kill clicked at tick 475; CRITICAL screenshot at tick 493; transition alert frame tick 489. This includes command delivery plus configured operator grace/heartbeat threshold. It is watchable and correct, but note the delay in demos.
3. **P3 - Full 5+ minute soak not completed by Codex Chrome control.** Needs human/stronger-machine pass for memory/FPS profiling.

## Manual-Verify Recipes

4A-6 Resize/fullscreen:

```text
Command: keep `make run` and `VITE_OHMIC_STREAM=real npm run dev -- --host 127.0.0.1 --port 5173` running; open http://127.0.0.1:5173 in Chrome.
Watch: resize window small -> large and enter fullscreen.
Expected: canvas resizes, panels remain readable, no console errors or WebGL context loss.
```

4A-9 Long browser soak:

```text
Command: open Chrome DevTools Performance/Memory on http://127.0.0.1:5173 and leave it live for 5-10 minutes.
Watch: FPS, JS heap, console, tick advancement, and flow lines.
Expected: ticks continue, no accumulating console errors, no unbounded memory climb, no frozen numbers.
```

4A-10 Idle then interact:

```text
Command: background the tab for 60-120 seconds, return, then click Kill Solar.
Watch: stream status and CRITICAL transition.
Expected: stream is live or clearly reconnecting; Kill still triggers CRITICAL and grid-forming.
```

4B-12 Mosquitto drop:

```text
Command: stop Mosquitto briefly, then restart it.
Watch: backend logs, frontend Stream status, and whether values become NaN/garbage.
Expected: clear disconnected/reconnecting state or controlled backend failure; no fake-live zombie UI.
```

4B-14 High-SoC kill:

```text
Command: let BESS charge near 90%, then click Kill Solar.
Watch: BESS flow and load served versus low-SoC/floor behavior.
Expected: high SoC covers more critical load; low SoC reports unmet honestly.
```

4B-15 Ridge re-anchor:

```text
Command: run backend + frontend for a long soak; watch backend logs for `ridge re-anchored`.
Watch: forecast actual vs predicted and `forecast.cond` in the UI.
Expected: cond remains bounded or re-anchors before predictions drift into garbage.
```

4B-17 Network throttling:

```text
Command: Chrome DevTools -> Network -> Slow 3G while dashboard is live.
Watch: Stream status, console, and whether displayed values freeze as if live.
Expected: graceful lag/reconnect indication; no crash and no stale-as-live state.
```

## Honest Unknowns

- Full resize/fullscreen behavior was not driven because the Chrome-control API exposed to this run did not provide safe window management.
- Long soak, memory/FPS profiling, background-tab interaction, Mosquitto drop, and network throttling are not claimed as passes.
- The active git project vault is outside this turn's writable root (`/Users/meetbhadra/Projects/microgrid/vault`). This report was saved in the writable `/Users/meetbhadra/Ohmic/vault`; mirror it to the active vault when filesystem permissions allow.
