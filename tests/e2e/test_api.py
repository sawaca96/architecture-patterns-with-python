from collections.abc import AsyncGenerator
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.allocation.adapters.orm import metadata
from app.allocation.routers.api import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, Any]:
    async with AsyncClient(
        app=app,
        base_url="http://testserver",
        headers={"Content-Type": "application/json"},
    ) as client:
        yield client


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, Any]:
    session = sessionmaker(bind=engine, class_=AsyncSession)()
    yield session
    await session.close()


@pytest.fixture(autouse=True)
async def clear_db(session: AsyncSession) -> AsyncGenerator[Any, Any]:
    yield session
    for table in reversed(metadata.sorted_tables):
        await session.execute(table.delete())


async def test_add_batch_returns_201(client: AsyncClient, session: AsyncSession) -> None:
    # Given
    await session.execute(
        sa.text("INSERT INTO products (sku, version_number) VALUES " "('SKU', 1)")
    )
    await session.commit()

    # When
    res = await client.post(
        "/batches", json={"batch_id": str(uuid4()), "sku": "SKU", "quantity": 3}
    )

    # Then
    assert res.status_code == 201
    assert res.json() == {"message": "success"}


async def test_allocate_api_returns_201_and_allocated_batch(
    session: AsyncSession, client: AsyncClient
) -> None:
    # Given: create 3 batches with different eta. 2 batches have same sku
    await session.execute(
        sa.text("INSERT INTO products (sku, version_number) VALUES " "('SKU', 1)")
    )
    await session.execute(
        sa.text("INSERT INTO products (sku, version_number) VALUES " "('OTHER-SKU', 1)")
    )
    await session.commit()
    batches = [
        (UUID("d236f2aa-8f61-4aeb-9cbd-eade21736457"), "SKU", 100, date(2011, 1, 2)),
        (UUID("f6e16413-441e-40c0-b2eb-e826b080b448"), "SKU", 100, date(2011, 1, 1)),
        (UUID("504d8ed7-b0d2-40ae-9e77-0de52489ec43"), "OTHER-SKU", 100, None),
    ]
    for id, sku, qty, eta in batches:
        await session.execute(
            sa.text("INSERT INTO batch (id, sku, qty, eta) " "VALUES (:id, :sku, :qty, :eta)"),
            dict(id=id, sku=sku, qty=qty, eta=eta),
        )
        await session.commit()

    # When
    res = await client.post(
        "/allocate", json={"line_id": str(uuid4()), "sku": "SKU", "quantity": 3}
    )

    # Then: order line is allocated to the batch with earliest eta, and status code 201
    assert res.status_code == 201
    assert res.json() == {"batch_id": "f6e16413-441e-40c0-b2eb-e826b080b448"}


async def test_allocate_api_returns_400_and_error_message_if_invalid_sku(
    client: AsyncClient,
) -> None:
    # When: request with invalid sku
    res = await client.post(
        "/allocate", json={"line_id": str(uuid4()), "sku": "NOT-EXIST-SKU", "quantity": 3}
    )

    # Then: status code 400 and error message
    assert res.status_code == 400
    assert res.json() == {"detail": "Invalid sku NOT-EXIST-SKU"}
