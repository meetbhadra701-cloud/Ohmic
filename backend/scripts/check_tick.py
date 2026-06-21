#!/usr/bin/env python3
"""Step 1 gate: prove clock tick-sync + bus pub/sub plumbing.

Launches the Clock + two DummyNodes + a verifier on one event loop. Asserts the
verifier receives monotonic, contiguous ticks and that both dummy nodes publish
state for those ticks. Exit 0 on success.

    .venv/bin/python backend/scripts/check_tick.py
"""
import asyncio
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sim.bus import Bus, new_run_id
from sim.clock import Clock
from sim.config import load_config
from sim.agents.dummy import DummyNode

EXPECT_TICKS = 20
TICK_PERIOD = 0.08  # fast ticks for the test, with room for state messages
EXPECTED_NODES = {"PV_01", "BESS_01"}


async def verifier(bus: Bus, ticks_seen: list[int], states: dict[str, set]) -> None:
    async with bus:
        await bus.subscribe("grid/tick", "node/+/state")
        async for msg in bus.messages():
            if msg.topic == "grid/tick":
                ticks_seen.append(msg.payload["tick"])
            elif msg.topic.endswith("/state"):
                states.setdefault(msg.payload["node_id"], set()).add(msg.payload["tick"])
            if (
                len(set(ticks_seen)) >= EXPECT_TICKS
                and all(len(states.get(node, set())) >= EXPECT_TICKS - 2 for node in EXPECTED_NODES)
            ):
                return


async def main() -> int:
    cfg = load_config()
    host, port = cfg["mqtt"]["host"], cfg["mqtt"]["port"]
    ticks_per_day = cfg["sim"]["ticks_per_day"]
    run_id = new_run_id("tick")

    ticks_seen: list[int] = []
    states: dict[str, set] = {}

    clock = Clock(Bus(host, port, "clock", run_id=run_id), TICK_PERIOD, ticks_per_day, max_ticks=EXPECT_TICKS + 8)
    pv = DummyNode(Bus(host, port, "dummy_pv", run_id=run_id), "PV_01", "solar", {"output_kw": 70.0, "alive": True})
    bess = DummyNode(Bus(host, port, "dummy_bess", run_id=run_id), "BESS_01", "battery", {"soc": 0.6, "flow_kw": 0.0})

    tasks = [
        asyncio.create_task(clock.run()),
        asyncio.create_task(pv.run()),
        asyncio.create_task(bess.run()),
    ]
    vbus = Bus(host, port, "verifier", run_id=run_id)
    try:
        async with asyncio.timeout(15):
            await verifier(vbus, ticks_seen, states)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    # Assertions
    distinct = sorted(set(ticks_seen))
    assert distinct == sorted(ticks_seen), f"duplicate ticks: {ticks_seen}"
    # The verifier may connect after tick 0 is published (grid/tick isn't retained);
    # what matters is that ticks are monotonic and contiguous from where we joined.
    assert distinct[0] <= 3, f"ticks started unexpectedly late: {distinct[:3]}"
    assert distinct == list(range(distinct[0], distinct[-1] + 1)), f"ticks not contiguous: {distinct}"
    assert len(distinct) >= EXPECT_TICKS, f"saw only {len(distinct)} ticks"
    for node in EXPECTED_NODES:
        assert node in states and len(states[node]) >= EXPECT_TICKS - 2, f"{node} under-published: {states.get(node)}"
    print(f"OK: {len(distinct)} monotonic contiguous ticks; nodes published: "
          f"{ {n: len(s) for n, s in states.items()} }")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except (AssertionError, Exception) as exc:  # noqa: BLE001
        print(f"CHECK FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
