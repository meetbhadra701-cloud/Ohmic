# Decision: Freeze four contract spec-gaps in CONTRACTS v1
- Date: 2026-06-20
- Context: The build manual left four wire-level details ambiguous. Because Codex
  builds the frontend strictly against `CONTRACTS/`, these must be decided once
  and frozen, not left implicit, or backend and frontend will desync.
- Options considered:
  1. Clearing price: last matched ask price vs last matched bid vs midpoint.
  2. Curtailment settlement: settle on financially-matched kW vs delivered kW.
  3. Power sign convention: pick a direction for generation/load/charge.
  4. Heartbeat recovery: clear CRITICAL on 1 good beat vs N consecutive.
  5. Heartbeat channel: fold into `node/<id>/state` vs a dedicated topic.
- Decision:
  1. **Uniform clearing price = price of the last matched ask** (merit-order
     convention). All matches settle at this single price (not pay-as-bid).
  2. **Settle on delivered kW at the cleared price.** Feasibility curtailment
     reduces delivered kW; `curtailed_kw` is recorded per match.
  3. **Generation/discharge positive, load draw/charge negative.** Flows are
     directed `from`→`to` with positive magnitude.
  4. **Clear CRITICAL after ≥2 consecutive good heartbeats** (anti-flap).
  5. **Dedicated `node/<id>/heartbeat` topic**, separate from state, so an
     "alive but silent on state" node is still distinguishable from a dead one.
- Why (evidence / tradeoff): Merit-order uniform pricing is the standard,
  defensible CDA rule and is simplest for the frontend to display. Delivered-kW
  settlement keeps money from paying for power a wire could not carry (the whole
  point of the feasibility layer). A single sign convention prevents the most
  common integration bug. Hysteresis stops a single stray packet from flapping
  grid mode. A dedicated heartbeat decouples liveness from data payloads.
- Revisit when: moving to v2 (ADMM/optimal-power-flow feasibility may change how
  curtailment/settlement interact) or adding multi-line topology routing.
