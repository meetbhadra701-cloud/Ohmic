"""Battery / BESS agent = Agent A (Preservation Agent).

Goal: minimize degradation. Two-sided market participant governed by a SoC target
band:
  - below the band  -> BID to charge (buy cheap energy, typically midday solar),
  - above the band  -> ASK to discharge, priced by the quadratic degradation cost
                       (cheap when full, expensive near-empty),
  - inside the band  -> idle.
This produces a daily cycle (charge midday, discharge evening) and routes charging
flow through the auction + feasibility check. In a fault it bypasses the market and
grid-forms to the critical load only (Step 5).
"""
from __future__ import annotations

from ..physics.degradation import DegradationParams, marginal_degradation_cost
from .base import TOPIC_ALERT, TOPIC_TICK, BaseAgent

TOPIC_CLEARING = "market/clearing"

TARGET_SOC = 0.70           # SoC the battery steers toward
SOC_DEADBAND = 0.05         # idle band around the target
CHARGE_PRICE = 0.12         # willingness-to-pay to charge (above solar floor, below load ceiling)


class BatteryAgent(BaseAgent):
    def __init__(self, bus, cfg):
        node = cfg["nodes"]["battery"]
        super().__init__(bus, node["id"])
        self.capacity_kwh = node["capacity_kwh"]
        self.soc = node["soc_init"]
        self.soc_floor = node["soc_floor"]
        self.max_power_kw = node["max_power_kw"]
        self.dt_h = 24.0 / cfg["sim"]["ticks_per_day"]
        self.deg = DegradationParams.from_config(cfg)
        self.mode = "market"            # "market" | "grid_forming"
        self.flow_kw = 0.0
        self.unmet_kw = 0.0
        self.last_ask_price: float | None = None

    def subscriptions(self) -> list[str]:
        return [TOPIC_TICK, TOPIC_CLEARING, TOPIC_ALERT]

    def _energy_to_soc(self, kw: float) -> float:
        return (kw * self.dt_h) / self.capacity_kwh

    def _dischargeable_kw(self) -> float:
        energy_above_floor = max(0.0, (self.soc - self.soc_floor) * self.capacity_kwh)
        return min(self.max_power_kw, energy_above_floor / self.dt_h)

    def _chargeable_kw(self) -> float:
        room = max(0.0, (1.0 - self.soc) * self.capacity_kwh)
        return min(self.max_power_kw, room / self.dt_h)

    async def on_alert(self, alert: dict) -> None:
        self.mode = "grid_forming" if alert.get("level") == "CRITICAL" else "market"

    async def on_message(self, msg):
        if msg.topic == TOPIC_CLEARING:
            await self._on_clearing(msg.payload)
        else:
            await super().on_message(msg)

    async def on_tick(self, tick: dict) -> None:
        t = tick["tick"]
        await self.bus.publish(f"node/{self.node_id}/heartbeat", {"tick": t, "node_id": self.node_id})
        self.last_ask_price = None
        if self.mode == "market":
            await self._participate(t)
        await self._publish_state(t)

    async def _participate(self, t: int) -> None:
        if self.soc < TARGET_SOC - SOC_DEADBAND:               # charge
            vol = self._chargeable_kw()
            if vol > 1e-6:
                await self.bus.publish(
                    "market/bids",
                    {"tick": t, "agent_id": self.node_id, "intent": "buy",
                     "volume_kw": vol, "max_price_usd_kwh": CHARGE_PRICE},
                    qos=0,
                )
        elif self.soc > TARGET_SOC + SOC_DEADBAND:             # discharge
            vol = self._dischargeable_kw()
            if vol > 1e-6:
                soc_t1 = self.soc - self._energy_to_soc(vol)
                price = marginal_degradation_cost(self.soc, soc_t1, self.deg)["ask_price_usd_kwh"]
                self.last_ask_price = price
                await self.bus.publish(
                    "market/asks",
                    {"tick": t, "agent_id": self.node_id, "intent": "sell",
                     "volume_kw": vol, "min_price_usd_kwh": price},
                    qos=0,
                )

    async def _on_clearing(self, clearing: dict) -> None:
        matches = clearing.get("matches", [])
        discharged = sum(m["kw"] for m in matches if m["seller"] == self.node_id)
        charged = sum(m["kw"] for m in matches if m["buyer"] == self.node_id)
        self.soc = min(1.0, max(0.0, self.soc + self._energy_to_soc(charged - discharged)))
        self.flow_kw = discharged - charged                    # + discharge, - charge

    async def _publish_state(self, t: int) -> None:
        await self.bus.publish(
            f"node/{self.node_id}/state",
            {"tick": t, "node_id": self.node_id, "type": "battery",
             "soc": self.soc, "max_discharge_kw": self.max_power_kw,
             "flow_kw": self.flow_kw, "mode": self.mode,
             "ask_price_usd_kwh": self.last_ask_price, "unmet_kw": self.unmet_kw,
             "health": "nominal"},
            retain=True,
        )
