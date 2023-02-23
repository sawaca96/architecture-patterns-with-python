from collections.abc import AsyncGenerator
from typing import Any

import orjson
import pytest
from httpx import AsyncClient
from redis.asyncio.client import PubSub
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.allocation.adapters.orm import metadata
from app.allocation.adapters.redis import Redis
from app.allocation.constants import BATCH_QUANTITY_CHANGED_CHANNEL, ORDER_ALLOCATED_CHANNEL, ORDER_DEALLOCATED_CHANNEL
from app.allocation.entrypoints.restapi import app
from app.config import config


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, Any]:
    async with AsyncClient(
        app=app,
        base_url="http://testserver",
        headers={"Content-Type": "application/json"},
    ) as client:
        yield client


@pytest.fixture
async def rc() -> AsyncGenerator[Redis, None]:
    rc = Redis.from_url(config.REDIS_DSN)
    yield rc
    await rc.flushall()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, Any]:
    session = sessionmaker(bind=engine, class_=AsyncSession)()
    yield session
    await session.close()


@pytest.fixture(autouse=True)
async def clear_db(engine: AsyncEngine) -> AsyncGenerator[Any, Any]:
    yield engine
    async with engine.begin() as conn:
        for table in reversed(metadata.sorted_tables):
            await conn.execute(table.delete())


async def test_allocate_leading_to_add_row_to_allocations_view(client: AsyncClient) -> None:
    # Given: create batch
    earlist_batch_id, _ = await _create_two_batches(client)

    # When: allocate order
    allocate_res = await client.post("/allocate", json={"sku": "SKU", "quantity": 10})
    view_res = await client.get("/allocations/SKU")

    # Then: order is allocated. and allocations_view returns the allocation
    assert allocate_res.status_code == 201
    assert allocate_res.json()["batch_id"] == earlist_batch_id
    assert view_res.status_code == 200
    assert view_res.json()[0]["sku"] == "SKU"
    assert view_res.json()[0]["batch_id"] == earlist_batch_id
    assert view_res.json()[0]["qty"] == 10


async def test_change_batch_quantity_leading_to_reallocation(client: AsyncClient, rc: Redis) -> None:
    # Given: create batch and subscribe redis channels
    earlist_batch_id, latest_batch_id = await _create_two_batches(client)
    await client.post("/allocate", json={"sku": "SKU", "quantity": 10})
    pubsub = await _subscribe(rc)

    # When
    await rc.publish(
        BATCH_QUANTITY_CHANGED_CHANNEL,
        orjson.dumps({"id": earlist_batch_id, "qty": 5}),
    )

    # Then
    message1 = await pubsub.get_message(timeout=1)
    message2 = await pubsub.get_message(timeout=1)
    data1 = orjson.loads(message1["data"])
    assert message1["channel"].decode() == ORDER_DEALLOCATED_CHANNEL
    assert data1["sku"] == "SKU"
    assert data1["qty"] == 10
    data2 = orjson.loads(message2["data"])
    assert message2["channel"].decode() == ORDER_ALLOCATED_CHANNEL
    assert data2["sku"] == "SKU"
    assert data2["qty"] == 10
    assert data2["batch_id"] == latest_batch_id


async def _subscribe(rc: Redis) -> PubSub:
    pubsub = rc.pubsub()
    await pubsub.subscribe(ORDER_ALLOCATED_CHANNEL, ORDER_DEALLOCATED_CHANNEL)
    confirmation1 = await pubsub.get_message(timeout=1)
    confirmation2 = await pubsub.get_message(timeout=1)
    assert confirmation1["type"] == "subscribe"
    assert confirmation2["type"] == "subscribe"
    return pubsub


async def _create_two_batches(client: AsyncClient) -> tuple[str, str]:
    res1 = await client.post(
        "/batches",
        json={
            "sku": "SKU",
            "quantity": 10,
            "eta": "2021-01-01",
        },
    )
    res2 = await client.post(
        "/batches",
        json={
            "sku": "SKU",
            "quantity": 10,
            "eta": "2021-01-02",
        },
    )
    return res1.json()["batch_id"], res2.json()["batch_id"]
