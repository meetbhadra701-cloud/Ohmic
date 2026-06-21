# Status (owned by Claude Code — Codex: do not edit)

_Claude updates this after each build step. Human reads it first._

## Build steps (backend §6 / frontend §5)
- [x] CONTRACTS published (Claude — blocks Codex until done) — v1, 2026-06-20
- [x] Backend skeleton + MQTT smoke test — 2026-06-20, smoke test green
- [ ] Clock + bus + dummy nodes
- [ ] Physical models (solar/load, synthetic)
- [ ] Math: degradation cost, recursive ridge (+guards), CDA + feasibility
- [ ] Market loop steady-state
- [ ] Self-healing protocol
- [ ] WebSocket server (integration seam)
- [ ] Real-data CSV swap
- [ ] Frontend scaffold + mock stream
- [ ] 3D scene + data binding + flow lines
- [ ] Panels + alerts banner
- [ ] Kill-Solar control + self-heal visuals
- [ ] Real socket swap + polish

## Current blockers
- (none) — Codex was blocked on `CONTRACTS/websocket_api.md`; now published.

## In progress
- Step 1: clock + bus + dummy nodes (prove tick sync + pub/sub plumbing).
