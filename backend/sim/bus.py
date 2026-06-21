"""The MQTT bus — the ONLY place that touches aiomqtt and JSON (de)serialization.

Every other module talks to the broker through this seam. Centralizing here means:
- JSON encode/decode and the `schema_version`/`ts` envelope live in one place.
- Malformed messages are guarded once.
- Tests can swap in `FakeBus` (same interface, asyncio.Queue) with no broker.

Design: each agent owns its own `Bus` (its own aiomqtt connection). The broker is
the bus — no agent calls another directly. Each `Bus` is an async context manager.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import AsyncIterator

import aiomqtt

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Message:
    """A decoded inbound message: its topic and parsed JSON payload."""
    topic: str
    payload: dict


class Bus:
    """Thin async wrapper over one aiomqtt client connection."""

    def __init__(self, host: str, port: int, client_id: str):
        self._host = host
        self._port = port
        self._client_id = client_id
        self._client: aiomqtt.Client | None = None

    async def __aenter__(self) -> "Bus":
        self._client = aiomqtt.Client(self._host, port=self._port, identifier=self._client_id)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc) -> None:
        assert self._client is not None
        await self._client.__aexit__(*exc)
        self._client = None

    async def subscribe(self, *topic_filters: str, qos: int = 0) -> None:
        assert self._client is not None
        for f in topic_filters:
            await self._client.subscribe(f, qos=qos)

    async def publish(self, topic: str, payload: dict, qos: int = 0, retain: bool = False) -> None:
        """Stamp the envelope (schema_version, ts) and publish as JSON."""
        assert self._client is not None
        body = {"schema_version": SCHEMA_VERSION, "ts": time.time(), **payload}
        await self._client.publish(topic, json.dumps(body), qos=qos, retain=retain)

    async def messages(self) -> AsyncIterator[Message]:
        """Yield decoded inbound messages. Malformed JSON is skipped, not fatal."""
        assert self._client is not None
        async for msg in self._client.messages:
            try:
                payload = json.loads(msg.payload)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(payload, dict):
                continue
            yield Message(topic=str(msg.topic), payload=payload)
