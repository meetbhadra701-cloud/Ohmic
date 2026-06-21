# Status (owned by Claude Code — Codex: do not edit)

_Claude updates this after each build step. Human reads it first._

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
- [ ] Frontend scaffold + mock stream
- [ ] 3D scene + data binding + flow lines
- [ ] Panels + alerts banner
- [ ] Kill-Solar control + self-heal visuals
- [ ] Real socket swap + polish

## Current blockers
- (none) — Codex was blocked on `CONTRACTS/websocket_api.md`; now published.

## In progress
- Frontend steps (Codex): scaffold + mock stream, 3D scene, panels, Kill-Solar control.
