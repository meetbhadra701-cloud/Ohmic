# WebSocket API — v1 (frozen contract)

> Sole author: Claude Code. Codex consumes read-only. Change via Contract Lock.
> **This is the integration seam between backend and frontend.** The backend
> broadcasts exactly the frame below once per `grid/tick`. Field names here ARE
> the contract — renaming one is a Contract Lock event.

## Connection
- URL: `ws://localhost:8765`  (configurable in `backend/config.yaml` → `websocket.port`)
- Protocol: server pushes; client does not need to send anything to receive frames.
- On connect, the server immediately sends the latest cached frame (so a late
  client is not blank until the next tick), then one frame per tick thereafter.
- Encoding: JSON text frames, UTF-8.

## Optional client → server commands (v1)
The frontend's "Kill Solar" / "Restore Solar" control sends a JSON text frame the
server relays onto `chaos/command`:
```jsonc
{ "type": "chaos", "target": "PV_01", "action": "kill" }   // action: "kill" | "restore"
```
The server validates `target` against the known node set and ignores unknown
commands. Any resulting fault/recovery shows up in the next frame's `alerts`.

## Server → client frame (one per tick)
```jsonc
{
  "schema_version": 1,
  "tick": 124,
  "sim_time": "14:32",            // HH:MM sim clock
  "day_phase": 0.604,             // 0.0–1.0 through the sim day
  "mode": "NORMAL",               // "NORMAL" | "CRITICAL"  (grid-wide health)

  "nodes": {
    "PV_01": {
      "type": "solar",
      "output_kw": 70.0,          // >=0 current generation
      "alive": true,              // false once killed / missing heartbeats
      "health": "nominal"         // "nominal" | "degraded" | "fault"
    },
    "BESS_01": {
      "type": "battery",
      "soc": 0.825,               // 0.0–1.0
      "soc_percent": 82.5,        // convenience: soc*100, for display
      "flow_kw": -45.0,           // signed: + discharge, - charge
      "max_discharge_kw": 50.0,
      "mode": "market",           // "market" | "grid_forming"
      "ask_price_usd_kwh": 0.18,  // null while grid_forming
      "unmet_kw": 0.0,            // >=0 (grid_forming shortfall)
      "health": "nominal"
    },
    "LOAD_CAMPUS": {
      "type": "load",
      "demand_kw": 100.0,         // >=0 total demand
      "critical_kw": 40.0,        // >=0 must-serve
      "served_kw": 100.0,         // >=0 delivered
      "shed_kw": 0.0,             // >=0 non-critical shed
      "health": "nominal"
    }
  },

  "market": {
    "clearing_price_usd_kwh": 0.27,   // null if no trade this tick
    "flows": [                         // directed power flows to animate
      { "from": "BESS_01", "to": "LOAD_CAMPUS", "kw": 45.0, "curtailed_kw": 0.0 }
    ],
    "unmet_kw": 0.0,
    "surplus_kw": 0.0,
    "curtailed_kw": 0.0,               // total trimmed by line feasibility this tick
    "per_line_flow_kw": { "FEEDER_1": 45.0 }   // line loading, for capacity bars
  },

  "forecast": {
    "predicted_demand_kw": 118.0,      // Load's ridge forecast for next horizon
    "horizon_ticks": 5,
    "actual_demand_kw": 100.0,         // current realized, to chart forecast vs actual
    "cond": 1240.5,                    // ridge P-matrix condition number (health telemetry)
    "reanchor_count": 0,               // times the ridge re-anchored (rail-2 fires)
    "warm": true                       // false during cold-start baseline period
  },

  "alerts": [                          // active + just-transitioned alerts this tick
    // { "level": "CRITICAL", "type": "SOLAR_LOSS", "detail": "PV_01 missed 3 heartbeats", "tick": 130 }
  ]
}
```

## Guarantees for the frontend
- The frame is a **superset**: every value the UI needs to render the scene,
  panels, forecast chart, capacity bars, and alert banner is present each tick.
- `nodes` always contains all three v1 node ids; a killed node reports
  `alive:false` (and stale `output_kw`/last-known values) rather than disappearing.
- `mode` flips to `"CRITICAL"` on the same frame the CRITICAL alert appears, and
  back to `"NORMAL"` on the ALL_CLEAR frame.
- `clearing_price_usd_kwh` and `ask_price_usd_kwh` are `null` (not `0`) when no
  price applies, so the UI can distinguish "free" from "n/a".
- Numbers are plain JSON numbers (not strings). Missing optional data is `null`.

## Low-power mode (frontend hint, not enforced by backend)
The 8 GB Intel Air is a target machine. The backend cadence is configurable, but
the frontend should offer a low-power toggle that disables expensive WebGL effects
independently — the frame shape is identical in both modes.
