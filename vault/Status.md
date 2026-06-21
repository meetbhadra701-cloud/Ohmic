# Status (owned by Claude Code — Codex: do not edit)

_Claude updates this after each build step. Human reads it first._

## v1 Audit verdict — 2026-06-21: **DONE-WITH-CAVEATS**
Full slice runs live (real broker + WS); self-heal arc proven through the real
Kill-Solar WebSocket path; 46/46 tests, all 5 gates green; math + contract real.
Caveats are docs/polish only — see `Decisions/2026-06-21-v1-verification-audit.md`.
Top fix: add run instructions to `README.md` (G1). Visual 3D render still needs a
manual eyes-on pass on the stronger Mac (frontend builds clean; pixels unverified).

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
