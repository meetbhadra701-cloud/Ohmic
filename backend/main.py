#!/usr/bin/env python3
"""Sim + WebSocket server entrypoint.

Starts Mosquitto (if not already running), then runs the full sim and the
WebSocket broadcast server on one asyncio event loop. Press Ctrl-C to stop.

    .venv/bin/python backend/main.py
"""
from __future__ import annotations

import asyncio
import logging
import pathlib
import subprocess
import sys
import time

# Make `sim` importable when run from the repo root.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from sim.bus import new_run_id
from sim.config import load_config
from sim.runner import build_server, build_sim

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")


def _ensure_mosquitto(cfg: dict) -> None:
    """Start Mosquitto via brew services if the port isn't already answering."""
    import socket
    host = cfg["mqtt"]["host"]
    port = int(cfg["mqtt"]["port"])
    with socket.socket() as s:
        s.settimeout(1.0)
        try:
            s.connect((host, port))
            log.info("Mosquitto already listening on %s:%s", host, port)
            return
        except OSError:
            pass
    log.info("Starting Mosquitto via brew services ...")
    subprocess.run(["brew", "services", "start", "mosquitto"], check=False)
    # Give it a moment to bind.
    for _ in range(20):
        time.sleep(0.2)
        with socket.socket() as s:
            s.settimeout(0.5)
            try:
                s.connect((host, port))
                log.info("Mosquitto up.")
                return
            except OSError:
                continue
    log.warning("Mosquitto may not be running; proceeding anyway.")


async def main() -> None:
    cfg = load_config()
    _ensure_mosquitto(cfg)
    run_id = new_run_id("main")

    clock, agents = build_sim(cfg, log=log.info, run_id=run_id)
    server = build_server(cfg, run_id=run_id)

    log.info("Starting sim (run_id=%s) + WebSocket server on ws://%s:%s ...",
             run_id, cfg["websocket"]["host"], cfg["websocket"]["port"])

    tasks = (
        [asyncio.create_task(clock.run(), name="clock")]
        + [asyncio.create_task(a.run(), name=a.node_id) for a in agents]
        + [asyncio.create_task(server.run(), name="ws_server")]
    )
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        log.info("Stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
