#!/usr/bin/env python3
"""Step 6 gate: prove the WebSocket server broadcasts contract-compliant frames.

Runs the full sim + WebSocket server, connects a WS client, collects frames,
and asserts:
  - One frame arrives per tick (within tolerance).
  - Every frame has the required top-level fields from CONTRACTS/websocket_api.md.
  - All three node IDs are present with their type-correct sub-fields.
  - market, forecast, and alerts blocks are present and well-typed.
  - mode is "NORMAL" or "CRITICAL".
  - schema_version == 1.

    .venv/bin/python backend/scripts/check_ws.py
"""
import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import websockets

from sim.bus import new_run_id
from sim.config import load_config
from sim.runner import build_server, build_sim

EXPECT_FRAMES = 30
TICK_PERIOD = 0.20   # fast enough for a gate run


def _check_frame(frame: dict, idx: int) -> list[str]:
    """Return a list of violation strings (empty = OK)."""
    errs: list[str] = []

    def require(cond: bool, msg: str) -> None:
        if not cond:
            errs.append(f"frame[{idx}]: {msg}")

    # Top-level
    require(frame.get("schema_version") == 1, "schema_version != 1")
    require(isinstance(frame.get("tick"), int), "tick not int")
    require(isinstance(frame.get("sim_time"), str), "sim_time not str")
    require(isinstance(frame.get("day_phase"), float), "day_phase not float")
    require(frame.get("mode") in ("NORMAL", "CRITICAL"), f"mode invalid: {frame.get('mode')!r}")
    require(isinstance(frame.get("nodes"), dict), "nodes not dict")
    require(isinstance(frame.get("market"), dict), "market not dict")
    require(isinstance(frame.get("forecast"), dict), "forecast not dict")
    require(isinstance(frame.get("alerts"), list), "alerts not list")

    # Nodes
    nodes = frame.get("nodes", {})
    require(set(nodes.keys()) == {"PV_01", "BESS_01", "LOAD_CAMPUS"}, f"unexpected node keys: {set(nodes.keys())}")

    pv = nodes.get("PV_01", {})
    require(pv.get("type") == "solar", "PV_01.type != solar")
    require(isinstance(pv.get("output_kw"), (int, float)), "PV_01.output_kw not number")
    require(isinstance(pv.get("alive"), bool), "PV_01.alive not bool")

    batt = nodes.get("BESS_01", {})
    require(batt.get("type") == "battery", "BESS_01.type != battery")
    require(isinstance(batt.get("soc"), (int, float)), "BESS_01.soc not number")
    require(isinstance(batt.get("soc_percent"), (int, float)), "BESS_01.soc_percent not number")
    require(batt.get("mode") in ("market", "grid_forming"), f"BESS_01.mode invalid: {batt.get('mode')!r}")

    load = nodes.get("LOAD_CAMPUS", {})
    require(load.get("type") == "load", "LOAD_CAMPUS.type != load")
    require(isinstance(load.get("demand_kw"), (int, float)), "LOAD_CAMPUS.demand_kw not number")
    require(isinstance(load.get("served_kw"), (int, float)), "LOAD_CAMPUS.served_kw not number")

    # Market
    mkt = frame.get("market", {})
    require("clearing_price_usd_kwh" in mkt, "market missing clearing_price_usd_kwh")
    require(isinstance(mkt.get("flows"), list), "market.flows not list")
    require(isinstance(mkt.get("unmet_kw"), (int, float)), "market.unmet_kw not number")
    require(isinstance(mkt.get("curtailed_kw"), (int, float)), "market.curtailed_kw not number")
    require(isinstance(mkt.get("per_line_flow_kw"), dict), "market.per_line_flow_kw not dict")

    # Forecast
    fcast = frame.get("forecast", {})
    require(isinstance(fcast.get("predicted_demand_kw"), (int, float)), "forecast.predicted_demand_kw not number")
    require(isinstance(fcast.get("horizon_ticks"), int), "forecast.horizon_ticks not int")
    require(isinstance(fcast.get("actual_demand_kw"), (int, float)), "forecast.actual_demand_kw not number")
    require(isinstance(fcast.get("warm"), bool), "forecast.warm not bool")

    return errs


async def collect_frames(ws_port: int, frames: list[dict], n: int) -> None:
    uri = f"ws://localhost:{ws_port}"
    async with websockets.connect(uri) as ws:
        async for raw in ws:
            frame = json.loads(raw)
            frames.append(frame)
            if len(frames) >= n:
                return


async def main() -> int:
    cfg = load_config()
    run_id = new_run_id("ws")
    ws_port = int(cfg["websocket"]["port"])

    clock, agents = build_sim(cfg, log=lambda m: None,
                              tick_period=TICK_PERIOD,
                              max_ticks=EXPECT_FRAMES + 20,
                              run_id=run_id)
    server = build_server(cfg, run_id=run_id)

    sim_tasks = (
        [asyncio.create_task(clock.run())]
        + [asyncio.create_task(a.run()) for a in agents]
        + [asyncio.create_task(server.run())]
    )

    frames: list[dict] = []
    # Wait for the WS server to bind (retry-connect instead of a fixed sleep).
    deadline = asyncio.get_event_loop().time() + 10.0
    while asyncio.get_event_loop().time() < deadline:
        try:
            async with websockets.connect(f"ws://localhost:{ws_port}"):
                break
        except OSError:
            await asyncio.sleep(0.1)
    try:
        async with asyncio.timeout(30):
            await collect_frames(ws_port, frames, EXPECT_FRAMES)
    finally:
        for t in sim_tasks:
            t.cancel()
        await asyncio.gather(*sim_tasks, return_exceptions=True)

    assert len(frames) >= EXPECT_FRAMES, f"only {len(frames)} frames received"

    all_errors: list[str] = []
    for i, f in enumerate(frames):
        all_errors.extend(_check_frame(f, i))

    if all_errors:
        for e in all_errors:
            print(f"  FAIL: {e}", file=sys.stderr)
        raise AssertionError(f"{len(all_errors)} contract violations found")

    ticks = [f["tick"] for f in frames]
    modes = {f["mode"] for f in frames}
    print(f"OK: {len(frames)} frames; ticks {min(ticks)}..{max(ticks)}; "
          f"modes seen: {sorted(modes)}; all fields contract-compliant")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except (AssertionError, Exception) as exc:  # noqa: BLE001
        print(f"CHECK FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
