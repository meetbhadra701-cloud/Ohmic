#!/usr/bin/env python3
"""Step 0 gate: prove the broker + aiomqtt + asyncio plumbing works.

Publishes one message to a test topic and asserts we receive it back.
Exit 0 on success, non-zero on failure. Run after `brew services start mosquitto`:

    .venv/bin/python backend/scripts/smoke_mqtt.py
"""
import asyncio
import json
import sys

import aiomqtt

HOST = "localhost"
PORT = 1883
TOPIC = "smoke/test"
PAYLOAD = {"hello": "microgrid", "n": 42}


async def main() -> int:
    async with aiomqtt.Client(HOST, port=PORT) as client:
        await client.subscribe(TOPIC)
        await client.publish(TOPIC, json.dumps(PAYLOAD))
        async with asyncio.timeout(5):
            async for message in client.messages:
                received = json.loads(message.payload)
                assert received == PAYLOAD, f"mismatch: {received!r}"
                print(f"OK: round-tripped {received} on {message.topic}")
                return 0
    return 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except (aiomqtt.MqttError, asyncio.TimeoutError) as exc:
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        print("Is mosquitto running? `brew services start mosquitto`", file=sys.stderr)
        sys.exit(2)
