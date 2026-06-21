"""Wire the sim: clock + the four real agents. Reused by check scripts + server."""
from __future__ import annotations

import pathlib
from typing import Callable

from .agents.battery import BatteryAgent
from .agents.grid_operator import GridOperatorAgent
from .agents.load import LoadAgent
from .agents.solar import SolarAgent
from .bus import Bus
from .chaos import ChaosAgent
from .clock import Clock
from .physics.profiles import load_csv_profiles
from .server import WebSocketServer

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def _configure_profiles(cfg: dict) -> None:
    """Load CSV profiles if config requests it; otherwise synthetic curves stay active."""
    prof = cfg.get("profiles", {})
    if prof.get("source") == "csv":
        solar = _REPO_ROOT / prof["solar_csv"]
        load_ = _REPO_ROOT / prof["load_csv"]
        load_csv_profiles(solar, load_)


def make_bus(cfg: dict, client_id: str, run_id: str | None = None) -> Bus:
    return Bus(cfg["mqtt"]["host"], cfg["mqtt"]["port"], client_id, run_id=run_id)


def build_sim(cfg: dict, log: Callable[[str], None] | None = None,
              tick_period: float | None = None, max_ticks: int = 0,
              run_id: str | None = None):
    """Return (clock, [agents]). Each owns its own bus/connection."""
    _configure_profiles(cfg)
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


def build_server(cfg: dict, run_id: str | None = None) -> WebSocketServer:
    """Return a WebSocketServer wired to the same run's MQTT bus."""
    return WebSocketServer(make_bus(cfg, "ws_server", run_id), cfg)
