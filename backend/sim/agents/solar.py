"""Solar PV agent (Generator) — deterministic, uncontrollable, killable.

Output follows a time-of-day irradiance curve capped by the inverter limit. Solar
is must-take generation: it asks at the price floor so its energy clears first.
The chaos module can 'kill' it (it stops publishing state + heartbeat), which is
what the Grid Operator detects as a fault.
"""
from __future__ import annotations

from ..physics.clearing import Order
from ..physics.profiles import solar_output_kw
from .base import TOPIC_TICK, BaseAgent

TOPIC_CHAOS = "chaos/command"


class SolarAgent(BaseAgent):
    def __init__(self, bus, cfg):
        node = cfg["nodes"]["solar"]
        super().__init__(bus, node["id"])
        self.inverter_kw = node["inverter_kw"]
        self.floor_price = cfg["degradation"]["floor_price"]
        self.output_kw = 0.0
        self.alive = True

    def subscriptions(self) -> list[str]:
        return [TOPIC_TICK, TOPIC_CHAOS]

    async def on_message(self, msg):
        if msg.topic == TOPIC_CHAOS and msg.payload.get("target") == self.node_id:
            self.alive = msg.payload.get("action") != "kill"
        else:
            await super().on_message(msg)

    async def on_tick(self, tick: dict) -> None:
        if not self.alive:
            return  # dead: no heartbeat, no state, no ask -> operator will detect loss
        t = tick["tick"]
        self.output_kw = solar_output_kw(tick["day_phase"], self.inverter_kw)
        await self.bus.publish(f"node/{self.node_id}/heartbeat", {"tick": t, "node_id": self.node_id})
        await self.bus.publish(
            f"node/{self.node_id}/state",
            {"tick": t, "node_id": self.node_id, "type": "solar",
             "output_kw": self.output_kw, "alive": True, "health": "nominal"},
            retain=True,
        )
        if self.output_kw > 0.0:
            ask = Order(self.node_id, self.floor_price, self.output_kw)
            await self.bus.publish(
                "market/asks",
                {"tick": t, "agent_id": self.node_id, "intent": "sell",
                 "volume_kw": ask.qty_kw, "min_price_usd_kwh": ask.price_usd_kwh},
                qos=0,
            )
