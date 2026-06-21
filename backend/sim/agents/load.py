"""Load / Campus agent = Agent B (Load Servicing Agent).

Goal: maximize served demand, avoid shedding. Splits demand into critical
(must-serve) and non-critical (sheddable). Runs the online recursive ridge
forecast to anticipate demand. In a fault it bypasses forecast/market and sheds
all non-critical load immediately (Step 5).

Feature vector contract (mirrored in recursive_ridge x-ordering), d = 6:
    x = [1(bias), sin(2*pi*phase), cos(2*pi*phase), temp, lag1, lag2]
"""
from __future__ import annotations

import math

import numpy as np

from ..physics.clearing import Order
from ..physics.profiles import load_demand_kw, split_load
from ..physics.recursive_ridge import RecursiveRidge, RidgeConfig
from .base import TOPIC_ALERT, TOPIC_TICK, BaseAgent

TOPIC_CLEARING = "market/clearing"
FEATURE_DIM = 6
MAX_PRICE_USD_KWH = 0.40   # load's willingness-to-pay ceiling


def _temp_proxy(day_phase: float) -> float:
    """Synthetic daily temperature curve (placeholder until the CSV swap)."""
    return 15.0 + 10.0 * math.sin(2 * math.pi * (day_phase - 0.25))


class LoadAgent(BaseAgent):
    def __init__(self, bus, cfg, log=None):
        node = cfg["nodes"]["load"]
        super().__init__(bus, node["id"])
        self.base_kw = node["base_kw"]
        self.peak_kw = node["peak_kw"]
        self.noise_kw = node["noise_kw"]
        self.critical_fraction = node["critical_fraction"]
        self.horizon = cfg["ridge"]["horizon_ticks"]
        self.ticks_per_day = cfg["sim"]["ticks_per_day"]
        self.rng = np.random.default_rng(1234)   # deterministic noise
        self.ridge = RecursiveRidge(RidgeConfig.from_config(cfg, FEATURE_DIM), log=log)
        self.lag1 = self.base_kw
        self.lag2 = self.base_kw
        self.mode = "market"            # "market" | "fault"
        self.demand_kw = 0.0
        self.served_kw = 0.0
        self.shed_kw = 0.0
        self.predicted_kw = 0.0

    def subscriptions(self) -> list[str]:
        return [TOPIC_TICK, TOPIC_CLEARING, TOPIC_ALERT]

    def _features(self, day_phase: float, lag1: float, lag2: float) -> np.ndarray:
        return np.array([
            1.0,
            math.sin(2 * math.pi * day_phase),
            math.cos(2 * math.pi * day_phase),
            _temp_proxy(day_phase),
            lag1,
            lag2,
        ])

    async def on_alert(self, alert: dict) -> None:
        self.mode = "fault" if alert.get("level") == "CRITICAL" else "market"

    async def on_message(self, msg):
        if msg.topic == TOPIC_CLEARING:
            await self._on_clearing(msg.payload)
        else:
            await super().on_message(msg)

    async def on_tick(self, tick: dict) -> None:
        t = tick["tick"]
        phase = tick["day_phase"]
        await self.bus.publish(f"node/{self.node_id}/heartbeat", {"tick": t, "node_id": self.node_id}, qos=1)

        actual = load_demand_kw(phase, self.base_kw, self.peak_kw, self.noise_kw, self.rng)
        self.demand_kw = actual
        critical, _ = split_load(actual, self.critical_fraction)

        x = self._features(phase, self.lag1, self.lag2)
        # Forecast a few ticks ahead for the UI chart (projected phase).
        future_phase = ((t + self.horizon) % self.ticks_per_day) / self.ticks_per_day
        x_future = self._features(future_phase, actual, self.lag1)
        self.predicted_kw = self.ridge.predict(x_future) if self.ridge.is_warm() else actual

        if self.mode == "fault":
            # Bypass forecast/market: shed all non-critical, buy only critical.
            self.shed_kw = actual - critical
            bid_kw = critical
        else:
            self.shed_kw = 0.0
            bid_kw = actual

        if bid_kw > 1e-6:
            bid = Order(self.node_id, MAX_PRICE_USD_KWH, bid_kw)
            await self.bus.publish(
                "market/bids",
                {"tick": t, "agent_id": self.node_id, "intent": "buy",
                 "volume_kw": bid.qty_kw, "max_price_usd_kwh": bid.price_usd_kwh},
                qos=1,
            )

        # Online learning: update the ridge with this tick's realized demand.
        self.ridge.update(x, actual)
        self.lag2 = self.lag1
        self.lag1 = actual
        await self._publish_state(t, critical)

    async def _on_clearing(self, clearing: dict) -> None:
        self.served_kw = sum(m["kw"] for m in clearing.get("matches", []) if m["buyer"] == self.node_id)

    async def _publish_state(self, t: int, critical: float) -> None:
        rs = self.ridge.state()
        await self.bus.publish(
            f"node/{self.node_id}/state",
            {"tick": t, "node_id": self.node_id, "type": "load",
             "demand_kw": self.demand_kw, "critical_kw": critical,
             "served_kw": self.served_kw, "shed_kw": self.shed_kw, "health": "nominal",
             # forecast telemetry (consumed by the WebSocket layer for the frame's forecast block)
             "predicted_demand_kw": self.predicted_kw, "forecast_horizon_ticks": self.horizon,
             "ridge_cond": rs["cond"], "ridge_reanchor_count": rs["reanchor_count"],
             "ridge_warm": rs["warm"]},
            retain=True,
        )
