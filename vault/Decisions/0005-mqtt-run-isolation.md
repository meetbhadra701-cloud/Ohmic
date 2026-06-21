# Decision 0005 — MQTT Run Isolation

Date: 2026-06-21
Owner: Codex

## Decision

Every MQTT message now carries a `run_id`, and every bus can filter inbound messages to the active run.

## Rationale

Mosquitto retained messages are useful for late subscribers, but they caused stale frames from prior runs to contaminate tests and agent state.

Observed symptoms:

- tick tests saw retained state for nodes that were not part of the test
- market checks could consume stale clearings
- parallel or repeated runs could collide on static client ids

## Details

- `Bus(..., run_id=...)` stamps `run_id` into published payloads.
- `Bus.messages()` ignores messages whose `run_id` does not match.
- client ids include a run-specific suffix.
- gate scripts create unique run ids with `new_run_id(...)`.
- `FakeBus` mirrors the same run filtering for deterministic tests.

## Consequences

- Retained MQTT topics remain usable.
- Repeated test runs are isolated.
- Step 6 WebSocket code must preserve or intentionally bridge the active run id when sending chaos commands.

