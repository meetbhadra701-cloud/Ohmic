# Status (owned by Claude Code — Codex: do not edit)

_Claude updates this after each build step. Human reads it first._

## Follow-up verification round + broker fix — 2026-06-21 (Claude)
Drove the 7 items the first browser audit left open. **6 PASS, 1 fix landed, 1 tooling-limited.**
- **FIXED [was a crash]:** dropping Mosquitto previously killed the whole backend
  (unhandled `MqttError`). Added bounded-backoff broker reconnect to `BaseAgent.run`,
  `Clock.run`, `WebSocketServer.run` + guarded the chaos relay. Backend now survives a
  broker outage and resumes (monotonic tick, no NaN). Verified: 46 pytest + 5 gates +
  live drop→recover.
- **Ridge re-anchor CONFIRMED** properly: live `forecast.reanchor_count` increments only
  via the watchdog; controlled real-sim harness fired it at cond>cond_max (cond→1.0,
  count++, logged). (Corrects the earlier "cond 37M→346" note below — that drop was a
  backend restart, not a verified watchdog event; cond 37M < 1e8 threshold.)
- **90% vs 25% SoC:** 7 GF ticks/~23 kWh vs 1 tick/~2 kWh, both stop at 0.20 floor — real.
- **Soak (5 min):** no memory leak (GC sawtooth ~48–105 MB); FPS median 38, no freezes.
- **Resize:** clean 699/1280/1400; narrow <~880px overflows (canvas min-width, frontend).
- **Idle 94s backgrounded:** WS stayed live (+93 ticks); post-idle Kill worked.
- **Network throttle:** not drivable with available tools (no CDP); recipe in vault.
Full detail: `Decisions/2026-06-21-e2e-browser-demo-audit.md` (§0).

## Codex E2E Browser Acceptance Test — 2026-06-21: **PASS-WITH-CAVEATS**
Codex operated the real local stack in Meet's Chrome and cross-checked rendered
values against live WebSocket frames. Core Kill-Solar demo passed end to end:
NORMAL -> CRITICAL -> PV offline -> BESS grid-forming -> load shed -> SoC floor
with honest unmet -> Restore -> NORMAL. Evidence report:
`Decisions/2026-06-21-e2e-browser-demo-audit-codex.md`; screenshots and WS logs:
`Screenshots/2026-06-21-e2e/`.

## v1 E2E Browser Demo verdict — 2026-06-21: **PASS-WITH-CAVEATS**
Operated the real running system in a real browser (Claude in Chrome). **3D scene
renders correctly — the prior "pixels unverified" unknown is now RESOLVED.** Rendered
numbers match the live WS stream tick-for-tick (3 exact cross-checks). Kill-Solar
self-heal arc observed live end-to-end with scene + numbers moving together
(CRITICAL → shed → grid-forming → SoC floor → honest unmet → ALL_CLEAR → market).
Ridge re-anchor fired live (cond 37M→346); battery floor + honest unmet confirmed.
Full report: `Decisions/2026-06-21-e2e-browser-demo-audit.md`.
**Original demo-polish defects:** D1/D2/D3/D4 were later fixed by Codex in
`9582cf8 fix browser e2e frontend caveats`. Current `frontend/src/App.tsx` drives
the CRITICAL banner from `frame.mode`, and `frontend/src/stream.ts` has reconnect
and queued command handling. Claude's follow-up note about D1 still being unfixed
was stale relative to the current frontend.

## v1 Verification Audit — 2026-06-21: **DONE-WITH-CAVEATS**
Full slice runs live (real broker + WS); self-heal arc proven through the real
Kill-Solar WebSocket path; 46/46 tests, all 5 gates green; math + contract real.
Caveats are docs/polish only — see `Decisions/2026-06-21-v1-verification-audit.md`.
Top fix: add run instructions to `README.md` (G1).

## Build steps (backend §6 / frontend §5)
- [x] CONTRACTS published (Claude — blocks Codex until done) — v1, 2026-06-20
- [x] Backend skeleton + MQTT smoke test — 2026-06-20, smoke test green
- [x] Clock + bus + dummy nodes — 2026-06-20, check_tick green (20 contiguous ticks)
- [x] Physical models (solar/load, synthetic) — 2026-06-20, 12 pytest green
- [x] Math: degradation cost, recursive ridge (+guards), CDA + feasibility — 2026-06-20, 34 pytest green (all 5 ridge rails exercised)
- [x] Market loop steady-state — 2026-06-20, check_market green (trades + curtailment + energy conservation, stable across runs)
- [x] Self-healing protocol — 2026-06-20, check_heal green (kill -> CRITICAL -> shed + grid-forming -> ALL_CLEAR -> market), stable across runs
- [x] WebSocket server (integration seam) — 2026-06-21, check_ws green (30 frames, all fields contract-compliant)
- [x] Real-data CSV swap — 2026-06-21, CSV profiles behind same signatures, all gates unchanged
- [x] Frontend scaffold + mock stream — audit-verified 2026-06-21 (contract-shaped mock w/ self-heal arc; `npm run build` clean)
- [x] 3D scene + data binding + flow lines — audit-verified (R3F Canvas + FlowLine/nodes in App.tsx; type-checks)
- [x] Panels + alerts banner — audit-verified (metric cards, forecast chart, alert banner present)
- [x] Kill-Solar control + self-heal visuals — code verified; live data arc proven via WS. **Visual render: confirm manually on stronger Mac.**
- [x] Real socket swap + polish — audit-verified (`VITE_OHMIC_STREAM=real` → live ws://localhost:8765)

## Current blockers
- (none.) Backend complete. Frontend complete pending one manual eyes-on render pass.

## Open caveats (from audit)
- G1 [docs]: `README.md` has no run instructions (steps only in vault). Highest-value fix.
- G2 [design]: grid-forming emergency supply bypasses the auction (server reconciles served/shed). Works; note for purity.
- G3 [coordination]: commit 632a37a crossed backend/frontend ownership boundary (no conflict).
- G4 [cosmetic]: type `forecast.cond` as nullable in frontend types.
