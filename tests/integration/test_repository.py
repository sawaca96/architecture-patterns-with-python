from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.allocation.adapters import repository
from app.allocation.domain import models


async def test_repository_can_save_a_batch_with_allocations(session: AsyncSession) -> None:
    # Given
    order_line = models.OrderLine(
        id=UUID("13785f9d-c4e1-4e2b-a789-bc8d2309ce34"), sku="RETRO-CLOCK", qty=10
    )
    batch = models.Batch(
        id=UUID("b463867c-e573-4a71-bd51-282f32763ee9"), sku="RETRO-CLOCK", qty=100
    )
    batch.allocate(order_line)
    repo = repository.PGBatchRepository(session)

    # When
    await repo.add(batch)

    # Then
    rows = await session.execute(sa.text("SELECT id, sku, qty, eta FROM batch"))
    assert list(rows) == [(UUID("b463867c-e573-4a71-bd51-282f32763ee9"), "RETRO-CLOCK", 100, None)]
    rows = await session.execute(sa.text("SELECT order_line_id, batch_id FROM allocation"))
    assert list(rows) == [
        (UUID("13785f9d-c4e1-4e2b-a789-bc8d2309ce34"), UUID("b463867c-e573-4a71-bd51-282f32763ee9"))
    ]


async def test_repository_can_retrieve_a_batch_with_allocations(session: AsyncSession) -> None:
    # Given: create two batches and allocate one to an order
    order_line = models.OrderLine(sku="RETRO-CLOCK", qty=10)
    batch1 = models.Batch(
        id=UUID("0194c5bc-20af-4fd1-82bf-324e5f26fce7"), sku="RETRO-CLOCK", qty=100
    )
    batch2 = models.Batch(sku="MINIMALIST-SPOON", qty=100)
    session.add(order_line)
    session.add(batch1)
    session.add(batch2)
    batch1.allocate(order_line)
    # 'add' method doesn't automatically flushed, so manual flush is required to refer batch
    await session.flush()

    # When
    repo = repository.PGBatchRepository(session)
    result = await repo.get(batch1.id)

    # Then
    assert result.id == UUID("0194c5bc-20af-4fd1-82bf-324e5f26fce7")
    assert result.sku == "RETRO-CLOCK"
    assert result.qty == 100
    assert result.available_quantity == 90
    assert list(result.allocations) == [order_line]


async def test_repository_can_fetch_batch_list(session: AsyncSession) -> None:
    # Given: create two batches and allocate one to an order
    batch1 = models.Batch(sku="SKU-1", qty=100)
    batch2 = models.Batch(sku="SKU-2", qty=100)
    session.add(batch1)
    session.add(batch2)
    # 'add' method doesn't automatically flushed, so manual flush is required to refer batch
    await session.flush()

    # When
    repo = repository.PGBatchRepository(session)
    result = await repo.list()

    # Then
    assert result == [batch1, batch2]
