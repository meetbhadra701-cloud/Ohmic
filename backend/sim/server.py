"""WebSocket broadcast server — the frontend integration seam.

Subscribes to every MQTT topic, maintains a latest-value cache, and broadcasts
one superset JSON frame per ``grid/tick`` to all connected WebSocket clients.
The frame shape is defined verbatim in ``CONTRACTS/websocket_api.md``.

Optional client→server chaos commands are validated and relayed to MQTT::

    { "type": "chaos", "target": "PV_01", "action": "kill" | "restore" }

Run via ``runner.build_server(cfg, run_id).run()`` alongside the sim tasks.
"""
from __future__ import annotations

import asyncio
import json
import logging

import websockets
import websockets.exceptions

from .bus import SCHEMA_VERSION, Bus

log = logging.getLogger(__name__)

# Topics this server subscribes to (order doesn't matter — asyncio delivers all).
_MQTT_SUBS_QOS0 = ["grid/tick"]
_MQTT_SUBS_QOS1 = ["node/+/state", "market/clearing", "grid/alert"]

KNOWN_NODES = {"PV_01", "BESS_01", "LOAD_CAMPUS"}
KNOWN_ACTIONS = {"kill", "restore"}


class WebSocketServer:
    """MQTT subscriber + WebSocket broadcaster.

    One instance per sim run.  Owns its own Bus connection so it can
    publish chaos relay commands back onto the broker.
    """

    def __init__(self, bus: Bus, cfg: dict) -> None:
        self._bus = bus
        self._ws_host = cfg["websocket"]["host"]
        self._ws_port = int(cfg["websocket"]["port"])
        self._node_cfg = cfg["nodes"]

        # --- Latest-value caches (updated as MQTT messages arrive) ---
        self._tick_payload: dict = {}
        self._node_state: dict[str, dict] = {}   # node_id -> last state payload
        self._clearing: dict = {}
        # Current grid-wide mode: "NORMAL" | "CRITICAL"
        self._alert_level: str = "NORMAL"
        # Alerts accumulated since the last tick broadcast (flushed each tick).
        self._pending_alerts: list[dict] = []
        # Last assembled frame — sent immediately to any late-joining client.
        self._last_frame: dict | None = None

        # Connected WebSocket clients.
        self._clients: set = set()

    # ------------------------------------------------------------------ public

    async def run(self) -> None:
        """Main coroutine: open MQTT connection and start WS listener."""
        async with self._bus:
            await self._bus.subscribe(*_MQTT_SUBS_QOS0, qos=0)
            await self._bus.subscribe(*_MQTT_SUBS_QOS1, qos=1)
            log.info("WebSocket server listening on ws://%s:%s",
                     self._ws_host, self._ws_port)
            async with websockets.serve(self._ws_handler, self._ws_host, self._ws_port):
                async for msg in self._bus.messages():
                    await self._on_mqtt(msg)

    # ------------------------------------------------------------------ MQTT

    async def _on_mqtt(self, msg) -> None:
        p = msg.payload

        if msg.topic == "grid/tick":
            self._tick_payload = p
            frame = self._assemble()
            self._last_frame = frame
            self._pending_alerts.clear()
            raw = json.dumps(frame)
            dead: list = []
            for client in list(self._clients):
                try:
                    await client.send(raw)
                except websockets.exceptions.ConnectionClosed:
                    dead.append(client)
            for d in dead:
                self._clients.discard(d)

        elif msg.topic.endswith("/state"):
            nid = p.get("node_id")
            if nid:
                self._node_state[nid] = p

        elif msg.topic == "market/clearing":
            self._clearing = p

        elif msg.topic == "grid/alert":
            level = p.get("level", "NORMAL")
            # "ALL_CLEAR" transitions back to NORMAL.
            self._alert_level = "NORMAL" if level == "ALL_CLEAR" else level
            self._pending_alerts.append({
                "level": level,
                "type": p.get("type"),
                "detail": p.get("detail"),
                "tick": p.get("tick"),
            })

    # ------------------------------------------------------------------ Frame assembly

    def _assemble(self) -> dict:
        tp = self._tick_payload
        solar_id = self._node_cfg["solar"]["id"]
        batt_id = self._node_cfg["battery"]["id"]
        load_id = self._node_cfg["load"]["id"]

        pv = self._node_state.get(solar_id, {})
        batt = self._node_state.get(batt_id, {})
        load = self._node_state.get(load_id, {})

        # Solar is alive only if the last state said so AND the grid is not CRITICAL.
        # When killed, solar stops publishing, so cached state.alive stays True —
        # the alert_level override is what drives alive→False for the UI.
        pv_alive = pv.get("alive", True) and self._alert_level != "CRITICAL"

        nodes = {
            solar_id: {
                "type": "solar",
                "output_kw": pv.get("output_kw", 0.0),
                "alive": pv_alive,
                "health": pv.get("health", "nominal"),
            },
            batt_id: {
                "type": "battery",
                "soc": batt.get("soc", 0.0),
                "soc_percent": round(batt.get("soc", 0.0) * 100.0, 1),
                "flow_kw": batt.get("flow_kw", 0.0),
                "max_discharge_kw": batt.get("max_discharge_kw", 0.0),
                "mode": batt.get("mode", "market"),
                "ask_price_usd_kwh": batt.get("ask_price_usd_kwh"),
                "unmet_kw": batt.get("unmet_kw", 0.0),
                "health": batt.get("health", "nominal"),
            },
            load_id: {
                "type": "load",
                "demand_kw": load.get("demand_kw", 0.0),
                "critical_kw": load.get("critical_kw", 0.0),
                "served_kw": load.get("served_kw", 0.0),
                "shed_kw": load.get("shed_kw", 0.0),
                "health": load.get("health", "nominal"),
            },
        }

        cl = self._clearing
        flows = [
            {
                "from": m["seller"],
                "to": m["buyer"],
                "kw": m["kw"],
                "curtailed_kw": m.get("curtailed_kw", 0.0),
            }
            for m in cl.get("matches", [])
        ]
        market = {
            "clearing_price_usd_kwh": cl.get("clearing_price_usd_kwh"),
            "flows": flows,
            "unmet_kw": cl.get("unmet_kw", 0.0),
            "surplus_kw": cl.get("surplus_kw", 0.0),
            "curtailed_kw": cl.get("curtailed_kw", 0.0),
            "per_line_flow_kw": cl.get("per_line_flow_kw", {}),
        }

        forecast = {
            "predicted_demand_kw": load.get("predicted_demand_kw", 0.0),
            "horizon_ticks": load.get("forecast_horizon_ticks", 0),
            "actual_demand_kw": load.get("demand_kw", 0.0),
            "cond": load.get("ridge_cond"),
            "reanchor_count": load.get("ridge_reanchor_count", 0),
            "warm": load.get("ridge_warm", False),
        }

        return {
            "schema_version": SCHEMA_VERSION,
            "tick": tp.get("tick", 0),
            "sim_time": tp.get("sim_time", "00:00"),
            "day_phase": tp.get("day_phase", 0.0),
            "mode": self._alert_level,
            "nodes": nodes,
            "market": market,
            "forecast": forecast,
            "alerts": list(self._pending_alerts),
        }

    # ------------------------------------------------------------------ WebSocket

    async def _ws_handler(self, ws) -> None:
        self._clients.add(ws)
        # Immediately push the latest frame so a late client isn't blank.
        if self._last_frame is not None:
            try:
                await ws.send(json.dumps(self._last_frame))
            except websockets.exceptions.ConnectionClosed:
                self._clients.discard(ws)
                return
        try:
            async for raw in ws:
                await self._relay_chaos(raw)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)

    async def _relay_chaos(self, raw: str) -> None:
        try:
            cmd = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return
        if cmd.get("type") != "chaos":
            return
        target = cmd.get("target")
        action = cmd.get("action")
        if target not in KNOWN_NODES or action not in KNOWN_ACTIONS:
            log.warning("Ignored invalid chaos command: %r", cmd)
            return
        await self._bus.publish("chaos/command", {"target": target, "action": action}, qos=1)
