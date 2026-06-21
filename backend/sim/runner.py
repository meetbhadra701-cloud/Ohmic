"""Wire the sim: clock + the four real agents. Reused by check scripts + server."""
from __future__ import annotations

from typing import Callable

from .agents.battery import BatteryAgent
from .agents.grid_operator import GridOperatorAgent
from .agents.load import LoadAgent
from .agents.solar import SolarAgent
from .bus import Bus
from .chaos import ChaosAgent
from .clock import Clock


def make_bus(cfg: dict, client_id: str, run_id: str | None = None) -> Bus:
    return Bus(cfg["mqtt"]["host"], cfg["mqtt"]["port"], client_id, run_id=run_id)


def build_sim(cfg: dict, log: Callable[[str], None] | None = None,
              tick_period: float | None = None, max_ticks: int = 0,
              run_id: str | None = None):
    """Return (clock, [agents]). Each owns its own bus/connection."""
    tp = tick_period if tick_period is not None else cfg["sim"]["tick_period_s"]
    clock = Clock(make_bus(cfg, "clock", run_id), tp, cfg["sim"]["ticks_per_day"], max_ticks)
    agents = [
        SolarAgent(make_bus(cfg, "solar", run_id), cfg),
        BatteryAgent(make_bus(cfg, "battery", run_id), cfg),
        LoadAgent(make_bus(cfg, "load", run_id), cfg, log=log),
        GridOperatorAgent(make_bus(cfg, "operator", run_id), cfg, log=log),
        ChaosAgent(make_bus(cfg, "chaos", run_id), cfg),
    ]
    return clock, agents
