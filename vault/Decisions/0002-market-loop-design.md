# Decision: Market-loop timing, battery participation, and a YAML trap
- Date: 2026-06-20
- Context: Wiring the pub/sub market loop (Step 4) surfaced three non-obvious choices
  and one bug that cost real time. Recording them so they are not re-litigated.
- Options considered & Decisions:
  1. **Settlement timing.** The Grid Operator cannot know all of a tick's orders
     have arrived (pub/sub, no barrier). Options: clear on the next tick (1-tick
     grace), clear on an explicit "market close" signal, or clear with a multi-tick
     grace. → **Clear with a 2-tick grace** (settle tick T when tick T+2 arrives).
     A 1-tick grace was empirically flaky: with 6 MQTT clients on one event loop,
     task-scheduling order is nondeterministic and many books settled empty. 2
     ticks gives a full tick period of slack and is reliably correct.
  2. **Order QoS.** Bids/asks were QoS 1 (PUBACK handshake) → round-trip latency
     pushed orders past the settle window. → **Orders are QoS 0** (fire-and-forget;
     the settle grace tolerates a rare drop as `unmet`). Clearing and alerts stay
     QoS 1 (must not drop).
  3. **Battery market participation.** A discharge-only battery drains overnight
     (it is the only night supply) and never recharges, so midday solar never
     flows through the feasibility check and curtailment never triggers. →
     **Battery is a two-sided participant** governed by a SoC target band: bids to
     charge below the band, asks to discharge above it. This produces a daily cycle
     and routes charging flow through the auction, so the midday solar→(load+charge)
     flow exceeds the feeder rating and curtailment is exercised realistically.
- The bug: **PyYAML (YAML 1.1) parses `5.0e-5` / `1.0e8` as STRINGS**, not floats,
  unless written with an explicit exponent sign or as plain decimals. This silently
  made degradation coefficients and `cond_max` strings, crashing the ridge watchdog
  and battery pricing. Fixed by writing plain decimals in config.yaml AND adding
  defensive `float()`/`int()` casts in the `from_config` constructors.
- Why: faithful to the manual (real CDA + feasibility, all ridge rails) while being
  robust on a single-process asyncio sim. Curtailment, trades, and energy
  conservation now hold deterministically across runs.
- Revisit when: moving to realistic (>=100ms) tick periods for the live demo the
  grace could drop to 1 tick; or if agents move to separate processes.
