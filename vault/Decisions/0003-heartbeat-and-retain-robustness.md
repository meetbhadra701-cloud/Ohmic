# Decision: Heartbeat reliability, fault-detection grace, and retained-message hygiene
- Date: 2026-06-20
- Context: Wiring self-healing (Step 5) exposed several startup/timing fragilities
  that produced spurious CRITICAL alerts and cross-run contamination. Recording the
  fixes so they are not undone.
- Decisions:
  1. **Heartbeats are QoS 1.** They were QoS 0 (at-most-once); under the startup
     message burst some were dropped, and 3 dropped in a row tripped a false
     SOLAR_LOSS. Liveness signals must be reliable → QoS 1.
  2. **Fault detection uses a larger grace than market settlement.** Market clears
     at tick T-2; liveness is evaluated at tick T-4 (`HEARTBEAT_GRACE=4`). Beats can
     arrive a little late on a shared, unordered MQTT stream; a false "missed beat"
     is far worse than a 2-tick-later fault detection.
  3. **No fault before first life.** The operator records each node's first-seen
     tick and never evaluates liveness for ticks at or before it — so a node that
     connects a few ticks late is not mistaken for a dead node.
  4. **Retained-message hygiene.** `grid/alert`, `market/clearing`, and node state
     are retained (so a late-joining frontend gets current state). But agents and
     check scripts must IGNORE retained frames on connect — otherwise a prior run's
     retained CRITICAL would flip the battery into grid-forming at startup. The Bus
     now exposes `Message.retain`; `BaseAgent.run` and the check observers skip
     retained messages. (The WebSocket server is the deliberate exception: it WANTS
     retained state to seed late clients, and builds its own cache.)
- Why: the protocol must be robust on a single-process asyncio sim where 6 MQTT
  clients share one event loop and connect/burst at startup. With these four fixes
  the full heal transcript (kill -> CRITICAL -> shed + grid-forming -> ALL_CLEAR ->
  market) is deterministic across repeated runs.
- Revisit when: agents move to separate processes, or tick periods become large
  enough (>=0.5s) that the graces could shrink.
