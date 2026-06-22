"""Central Clock — the sim's single source of time.

Publishes `grid/tick` at a fixed wall-clock interval. Every agent is edge-triggered
on this tick; no agent uses its own wall-clock timer, so the sim is deterministic
and pausable. The monotonic `tick` counter is the only clock that matters.
"""
from __future__ import annotations

import asyncio
import logging

import aiomqtt

from .bus import Bus

TOPIC_TICK = "grid/tick"

log = logging.getLogger("sim.clock")


def tick_to_sim_time(tick: int, ticks_per_day: int) -> str:
    """Map a tick to an HH:MM sim clock string."""
    frac = (tick % ticks_per_day) / ticks_per_day
    minutes = int(round(frac * 24 * 60)) % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def day_phase(tick: int, ticks_per_day: int) -> float:
    """Fraction (0.0-1.0) through the sim day — drives the irradiance curve."""
    return (tick % ticks_per_day) / ticks_per_day


class Clock:
    def __init__(self, bus: Bus, tick_period_s: float, ticks_per_day: int, max_ticks: int = 0):
        self._bus = bus
        self._period = tick_period_s
        self._ticks_per_day = ticks_per_day
        self._max_ticks = max_ticks  # 0 = run forever
        self.tick = 0

    async def run(self) -> None:
        """Publish ticks forever, surviving broker drops.

        On `MqttError` the clock reconnects (bounded backoff) and resumes from the
        *same* tick — `self.tick` only advances after a successful publish, so the
        monotonic counter never skips or rewinds across a broker outage.
        """
        backoff = 1.0
        while True:
            try:
                async with self._bus:
                    backoff = 1.0
                    while self._max_ticks == 0 or self.tick < self._max_ticks:
                        await self._bus.publish(
                            TOPIC_TICK,
                            {
                                "tick": self.tick,
                                "sim_time": tick_to_sim_time(self.tick, self._ticks_per_day),
                                "day_phase": day_phase(self.tick, self._ticks_per_day),
                            },
                            qos=0,
                        )
                        self.tick += 1
                        await asyncio.sleep(self._period)
                return  # reached max_ticks → done
            except aiomqtt.MqttError as exc:
                log.warning("clock lost broker (%s); reconnecting in %.1fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10.0)
