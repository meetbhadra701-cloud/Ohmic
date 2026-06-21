"""Bus test doubles and run isolation."""
import asyncio

import pytest

from sim.bus import FakeBroker, FakeBus, new_run_id


async def _filters_other_run_ids():
    broker = FakeBroker()
    run_a = new_run_id("a")
    run_b = new_run_id("b")

    async with FakeBus(broker, "publisher-a", run_id=run_a) as pub_a:
        await pub_a.publish("node/PV_01/state", {"tick": 1, "node_id": "PV_01"}, retain=True)

    async with FakeBus(broker, "subscriber-b", run_id=run_b) as sub_b:
        await sub_b.subscribe("node/+/state")
        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(0.05):
                await anext(sub_b.messages())


def test_fake_bus_filters_other_run_ids():
    asyncio.run(_filters_other_run_ids())


async def _delivers_matching_retained_run():
    broker = FakeBroker()
    run_id = new_run_id("same")

    async with FakeBus(broker, "publisher", run_id=run_id) as pub:
        await pub.publish("grid/alert", {"tick": 7, "level": "CRITICAL"}, retain=True)

    async with FakeBus(broker, "subscriber", run_id=run_id) as sub:
        await sub.subscribe("grid/alert")
        async with asyncio.timeout(0.05):
            msg = await anext(sub.messages())

    assert msg.retain is True
    assert msg.payload["run_id"] == run_id
    assert msg.payload["level"] == "CRITICAL"


def test_fake_bus_delivers_matching_retained_run():
    asyncio.run(_delivers_matching_retained_run())
