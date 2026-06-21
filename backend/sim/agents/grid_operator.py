"""Grid Operator (Auctioneer).

Collects bids/asks, clears a continuous double auction, enforces physical
feasibility (line-capacity curtailment), and publishes the result. Also detects
missing heartbeats and raises/clears the fault alert.

Timing: orders published during tick T's window are cleared two ticks later (when
tick T+2 arrives). The 2-tick settlement grace guarantees every agent's order has
arrived in the bucket regardless of task-scheduling order across the (single
event loop) clients. Settlement latency is 2 ticks — fine for a discrete-tick sim.
"""
from __future__ import annotations

from ..physics.clearing import Order, clear
from ..physics.network import feasible_flows, lines_from_config, single_feeder_route
from .base import TOPIC_TICK, BaseAgent

TOPIC_BIDS = "market/bids"
TOPIC_ASKS = "market/asks"
TOPIC_CLEARING = "market/clearing"
TOPIC_ALERT = "grid/alert"


class GridOperatorAgent(BaseAgent):
    def __init__(self, bus, cfg, log=None):
        super().__init__(bus, "GRID_OP")
        self.lines = lines_from_config(cfg)
        self.route = single_feeder_route(next(iter(self.lines)))
        self.miss_threshold = cfg["heartbeat"]["miss_threshold"]
        self.clear_consecutive = cfg["heartbeat"]["clear_consecutive"]
        self.monitored = [cfg["nodes"]["solar"]["id"]]
        self._log = log or (lambda _m: None)
        self.orders: dict[int, dict[str, list[Order]]] = {}
        self.beats: dict[int, set[str]] = {}
        self.missed: dict[str, int] = {n: 0 for n in self.monitored}
        self.good: dict[str, int] = {n: 0 for n in self.monitored}
        self.state = "NORMAL"            # "NORMAL" | "CRITICAL"

    def subscriptions(self) -> list[str]:
        return [TOPIC_TICK, TOPIC_BIDS, TOPIC_ASKS, "node/+/heartbeat"]

    async def on_message(self, msg):
        if msg.topic == TOPIC_BIDS:
            self._record(msg.payload, "bids", Order(msg.payload["agent_id"], msg.payload["max_price_usd_kwh"], msg.payload["volume_kw"]))
        elif msg.topic == TOPIC_ASKS:
            self._record(msg.payload, "asks", Order(msg.payload["agent_id"], msg.payload["min_price_usd_kwh"], msg.payload["volume_kw"]))
        elif msg.topic.endswith("/heartbeat"):
            self.beats.setdefault(msg.payload["tick"], set()).add(msg.payload["node_id"])
        else:
            await super().on_message(msg)

    def _record(self, payload: dict, side: str, order: Order) -> None:
        self.orders.setdefault(payload["tick"], {"bids": [], "asks": []})[side].append(order)

    SETTLE_GRACE = 2                      # ticks of slack so every order has arrived

    async def on_tick(self, tick: dict) -> None:
        t = tick["tick"]
        settle = t - self.SETTLE_GRACE    # clear a fully-collected book
        if settle >= 0:
            await self._settle(settle)
            await self._detect_faults(settle, t)
        # housekeeping: drop buckets older than the just-settled tick
        for old in [k for k in self.orders if k < settle]:
            self.orders.pop(old, None)
        for old in [k for k in self.beats if k < settle]:
            self.beats.pop(old, None)

    async def _settle(self, settle: int) -> None:
        book = self.orders.get(settle, {"bids": [], "asks": []})
        result = clear(book["bids"], book["asks"])
        feas = feasible_flows(result.matches, self.lines, self.route)
        matches_payload = [
            {"buyer": b["buyer"], "seller": b["seller"], "kw": b["delivered_kw"],
             "curtailed_kw": b["curtailed_kw"], "reason": b["reason"]}
            for b in feas.breakdown
        ]
        await self.bus.publish(
            TOPIC_CLEARING,
            {"tick": settle,
             "clearing_price_usd_kwh": result.clearing_price_usd_kwh,
             "matches": matches_payload,
             "unmet_kw": result.unmet_kw,
             "surplus_kw": result.surplus_kw,
             "curtailed_kw": feas.curtailed_kw,
             "per_line_flow_kw": feas.per_line_flow_kw},
            qos=1, retain=True,
        )

    async def _detect_faults(self, settle: int, now: int) -> None:
        for node in self.monitored:
            present = node in self.beats.get(settle, set())
            if present:
                self.missed[node] = 0
                self.good[node] += 1
            else:
                self.missed[node] += 1
                self.good[node] = 0

            if self.state == "NORMAL" and self.missed[node] >= self.miss_threshold:
                self.state = "CRITICAL"
                await self._raise_alert(now, "CRITICAL", "SOLAR_LOSS",
                                        f"{node} missed {self.missed[node]} heartbeats")
            elif self.state == "CRITICAL" and self.good[node] >= self.clear_consecutive:
                self.state = "NORMAL"
                await self._raise_alert(now, "ALL_CLEAR", "SOLAR_LOSS",
                                        f"{node} heartbeats resumed")

    async def _raise_alert(self, tick: int, level: str, type_: str, detail: str) -> None:
        self._log(f"ALERT {level} {type_} @ tick {tick}: {detail}")
        await self.bus.publish(
            TOPIC_ALERT, {"tick": tick, "level": level, "type": type_, "detail": detail},
            qos=1, retain=True,
        )
