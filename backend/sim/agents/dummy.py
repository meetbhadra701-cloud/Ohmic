"""Step 1 dummy node — publishes fixed state + heartbeat each tick.

Exists only to prove the pub/sub plumbing and tick sync before the real agents
(Steps 2-5) are built. Replaced by solar.py / battery.py / load.py later.
"""
from __future__ import annotations

from .base import BaseAgent


class DummyNode(BaseAgent):
    def __init__(self, bus, node_id: str, node_type: str, fixed_state: dict):
        super().__init__(bus, node_id)
        self.node_type = node_type
        self.fixed_state = fixed_state

    async def on_tick(self, tick: dict) -> None:
        t = tick["tick"]
        await self.bus.publish(f"node/{self.node_id}/heartbeat", {"tick": t, "node_id": self.node_id})
        await self.bus.publish(
            f"node/{self.node_id}/state",
            {"tick": t, "node_id": self.node_id, "type": self.node_type, "health": "nominal", **self.fixed_state},
            qos=0,
            retain=True,
        )
