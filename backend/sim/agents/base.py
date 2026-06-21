"""Base sim agent — common async shape: own a Bus, subscribe, dispatch by topic.

Subclasses override `subscriptions()` and the `on_*` hooks. Every agent is a plain
`async def run()` coroutine on the single event loop — no threads, no locks.
"""
from __future__ import annotations

from ..bus import Bus, Message

TOPIC_TICK = "grid/tick"
TOPIC_ALERT = "grid/alert"


class BaseAgent:
    def __init__(self, bus: Bus, node_id: str):
        self.bus = bus
        self.node_id = node_id

    def subscriptions(self) -> list[str]:
        """Topics this agent listens to. Default: just the tick."""
        return [TOPIC_TICK]

    async def run(self) -> None:
        async with self.bus:
            await self.bus.subscribe(*self.subscriptions())
            await self.on_start()
            async for msg in self.bus.messages():
                if msg.retain:
                    continue          # ignore stale retained state from a prior run
                await self.on_message(msg)

    async def on_start(self) -> None:
        """Optional one-time setup after subscribing."""

    async def on_message(self, msg: Message) -> None:
        """Default dispatch by topic prefix. Subclasses extend as needed."""
        if msg.topic == TOPIC_TICK:
            await self.on_tick(msg.payload)
        elif msg.topic == TOPIC_ALERT:
            await self.on_alert(msg.payload)

    async def on_tick(self, tick: dict) -> None:
        """Called once per `grid/tick`. The per-tick decision lives here."""

    async def on_alert(self, alert: dict) -> None:
        """Called on `grid/alert` (CRITICAL / ALL_CLEAR)."""
