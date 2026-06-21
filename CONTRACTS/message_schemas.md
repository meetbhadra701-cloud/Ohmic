# Message Schemas — v1 (frozen contract)

> Sole author: Claude Code. Codex consumes read-only. Change via Contract Lock.

All payloads are JSON objects. Common envelope fields appear on **every** message:

| Field            | Type   | Units | Notes |
|------------------|--------|-------|-------|
| `schema_version` | int    | —     | `1` for v1. Bump only via Contract Lock. |
| `tick`           | int    | ticks | Monotonic sim tick the message belongs to. |
| `run_id`         | string | —     | Unique sim-run identifier used to ignore stale retained MQTT frames. |

Power is **kW**, energy **kWh**, price **USD/kWh**, SoC a **fraction 0.0–1.0**
(the WebSocket frame also exposes `soc_percent` for display convenience).
Sign convention per `mqtt_topics.md` (generation/discharge +, load/charge −).

---

## `grid/tick`  (Clock → all)
```jsonc
{ "schema_version": 1, "tick": 124,
  "sim_time": "14:32",        // HH:MM sim clock, derived from tick % ticks_per_day
  "day_phase": 0.604 }        // 0.0–1.0 fraction through the sim day (for irradiance)
```

## `node/<id>/state`  (each node → bus, retained)
Discriminated by `type`. Common: `node_id`, `type`, `tick`, `health`
(`"nominal" | "degraded" | "fault"`).

```jsonc
// solar
{ "schema_version":1, "tick":124, "node_id":"PV_01", "type":"solar",
  "output_kw": 70.0,          // >=0, current generation, capped by inverter_kw
  "alive": true,
  "health": "nominal" }

// battery
{ "schema_version":1, "tick":124, "node_id":"BESS_01", "type":"battery",
  "soc": 0.825,               // 0.0–1.0 state of charge
  "max_discharge_kw": 50.0,   // >=0
  "flow_kw": -45.0,           // signed: + discharge, - charge, 0 idle
  "mode": "market",           // "market" | "grid_forming"
  "ask_price_usd_kwh": 0.18,  // current marginal ask price (null when grid_forming)
  "unmet_kw": 0.0,            // >=0, demand it could not cover (grid_forming only)
  "health": "nominal" }

// load
{ "schema_version":1, "tick":124, "node_id":"LOAD_CAMPUS", "type":"load",
  "demand_kw": 100.0,         // >=0 total demand this tick (critical+non-critical)
  "critical_kw": 40.0,        // >=0 must-serve portion
  "served_kw": 100.0,         // >=0 actually delivered
  "shed_kw": 0.0,             // >=0 non-critical demand shed
  "health": "nominal",
  "predicted_demand_kw": 118.0,
  "forecast_horizon_ticks": 5,
  "ridge_cond": 1240.5,
  "ridge_reanchor_count": 0,
  "ridge_warm": true }
```

## `node/<id>/heartbeat`  (each node → bus)
```jsonc
{ "schema_version":1, "tick":124, "node_id":"PV_01" }
```
Absence for `miss_threshold` (default 3) consecutive ticks → Operator raises a
CRITICAL alert for that node.

## `market/bids`  (Load → Operator)
```jsonc
{ "schema_version":1, "tick":124, "agent_id":"LOAD_CAMPUS", "intent":"buy",
  "volume_kw": 45.0,          // >=0 quantity sought
  "max_price_usd_kwh": 0.40 } // willingness to pay (highest)
```

## `market/asks`  (Battery, Solar → Operator)
```jsonc
{ "schema_version":1, "tick":124, "agent_id":"BESS_01", "intent":"sell",
  "volume_kw": 60.0,          // >=0 quantity offered
  "min_price_usd_kwh": 0.18 } // reservation price (lowest acceptable)
```
Solar asks at/near `floor_price` (must-take generation); Battery asks at its
marginal degradation cost + margin.

## `market/clearing`  (Operator → all, retained)
```jsonc
{ "schema_version":1, "tick":124,
  "clearing_price_usd_kwh": 0.27,   // uniform price = last matched ask price; null if no trade
  "matches": [
    { "buyer":"LOAD_CAMPUS", "seller":"BESS_01",
      "kw": 45.0,                   // delivered kW after feasibility (financial match minus curtailment)
      "curtailed_kw": 0.0,          // >=0 amount trimmed by line-capacity feasibility
      "reason": null }              // e.g. "FEEDER_1 over rating" when curtailed_kw>0
  ],
  "unmet_kw": 0.0,                  // >=0 demand with no feasible+affordable supply
  "surplus_kw": 0.0 }               // >=0 offered supply left unsold
```
Settlement rule (frozen): trades settle on **delivered kW at the cleared price**.
Curtailment reduces delivered kW; `curtailed_kw` records the trim.

## `grid/alert`  (Operator → all, retained)
```jsonc
{ "schema_version":1, "tick":130,
  "level": "CRITICAL",        // "CRITICAL" | "ALL_CLEAR"
  "type": "SOLAR_LOSS",       // event class; "SOLAR_LOSS" in v1
  "detail": "PV_01 missed 3 heartbeats" }
```
ALL_CLEAR is published after the node resumes heartbeats for **≥2 consecutive
ticks** (anti-flap hysteresis).

## `chaos/command`  (Chaos → targeted node)
```jsonc
{ "schema_version":1, "tick":200, "target":"PV_01",
  "action":"kill" }           // "kill" | "restore"
```
