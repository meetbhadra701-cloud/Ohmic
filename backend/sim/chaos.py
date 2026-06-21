"""Chaos module — induces the fault the system must self-heal from.

At `kill_tick` it tells the target node to die (stop publishing state/heartbeat);
at `revive_tick` it restores it. Deterministic for reproducible demos. Can also be
driven live from the frontend via the WebSocket `chaos` command (Step 6).
"""
from __future__ import annotations

from .agents.base import TOPIC_TICK, BaseAgent

TOPIC_CHAOS = "chaos/command"


class ChaosAgent(BaseAgent):
    def __init__(self, bus, cfg):
        super().__init__(bus, "CHAOS")
        c = cfg["chaos"]
        self.kill_tick = int(c["kill_tick"])
        self.revive_tick = int(c["revive_tick"])
        self.target = c["target"]

    def subscriptions(self) -> list[str]:
        return [TOPIC_TICK]

    async def on_tick(self, tick: dict) -> None:
        t = tick["tick"]
        if self.kill_tick and t == self.kill_tick:
            await self._command(t, "kill")
        elif self.revive_tick and t == self.revive_tick:
            await self._command(t, "restore")

    async def _command(self, t: int, action: str) -> None:
        await self.bus.publish(
            TOPIC_CHAOS, {"tick": t, "target": self.target, "action": action}, qos=1,
        )
