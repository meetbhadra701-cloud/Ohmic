"""Battery agent behavior that protects the self-healing demo path."""
import asyncio

import pytest

from sim.agents.battery import BatteryAgent, TARGET_SOC
from sim.bus import FakeBroker, FakeBus, new_run_id
from sim.config import load_config


def _agent() -> BatteryAgent:
    cfg = load_config()
    run_id = new_run_id("battery-test")
    return BatteryAgent(FakeBus(FakeBroker(), "battery", run_id=run_id), cfg)


def test_market_discharge_preserves_target_reserve():
    agent = _agent()
    agent.soc = 0.95

    offered = agent._market_dischargeable_kw()

    assert offered > 0.0
    assert agent.soc - agent._energy_to_soc(offered) >= TARGET_SOC


def test_pending_market_sells_prevent_overcommit():
    agent = _agent()
    agent.soc = TARGET_SOC + agent._energy_to_soc(agent.max_power_kw)
    first = agent._market_dischargeable_kw()
    agent.pending_market_sells[1] = first

    second = agent._market_dischargeable_kw()

    assert second == pytest.approx(0.0)


def test_grid_forming_discharges_immediately_to_critical_load():
    agent = _agent()
    agent.soc = 0.80
    agent.last_critical_kw = 40.0

    asyncio.run(agent._grid_form(10))

    assert agent.flow_kw == pytest.approx(40.0)
    assert agent.unmet_kw == pytest.approx(0.0)
    assert agent.soc < 0.80


def test_grid_forming_respects_soc_floor_and_reports_unmet():
    agent = _agent()
    agent.soc = agent.soc_floor
    agent.last_critical_kw = 40.0

    asyncio.run(agent._grid_form(10))

    assert agent.flow_kw == pytest.approx(0.0)
    assert agent.unmet_kw == pytest.approx(40.0)
    assert agent.soc == pytest.approx(agent.soc_floor)
