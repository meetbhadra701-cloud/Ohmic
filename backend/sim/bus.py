"""The MQTT bus — the ONLY place that touches aiomqtt and JSON (de)serialization.

Every other module talks to the broker through this seam. Centralizing here means:
- JSON encode/decode and the `schema_version`/`ts` envelope live in one place.
- Malformed messages are guarded once.
- Tests can swap in `FakeBus` (same interface, asyncio.Queue) with no broker.

Design: each agent owns its own `Bus` (its own aiomqtt connection). The broker is
the bus — no agent calls another directly. Each `Bus` is an async context manager.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import AsyncIterator, Iterable

import aiomqtt

SCHEMA_VERSION = 1


def new_run_id(prefix: str = "run") -> str:
    """Create a short run id for isolating retained MQTT state between sim runs."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass(frozen=True)
class Message:
    """A decoded inbound message: its topic and parsed JSON payload."""
    topic: str
    payload: dict
    retain: bool = False    # True if the broker delivered this as a retained message


class Bus:
    """Thin async wrapper over one aiomqtt client connection."""

    def __init__(self, host: str, port: int, client_id: str, run_id: str | None = None):
        self._host = host
        self._port = port
        self._run_id = run_id
        self._client_id = f"{client_id}-{run_id[:8]}" if run_id else client_id
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
        run_part = {"run_id": self._run_id} if self._run_id else {}
        body = {"schema_version": SCHEMA_VERSION, "ts": time.time(), **run_part, **payload}
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
            if self._run_id and payload.get("run_id") != self._run_id:
                continue
            yield Message(topic=str(msg.topic), payload=payload, retain=bool(msg.retain))


def _topic_matches(topic_filter: str, topic: str) -> bool:
    """MQTT-ish topic filter matching for the in-memory FakeBus."""
    f_parts = topic_filter.split("/")
    t_parts = topic.split("/")
    for i, part in enumerate(f_parts):
        if part == "#":
            return True
        if i >= len(t_parts):
            return False
        if part != "+" and part != t_parts[i]:
            return False
    return len(f_parts) == len(t_parts)


class FakeBroker:
    """Small in-memory broker for deterministic tests."""

    def __init__(self) -> None:
        self._subscribers: list[tuple[tuple[str, ...], asyncio.Queue[Message]]] = []
        self._retained: dict[str, dict] = {}

    def subscribe(self, filters: Iterable[str], queue: asyncio.Queue[Message]) -> None:
        fs = tuple(filters)
        self._subscribers.append((fs, queue))
        for topic, payload in self._retained.items():
            if any(_topic_matches(f, topic) for f in fs):
                queue.put_nowait(Message(topic=topic, payload=payload.copy(), retain=True))

    def unsubscribe(self, queue: asyncio.Queue[Message]) -> None:
        self._subscribers = [(fs, q) for fs, q in self._subscribers if q is not queue]

    def publish(self, topic: str, payload: dict, retain: bool = False) -> None:
        if retain:
            self._retained[topic] = payload.copy()
        for filters, queue in list(self._subscribers):
            if any(_topic_matches(f, topic) for f in filters):
                queue.put_nowait(Message(topic=topic, payload=payload.copy(), retain=False))


class FakeBus:
    """In-memory Bus-compatible test double.

    It preserves the same envelope stamping and run_id filtering as Bus, but avoids
    network timing and retained state from external Mosquitto runs.
    """

    def __init__(self, broker: FakeBroker, client_id: str, run_id: str | None = None):
        self._broker = broker
        self._client_id = client_id
        self._run_id = run_id
        self._queue: asyncio.Queue[Message] = asyncio.Queue()

    async def __aenter__(self) -> "FakeBus":
        return self

    async def __aexit__(self, *exc) -> None:
        self._broker.unsubscribe(self._queue)

    async def subscribe(self, *topic_filters: str, qos: int = 0) -> None:
        _ = qos
        self._broker.subscribe(topic_filters, self._queue)

    async def publish(self, topic: str, payload: dict, qos: int = 0, retain: bool = False) -> None:
        _ = qos
        run_part = {"run_id": self._run_id} if self._run_id else {}
        body = {"schema_version": SCHEMA_VERSION, "ts": time.time(), **run_part, **payload}
        self._broker.publish(topic, body, retain=retain)

    async def messages(self) -> AsyncIterator[Message]:
        while True:
            msg = await self._queue.get()
            if self._run_id and msg.payload.get("run_id") != self._run_id:
                continue
            yield msg
