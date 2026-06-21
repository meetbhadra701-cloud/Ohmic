#!/usr/bin/env python3
"""Step 5 gate: prove the self-healing protocol end to end.

Kills solar mid-run and asserts the full transcript:
  solar dies -> Operator raises CRITICAL after missed heartbeats
             -> Load sheds non-critical (shed_kw > 0)
             -> Battery enters grid_forming mode
  solar revives -> Operator raises ALL_CLEAR
                -> Battery returns to market mode, Load stops shedding.

    .venv/bin/python backend/scripts/check_heal.py
"""
import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sim.bus import Bus, new_run_id
from sim.config import load_config
from sim.runner import build_sim

KILL, REVIVE, RUN_TO = 26, 42, 58
TICK_PERIOD = 0.10      # realistic-ish cadence; leaves ample slack for heartbeat delivery


async def observe(bus, alerts, battery_mode, load_shed, solar_alive):
    async with bus:
        await bus.subscribe("grid/alert", "node/PV_01/state", "node/BESS_01/state", "node/LOAD_CAMPUS/state")
        async for msg in bus.messages():
            if msg.retain:
                continue          # skip stale retained frames from a prior run
            p, topic = msg.payload, msg.topic
            if topic == "grid/alert":
                alerts.append((p["tick"], p["level"], p["type"]))
            elif topic.endswith("BESS_01/state"):
                battery_mode[p["tick"]] = p["mode"]
            elif topic.endswith("LOAD_CAMPUS/state"):
                load_shed[p["tick"]] = p["shed_kw"]
            elif topic.endswith("PV_01/state"):
                solar_alive[p["tick"]] = p["alive"]


async def main() -> int:
    cfg = load_config()
    cfg["chaos"].update(kill_tick=KILL, revive_tick=REVIVE)
    run_id = new_run_id("heal")
    clock, agents = build_sim(cfg, log=lambda m: None, tick_period=TICK_PERIOD, max_ticks=RUN_TO, run_id=run_id)
    tasks = [asyncio.create_task(clock.run())] + [asyncio.create_task(a.run()) for a in agents]

    alerts, battery_mode, load_shed, solar_alive = [], {}, {}, {}
    obus = Bus(cfg["mqtt"]["host"], cfg["mqtt"]["port"], "heal_observer", run_id=run_id)
    try:
        async with asyncio.timeout(30):
            await asyncio.wait_for(observe(obus, alerts, battery_mode, load_shed, solar_alive),
                                   timeout=RUN_TO * TICK_PERIOD + 3)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    crit = [a for a in alerts if a[1] == "CRITICAL"]
    clear = [a for a in alerts if a[1] == "ALL_CLEAR"]
    assert crit, f"no CRITICAL alert raised. alerts={alerts}"
    assert clear, f"no ALL_CLEAR alert raised. alerts={alerts}"
    crit_tick, clear_tick = crit[0][0], clear[0][0]
    assert crit[0][2] == "SOLAR_LOSS"
    assert crit_tick > KILL, f"CRITICAL ({crit_tick}) not after kill ({KILL})"
    assert clear_tick > REVIVE, f"ALL_CLEAR ({clear_tick}) not after revive ({REVIVE})"

    # During the fault window: load shed and battery grid-formed.
    fault_ticks = [t for t in range(crit_tick, clear_tick) if t in load_shed]
    assert any(load_shed[t] > 1e-6 for t in fault_ticks), "load never shed non-critical during fault"
    gf = [t for t in range(crit_tick, clear_tick) if battery_mode.get(t) == "grid_forming"]
    assert gf, "battery never entered grid_forming during fault"

    # After recovery: battery ends back in market mode and load stops shedding.
    post = [t for t in battery_mode if t > clear_tick]
    assert post, "no battery state observed after recovery"
    assert battery_mode[max(battery_mode)] == "market", "battery did not return to market mode by end of run"
    assert load_shed[max(load_shed)] <= 1e-6, "load still shedding at end of run"

    print(f"OK: CRITICAL@{crit_tick} (kill@{KILL}) -> shed+grid_forming -> "
          f"ALL_CLEAR@{clear_tick} (revive@{REVIVE}) -> back to market")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception as exc:  # noqa: BLE001
        print(f"CHECK FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
