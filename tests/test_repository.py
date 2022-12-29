import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, repository


async def test_repository_can_save_a_batch(session: AsyncSession) -> None:
    # When
    batch = models.Batch("batch1", "RETRO-CLOCK", 100, eta=None)

    repo = repository.SqlAlchemyRepository(session)
    repo.add(batch)
    await session.commit()
    rows = await session.execute(
        sa.text("SELECT reference, sku, purchased_quantity, eta FROM batch")
    )
    assert list(rows) == [("batch1", "RETRO-CLOCK", 100, None)]


async def test_repository_can_retrieve_a_batch_with_allocations(session: AsyncSession) -> None:
    # Given: create two batches and allocate one to an order
    orderline = models.Orderline("order1", "RETRO-CLOCK", 10)
    batch1 = models.Batch("batch1", "RETRO-CLOCK", 100, None)
    batch2 = models.Batch("batch2", "MINIMALIST-SPOON", 100, None)
    session.add(orderline)
    session.add(batch1)
    session.add(batch2)
    batch1.allocate(orderline)
    await session.commit()

    # When
    repo = repository.SqlAlchemyRepository(session)
    result = await repo.get(batch1.id)

    # # Then
    assert result.reference == "batch1"
    assert result.sku == "RETRO-CLOCK"
    assert result.purchased_quantity == 100
    assert result.available_quantity == 90
