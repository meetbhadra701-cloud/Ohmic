"""Base sim agent — common async shape: own a Bus, subscribe, dispatch by topic.

Subclasses override `subscriptions()` and the `on_*` hooks. Every agent is a plain
`async def run()` coroutine on the single event loop — no threads, no locks.
"""
from __future__ import annotations

import asyncio
import logging

import aiomqtt

from ..bus import Bus, Message

TOPIC_TICK = "grid/tick"
TOPIC_ALERT = "grid/alert"

log = logging.getLogger("sim.agent")

# Bounded backoff between broker-reconnect attempts (seconds).
_RECONNECT_BACKOFF_S = 1.0
_RECONNECT_MAX_S = 10.0


class BaseAgent:
    def __init__(self, bus: Bus, node_id: str):
        self.bus = bus
        self.node_id = node_id

    def subscriptions(self) -> list[str]:
        """Topics this agent listens to. Default: just the tick."""
        return [TOPIC_TICK]

    async def run(self) -> None:
        """Run forever, surviving broker drops.

        On `MqttError` (broker disconnect/refused) the loop reconnects with bounded
        backoff and re-subscribes — a broker hiccup stalls this agent but never kills
        the process. `CancelledError` (clean shutdown) is *not* caught, so task
        cancellation still works. `FakeBus` never raises `MqttError`, so unit tests
        run the body exactly once, unchanged.
        """
        backoff = _RECONNECT_BACKOFF_S
        while True:
            try:
                async with self.bus:
                    await self.bus.subscribe(*self.subscriptions())
                    await self.on_start()
                    backoff = _RECONNECT_BACKOFF_S  # connected cleanly; reset backoff
                    async for msg in self.bus.messages():
                        await self.on_message(msg)
                return  # message stream ended normally → done
            except aiomqtt.MqttError as exc:
                log.warning("%s lost broker (%s); reconnecting in %.1fs",
                            self.node_id, exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _RECONNECT_MAX_S)

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
