# MQTT Topics — v1 (frozen contract)

> Sole author: Claude Code (backend). Codex consumes read-only.
> To change anything here, follow the Contract Lock protocol
> (`vault/CONTRACTS notes/Contract Lock.md`). Do not depend on a field while the
> latest lock line is `LOCKED`.

Broker: local Mosquitto, `localhost:1883`, no auth (sim only, single machine).
All payloads are JSON (UTF-8). Every message carries a `schema_version` (int) and
the originating `tick` (int). See `message_schemas.md` for payload shapes.

`<id>` is a node id from the fixed v1 set: `PV_01` (solar), `BESS_01` (battery),
`LOAD_CAMPUS` (load). The Grid Operator is `GRID_OP` (does not publish node state).

| Topic                  | Publisher          | Subscribers        | QoS | Retain | Purpose |
|------------------------|--------------------|--------------------|-----|--------|---------|
| `grid/tick`            | Clock              | all agents, WS     | 0   | no     | Heartbeat of the sim. Drives every agent. Loss recovered next tick. |
| `node/<id>/state`      | each node          | Operator, WS       | 0   | yes    | Full node state snapshot, published every tick the node is alive. Retained so late subscribers get last value. |
| `node/<id>/heartbeat`  | each node          | Operator           | 0   | no     | Lightweight liveness ping, published every tick. **Separate from state** so "alive but silent on state" is still detectable. Absence is what triggers fault detection. |
| `market/bids`          | Load (`LOAD_CAMPUS`) | Operator         | 1   | no     | Buy orders. QoS 1 — an unheard bid distorts clearing. |
| `market/asks`          | Battery, Solar     | Operator           | 1   | no     | Sell orders. QoS 1. |
| `market/clearing`      | Operator (`GRID_OP`) | all agents, WS   | 1   | yes    | Auction result + curtailment. QoS 1, retained (last clearing is authoritative). |
| `grid/alert`           | Operator (`GRID_OP`) | all agents, WS   | 1   | yes    | Fault/recovery alerts (CRITICAL / ALL_CLEAR). QoS 1 — must never drop. Retained so the current grid mode is always queryable. |
| `chaos/command`        | Chaos module       | targeted node      | 1   | no     | Kill/restore a node (operator-induced fault). QoS 1. |

## Per-tick ordering (within one `tick`)
1. Clock publishes `grid/tick`.
2. Each alive node publishes `node/<id>/heartbeat` then `node/<id>/state`.
3. Load publishes `market/bids`; Battery + Solar publish `market/asks`.
4. Operator clears → checks feasibility → publishes `market/clearing`, then runs
   heartbeat detection and may publish `grid/alert`.
5. WebSocket server assembles the latest-value cache and broadcasts one frame
   (see `websocket_api.md`).

Agents are **edge-triggered on `grid/tick`** — they never act on wall-clock timers.

## Sign convention (frozen)
Power in kW. **Generation / discharge is positive; load draw is negative; battery
charge is negative, discharge is positive.** Flows in `market/clearing` are
directed `from`→`to` with a positive `kw` magnitude.
