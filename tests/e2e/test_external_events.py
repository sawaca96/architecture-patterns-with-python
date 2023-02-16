from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import orjson
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.allocation.adapters.redis import Redis
from app.allocation.constants import BATCH_QUANTITY_CHANGED_CHANNEL, LINE_ALLOCATED_CHANNEL
from app.allocation.routers.api import app
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


async def test_change_batch_quantity_leading_to_reallocation(
    client: AsyncClient, rc: Redis, engine: AsyncEngine
) -> None:
    # Given
    await client.post(
        "/batches",
        json={
            "batch_id": "96a3b8cd-f2db-481f-894b-60d6c6bc3c42",
            "sku": "SKU",
            "quantity": 10,
            "eta": "2021-01-01",
        },
    )
    await client.post(
        "/batches",
        json={
            "batch_id": "5a63ca86-94e0-4146-8e72-6d79cf3ae0c2",
            "sku": "SKU",
            "quantity": 10,
            "eta": "2021-01-02",
        },
    )
    res = await client.post(
        "/allocate", json={"line_id": str(uuid4()), "sku": "SKU", "quantity": 10}
    )
    assert res.json() == {"batch_id": "96a3b8cd-f2db-481f-894b-60d6c6bc3c42"}

    pubsub = rc.pubsub()
    await pubsub.subscribe(LINE_ALLOCATED_CHANNEL)
    confirmation = await pubsub.get_message(timeout=1)
    assert confirmation["type"] == "subscribe"

    # When
    await rc.publish(
        BATCH_QUANTITY_CHANGED_CHANNEL,
        orjson.dumps({"id": "96a3b8cd-f2db-481f-894b-60d6c6bc3c42", "qty": 5}),
    )

    # Then
    message = await pubsub.get_message(timeout=1)
    data = orjson.loads(message["data"])
    assert data["batch_id"] == "5a63ca86-94e0-4146-8e72-6d79cf3ae0c2"
