# Microgrid Project — Vault Home

This vault is auto-populated by the two build agents (Claude Code + Codex).
You don't type here. You read here.

Start with **[[Status]]** every time you come back.

- **[[Status]]** — current build state (owned by Claude)
- **Agent Logs/** — what each agent did, per task
- **Reports/** — readable Codex build/review reports
- **Decisions/** — one note per architectural decision
- **Requests/** — Codex asks Claude for backend/contract changes here
- **CONTRACTS notes/Contract Lock** — serializes shared-contract changes

## Latest Codex Notes

- [[Reports/Codex Frontend Dashboard]]
- [[Reports/Codex Backend Review Fixes]]
- [[Decisions/0004-frontend-stream-and-low-power]]
- [[Decisions/0005-mqtt-run-isolation]]
- [[Requests/2026-06-21-websocket-run-id-followup]]

## The two-layer agent rule (don't forget)
- Build agents = Claude Code + Codex (they write code)
- Sim agents = Battery (A), Load (B), Solar, Grid Operator (inside the sim)
