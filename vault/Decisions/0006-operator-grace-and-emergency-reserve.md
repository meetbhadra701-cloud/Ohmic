# 0006 - Operator Grace And Emergency Reserve

Date: 2026-06-21
Owner: Codex
Status: Accepted

## Decision

- Normal market battery discharge preserves the emergency reserve around `TARGET_SOC`.
- Pending market sell offers count against future offers until their clearing tick is observed.
- During CRITICAL solar loss, the battery bypasses the auction and directly grid-forms to the latest critical load.
- Operator settlement and heartbeat grace are configurable:
  - live demo default: 8 ticks
  - fast verification scripts: 32 ticks

## Why

The backend could pass schema checks while failing the demo story: the battery could sell down toward the SoC floor before a fault, then have no visible emergency response. Fast MQTT gates also showed that 8 ticks of grace is too short when tick periods are 0.1-0.2 seconds.

## Consequences

- The live UI remains responsive after Kill Solar.
- Fast gates wait long enough for complete books and heartbeat buckets.
- The emergency path proves self-healing through state changes, not through optimistic frontend animation.
