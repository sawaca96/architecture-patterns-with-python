import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.allocation.adapters.orm import metadata
from app.allocation.domain import models
from app.allocation.service_layer.unit_of_work import ProductUnitOfWork


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


async def test_uow_can_save_product(session: AsyncSession) -> None:
    # Given
    uow = ProductUnitOfWork()

    # When
    async with uow:
        product = models.Product(sku="RETRO-CLOCK", version_number=1, batches=[])
        await uow.repo.add(product)
        await uow.commit()

    # Then
    [[sku]] = await session.execute(sa.text("SELECT sku FROM products"))
    assert sku == "RETRO-CLOCK"


async def test_uow_can_retrieve_product_with_batch_and_allocations(session: AsyncSession) -> None:
    # Given
    await session.execute(
        sa.text("INSERT INTO products (sku, version_number) VALUES " "('RETRO-CLOCK', 1)")
    )
    await session.execute(
        sa.text(
            "INSERT INTO batch (id, sku, qty, eta) VALUES "
            "('9c5d341f-4876-4a54-81f7-720a390884fb',  'RETRO-CLOCK', 100, null)"
        )
    )
    await session.commit()
    uow = ProductUnitOfWork()

    # When
    async with uow:
        product = await uow.repo.get("RETRO-CLOCK")
        line = models.OrderLine(sku="RETRO-CLOCK", qty=10)
        product.allocate(line)
        await uow.commit()

    # Then
    [[batch_id]] = await session.execute(sa.text("SELECT batch_id FROM allocation"))
    assert batch_id == UUID("9c5d341f-4876-4a54-81f7-720a390884fb")


async def test_rollback_uncommitted_work_by_default(session: AsyncSession) -> None:
    # Given
    await session.execute(
        sa.text("INSERT INTO products (sku, version_number) VALUES " "('RETRO-CLOCK', 1)")
    )
    await session.commit()
    uow = ProductUnitOfWork()

    # When
    async with uow:
        product = await uow.repo.get("RETRO-CLOCK")
        batch = models.Batch(sku="RETRO-CLOCK", qty=100, eta=None)
        product.batches.append(batch)

    # Then
    result = await session.execute(sa.text("SELECT * FROM batch"))
    assert list(result) == []


async def test_rollsback_on_error(session: AsyncSession) -> None:
    # Given
    await session.execute(
        sa.text("INSERT INTO products (sku, version_number) VALUES " "('RETRO-CLOCK', 1)")
    )
    await session.commit()

    class MyException(Exception):
        pass

    uow = ProductUnitOfWork()
    with pytest.raises(MyException):
        async with uow:
            product = await uow.repo.get("RETRO-CLOCK")
            batch = models.Batch(sku="RETRO-CLOCK", qty=100, eta=None)
            product.batches.append(batch)
            raise MyException()

    result = await session.execute(sa.text("SELECT * FROM batch"))
    assert list(result) == []


async def test_concurrent_updates_to_version_are_not_allowed(session: AsyncSession) -> None:
    await session.execute(
        sa.text("INSERT INTO products (sku, version_number) VALUES " "('RETRO-CLOCK', 1)")
    )
    await session.execute(
        sa.text(
            "INSERT INTO batch (id, sku, qty, eta) VALUES "
            "('9c5d341f-4876-4a54-81f7-720a390884fb',  'RETRO-CLOCK', 100, null)"
        )
    )
    await session.commit()

    order1 = models.OrderLine(sku="RETRO-CLOCK", qty=3)
    order2 = models.OrderLine(sku="RETRO-CLOCK", qty=7)
    exceptions = []

    async def allocate(order: models.OrderLine) -> None:
        try:
            async with ProductUnitOfWork() as uow:
                product = await uow.repo.get("RETRO-CLOCK")
                await asyncio.sleep(0.1)
                product.allocate(order)
                await uow.commit()
        except Exception as e:
            exceptions.append(e)

    await asyncio.gather(*[allocate(order1), allocate(order2)])
    [exception] = exceptions
    assert "could not serialize access due to concurrent update" in str(exception)

    [[version]] = await session.execute(
        sa.text("SELECT version_number FROM products WHERE sku=:sku"),
        dict(sku="RETRO-CLOCK"),
    )
    assert version == 2

    orders = await session.execute(
        sa.text(
            "SELECT order_line_id FROM allocation"
            " JOIN batch ON allocation.batch_id = batch.id"
            " JOIN order_line ON allocation.order_line_id = order_line.id"
            " WHERE order_line.sku=:sku"
        ),
        dict(sku="RETRO-CLOCK"),
    )
    assert len(orders.all()) == 1
