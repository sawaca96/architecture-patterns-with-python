from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, repository


async def test_repository_can_save_a_batch_with_allocations(session: AsyncSession) -> None:
    # Given
    order_line = models.OrderLine(
        id=UUID("13785f9d-c4e1-4e2b-a789-bc8d2309ce34"), sku="RETRO-CLOCK", qty=10
    )
    batch = models.Batch(UUID("b463867c-e573-4a71-bd51-282f32763ee9"), "RETRO-CLOCK", 100, eta=None)
    batch.allocate(order_line)
    repo = repository.PGBatchRepository(session)

    # When
    await repo.add(batch)

    # Then
    rows = await session.execute(sa.text("SELECT id, sku, purchased_quantity, eta FROM batch"))
    assert list(rows) == [(UUID("b463867c-e573-4a71-bd51-282f32763ee9"), "RETRO-CLOCK", 100, None)]
    rows = await session.execute(sa.text("SELECT order_line_id, batch_id FROM allocation"))
    assert list(rows) == [
        (UUID("13785f9d-c4e1-4e2b-a789-bc8d2309ce34"), UUID("b463867c-e573-4a71-bd51-282f32763ee9"))
    ]


async def test_repository_can_retrieve_a_batch_with_allocations(session: AsyncSession) -> None:
    # Given: create two batches and allocate one to an order
    order_line = models.OrderLine(
        id=UUID("97c5289f-aa4e-4c5f-8c9b-4b9f7597a7bd"), sku="RETRO-CLOCK", qty=10
    )
    batch1 = models.Batch(UUID("0194c5bc-20af-4fd1-82bf-324e5f26fce7"), "RETRO-CLOCK", 100, None)
    batch2 = models.Batch(
        UUID("ecd13d3d-c9ee-4a4f-9b1f-c9356ac668ab"), "MINIMALIST-SPOON", 100, None
    )
    session.add(order_line)
    session.add(batch1)
    session.add(batch2)
    batch1.allocate(order_line)
    # add is not automatically flushed, so I manual flush to refer to the batch in the next step.
    await session.flush()

    # When
    repo = repository.PGBatchRepository(session)
    result = await repo.get(batch1.id)

    # Then
    assert result.id == UUID("0194c5bc-20af-4fd1-82bf-324e5f26fce7")
    assert result.sku == "RETRO-CLOCK"
    assert result.purchased_quantity == 100
    assert result.available_quantity == 90
    assert list(result.allocations) == [order_line]


async def test_repository_can_fetch_batch_list(session: AsyncSession) -> None:
    # Given: create two batches and allocate one to an order
    batch1 = models.Batch(UUID("5518eac3-b214-448a-bd1c-f49bb92c4ed9"), "SKU-1", 100, None)
    batch2 = models.Batch(UUID("48ad28ea-d799-4b05-9a18-e3b5b34212a6"), "SKU-2", 100, None)
    session.add(batch1)
    session.add(batch2)
    # add is not automatically flushed, so I manual flush to refer to the batch in the next step.
    await session.flush()

    # When
    repo = repository.PGBatchRepository(session)
    result = await repo.list()

    # Then
    assert result == [batch1, batch2]
