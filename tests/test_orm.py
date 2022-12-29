from datetime import date

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models


async def test_orderline_mapper_can_load_lines(session: AsyncSession) -> None:
    await session.execute(
        sa.text(
            "INSERT INTO orderline (reference, sku, qty) VALUES "
            "('order1', 'OMINOUS-MIRROR', 12),"
            "('order1', 'GOTHIC-ARMCHAIR', 13),"
            "('order3', 'BLUE_TABLE', 14)"
        )
    )
    expected = [
        models.Orderline("order1", "OMINOUS-MIRROR", 12),
        models.Orderline("order1", "GOTHIC-ARMCHAIR", 13),
        models.Orderline("order3", "BLUE_TABLE", 14),
    ]
    result = await session.execute(sa.select(models.Orderline))
    assert [r[0] for r in result.fetchall()] == expected


async def test_orderline_mapper_can_save_lines(session: AsyncSession) -> None:
    line = models.Orderline("order1", "OMINOUS-MIRROR", 12)
    session.add(line)
    await session.commit()

    rows = await session.execute(sa.text("SELECT reference, sku, qty FROM orderline"))
    assert rows.fetchall() == [("order1", "OMINOUS-MIRROR", 12)]


async def test_retrieving_batches(session: AsyncSession) -> None:
    await session.execute(
        sa.text(
            "INSERT INTO batch (reference, sku, purchased_quantity, eta) VALUES "
            "('batch1', 'RETRO-CLOCK', 100, null),"
            "('batch2', 'MINIMALIST-SPOON', 100, '2011-01-02')"
        )
    )
    expected = [
        models.Batch("batch1", "RETRO-CLOCK", 100, eta=None),
        models.Batch("batch2", "MINIMALIST-SPOON", 100, eta=date(2011, 1, 2)),
    ]
    result = await session.execute(sa.select(models.Batch))
    assert [r[0] for r in result.fetchall()] == expected


async def test_saving_batches(session: AsyncSession) -> None:
    batch = models.Batch("batch1", "RETRO-CLOCK", 100, eta=None)
    session.add(batch)
    await session.commit()

    rows = await session.execute(
        sa.text("SELECT reference, sku, purchased_quantity, eta FROM batch")
    )
    assert rows.fetchall() == [("batch1", "RETRO-CLOCK", 100, None)]


async def test_saving_allocations(session: AsyncSession) -> None:
    # Given
    batch = models.Batch("batch1", "RETRO-CLOCK", 100, eta=None)
    line = models.Orderline("order1", "RETRO-CLOCK", 10)

    # When
    batch.allocate(line)
    session.add(batch)
    await session.commit()

    # Then
    rows = await session.execute(sa.text("SELECT orderline_id, batch_id FROM allocation"))
    # TODO: 모델엔 id가 없는데 쿼리결과엔 존재함
    assert rows.fetchall() == [(batch.id, line.id)]


async def test_retrieving_allocations(session: AsyncSession) -> None:
    # Given
    await session.execute(
        sa.text(
            "INSERT INTO orderline (id, reference, sku, qty) VALUES "
            "(1, 'order1', 'RETRO-CLOCK', 10)"
        )
    )
    [[orderline_id]] = await session.execute(
        sa.text(
            "SELECT id FROM orderline WHERE reference=:reference AND sku =:sku",
        ),
        dict(reference="order1", sku="RETRO-CLOCK"),
    )
    await session.execute(
        sa.text(
            "INSERT INTO batch (id, reference, sku, purchased_quantity, eta) VALUES "
            "(1, 'batch1', 'RETRO-CLOCK', 100, null)"
        )
    )
    [[batch_id]] = await session.execute(
        sa.text(
            "SELECT id FROM batch WHERE reference=:reference AND sku =:sku",
        ),
        dict(reference="batch1", sku="RETRO-CLOCK"),
    )
    await session.execute(
        sa.text(
            "INSERT INTO allocation (orderline_id, batch_id) VALUES (:orderline_id, :batch_id)"
        ),
        dict(orderline_id=orderline_id, batch_id=batch_id),
    )

    # When
    result = await session.execute(
        sa.select(models.Batch)
        .where(models.Batch.id == batch_id)
        .options(selectinload(models.Batch._allocations))
    )
    batch = result.scalar_one()
    assert batch._allocations == {models.Orderline("order1", "RETRO-CLOCK", 10)}
