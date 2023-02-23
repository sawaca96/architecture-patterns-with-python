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
from app.allocation.service_layer.unit_of_work import PGUnitOfWork


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


async def test_uow_can_save_product(session: AsyncSession) -> None:
    # Given
    uow = PGUnitOfWork()

    # When
    async with uow:
        product = models.Product(sku="RETRO-CLOCK", version_number=1, batches=[])
        await uow.products.add(product)
        await uow.commit()

    # Then
    [[sku]] = await session.execute(sa.text("SELECT sku FROM product"))
    assert sku == "RETRO-CLOCK"


async def test_uow_can_retrieve_product_with_batch_and_allocations(session: AsyncSession) -> None:
    # Given
    await session.execute(sa.text("INSERT INTO product (sku, version_number) VALUES ('RETRO-CLOCK', 1)"))
    await session.execute(
        sa.text(
            "INSERT INTO batch (id, sku, qty, eta) VALUES "
            "('9c5d341f-4876-4a54-81f7-720a390884fb',  'RETRO-CLOCK', 100, null)"
        )
    )
    await session.commit()
    uow = PGUnitOfWork()

    # When
    async with uow:
        product = await uow.products.get("RETRO-CLOCK")
        order = models.Order(sku="RETRO-CLOCK", qty=10)
        product.allocate(order)
        await uow.commit()

    # Then
    [[batch_id]] = await session.execute(sa.text("SELECT batch_id FROM allocation"))
    assert batch_id == UUID("9c5d341f-4876-4a54-81f7-720a390884fb")


async def test_rollback_uncommitted_work_by_default(session: AsyncSession) -> None:
    # Given
    await session.execute(sa.text("INSERT INTO product (sku, version_number) VALUES " "('RETRO-CLOCK', 1)"))
    await session.commit()
    uow = PGUnitOfWork()

    # When
    async with uow:
        product = await uow.products.get("RETRO-CLOCK")
        batch = models.Batch(sku="RETRO-CLOCK", qty=100, eta=None)
        product.batches.append(batch)

    # Then
    result = await session.execute(sa.text("SELECT * FROM batch"))
    assert list(result) == []


async def test_rollsback_on_error(session: AsyncSession) -> None:
    # Given
    await session.execute(sa.text("INSERT INTO product (sku, version_number) VALUES " "('RETRO-CLOCK', 1)"))
    await session.commit()

    class MyException(Exception):
        pass

    uow = PGUnitOfWork()
    with pytest.raises(MyException):
        async with uow:
            product = await uow.products.get("RETRO-CLOCK")
            batch = models.Batch(sku="RETRO-CLOCK", qty=100, eta=None)
            product.batches.append(batch)
            raise MyException()

    result = await session.execute(sa.text("SELECT * FROM batch"))
    assert list(result) == []


async def test_concurrent_updates_to_version_are_not_allowed(session: AsyncSession) -> None:
    await session.execute(sa.text("INSERT INTO product (sku, version_number) VALUES " "('RETRO-CLOCK', 1)"))
    await session.execute(
        sa.text(
            "INSERT INTO batch (id, sku, qty, eta) VALUES "
            "('9c5d341f-4876-4a54-81f7-720a390884fb',  'RETRO-CLOCK', 100, null)"
        )
    )
    await session.commit()

    order1 = models.Order(sku="RETRO-CLOCK", qty=3)
    order2 = models.Order(sku="RETRO-CLOCK", qty=7)
    exceptions = []

    async def allocate(order: models.Order) -> None:
        try:
            async with PGUnitOfWork() as uow:
                product = await uow.products.get("RETRO-CLOCK")
                product.allocate(order)
                await asyncio.sleep(0.1)
                await uow.commit()
        except Exception as e:
            exceptions.append(e)

    await asyncio.gather(*[allocate(order1), allocate(order2)])
    [exception] = exceptions
    assert "UPDATE statement on table 'product' expected to update 1 row(s); 0 were matched." in str(exception)

    [[version]] = await session.execute(
        sa.text("SELECT version_number FROM product WHERE sku=:sku"),
        dict(sku="RETRO-CLOCK"),
    )
    assert version == 2

    orders = await session.execute(
        sa.text(
            "SELECT order_id FROM allocation"
            " JOIN batch ON allocation.batch_id = batch.id"
            ' JOIN "order" ON allocation.order_id = "order".id'
            ' WHERE "order".sku=:sku'
        ),
        dict(sku="RETRO-CLOCK"),
    )
    assert len(orders.all()) == 1


async def test_get_by_batch_id(session: AsyncSession) -> None:
    b1 = models.Batch(id=UUID("c1dac0a1-b8e8-4052-a7e4-67061204d4d9"), sku="sku1", qty=100, eta=None)
    b2 = models.Batch(id=UUID("c3f04384-8fdf-4d89-8616-9efec913092f"), sku="sku1", qty=100, eta=None)
    b3 = models.Batch(id=UUID("cf15ab56-082a-4495-8422-b42cbb5ac1e5"), sku="sku2", qty=100, eta=None)
    p1 = models.Product(sku="sku1", batches=[b1, b2])
    p2 = models.Product(sku="sku2", batches=[b3])
    session.add(p1)
    session.add(p2)
    await session.commit()

    async with PGUnitOfWork() as uow:
        actual1 = await uow.products.get_by_batch_id(UUID("c1dac0a1-b8e8-4052-a7e4-67061204d4d9"))
        actual2 = await uow.products.get_by_batch_id(UUID("c3f04384-8fdf-4d89-8616-9efec913092f"))
        actual3 = await uow.products.get_by_batch_id(UUID("cf15ab56-082a-4495-8422-b42cbb5ac1e5"))
        assert actual1.sku == "sku1"
        assert actual2.sku == "sku1"
        assert actual3.sku == "sku2"
        await uow.commit()
