from datetime import date
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models


async def test_order_line_mapper_can_load_lines(session: AsyncSession) -> None:
    # Gievn
    await session.execute(
        sa.text(
            "INSERT INTO order_line (id, sku, qty) VALUES "
            "('6da2848c-9617-4f6b-8cb7-094f881ee87b', 'OMINOUS-MIRROR', 12),"
            "('74384460-a74c-44e4-a22a-152ab91a6058', 'GOTHIC-ARMCHAIR', 13),"
            "('9e9c74c3-fbf7-4d4f-a5c6-b6b168333c64', 'BLUE_TABLE', 14)"
        )
    )
    expected = [
        models.OrderLine(
            id=UUID("6da2848c-9617-4f6b-8cb7-094f881ee87b"), sku="OMINOUS-MIRROR", qty=12
        ),
        models.OrderLine(
            id=UUID("74384460-a74c-44e4-a22a-152ab91a6058"), sku="GOTHIC-ARMCHAIR", qty=13
        ),
        models.OrderLine(id=UUID("9e9c74c3-fbf7-4d4f-a5c6-b6b168333c64"), sku="BLUE_TABLE", qty=14),
    ]

    # When
    result = await session.execute(sa.select(models.OrderLine))

    # Then
    assert [r[0] for r in result.fetchall()] == expected


async def test_order_line_mapper_can_save_lines(session: AsyncSession) -> None:
    # Given
    line = models.OrderLine(
        id=UUID("280e4fbf-ec1b-4d7f-b61c-096cd02a5c6a"), sku="OMINOUS-MIRROR", qty=12
    )

    # When
    session.add(line)
    await session.flush()

    # Then
    rows = await session.execute(sa.text("SELECT id, sku, qty FROM order_line"))
    assert rows.fetchall() == [(UUID("280e4fbf-ec1b-4d7f-b61c-096cd02a5c6a"), "OMINOUS-MIRROR", 12)]


async def test_retrieving_batches(session: AsyncSession) -> None:
    # Given
    await session.execute(
        sa.text(
            "INSERT INTO batch (id, sku, purchased_quantity, eta) VALUES "
            "('fa3310b7-2a44-4f0b-be0e-cf6ba8e201fb', 'RETRO-CLOCK', 100, null),"
            "('db14a922-e95b-481c-ac67-476ca819e96d', 'MINIMALIST-SPOON', 100, '2011-01-02')"
        )
    )
    expected = [
        models.Batch(UUID("fa3310b7-2a44-4f0b-be0e-cf6ba8e201fb"), "RETRO-CLOCK", 100, eta=None),
        models.Batch(
            UUID("db14a922-e95b-481c-ac67-476ca819e96d"),
            "MINIMALIST-SPOON",
            100,
            eta=date(2011, 1, 2),
        ),
    ]

    # When
    result = await session.execute(sa.select(models.Batch))

    # Then
    assert [r[0] for r in result.fetchall()] == expected


async def test_saving_batches(session: AsyncSession) -> None:
    # Given
    batch = models.Batch(UUID("c7b6f091-bc25-458b-9027-1aa52fc3d9e1"), "RETRO-CLOCK", 100, eta=None)

    # When
    session.add(batch)
    await session.flush()

    # Then
    rows = await session.execute(sa.text("SELECT id, sku, purchased_quantity, eta FROM batch"))
    assert rows.fetchall() == [
        (UUID("c7b6f091-bc25-458b-9027-1aa52fc3d9e1"), "RETRO-CLOCK", 100, None)
    ]


async def test_saving_allocations(session: AsyncSession) -> None:
    # Given
    batch = models.Batch(UUID("9ef1794c-617b-4634-82e6-dda1f466ea72"), "RETRO-CLOCK", 100, eta=None)
    line = models.OrderLine(
        sku="RETRO-CLOCK", qty=10, id=UUID("591bf188-50e8-4279-904a-bcec100d966b")
    )

    # When
    batch.allocate(line)
    session.add(batch)
    await session.flush()

    # Then
    rows = await session.execute(sa.text("SELECT order_line_id, batch_id FROM allocation"))
    assert rows.fetchall() == [
        (UUID("591bf188-50e8-4279-904a-bcec100d966b"), UUID("9ef1794c-617b-4634-82e6-dda1f466ea72"))
    ]


async def test_retrieving_allocations(session: AsyncSession) -> None:
    # Given
    await session.execute(
        sa.text(
            "INSERT INTO order_line (id, sku, qty) VALUES "
            "('530ff94e-207f-428f-8857-fc41d0dc55c4', 'RETRO-CLOCK', 10)"
        )
    )
    [[order_line_id]] = await session.execute(
        sa.text(
            "SELECT id FROM order_line WHERE id=:id AND sku =:sku",
        ),
        dict(id=UUID("530ff94e-207f-428f-8857-fc41d0dc55c4"), sku="RETRO-CLOCK"),
    )
    await session.execute(
        sa.text(
            "INSERT INTO batch (id, sku, purchased_quantity, eta) VALUES "
            "('9c5d341f-4876-4a54-81f7-720a390884fb',  'RETRO-CLOCK', 100, null)"
        )
    )
    [[batch_id]] = await session.execute(
        sa.text(
            "SELECT id FROM batch WHERE id=:id AND sku =:sku",
        ),
        dict(id=UUID("9c5d341f-4876-4a54-81f7-720a390884fb"), sku="RETRO-CLOCK"),
    )
    await session.execute(
        sa.text(
            "INSERT INTO allocation (order_line_id, batch_id) VALUES (:order_line_id, :batch_id)"
        ),
        dict(order_line_id=order_line_id, batch_id=batch_id),
    )

    # When
    result = await session.execute(
        sa.select(models.Batch)
        .where(models.Batch.id == batch_id)
        .options(selectinload(models.Batch.allocations))
    )
    batch: models.Batch = result.scalar_one()
    assert batch.allocations == {
        models.OrderLine(id=UUID("530ff94e-207f-428f-8857-fc41d0dc55c4"), sku="RETRO-CLOCK", qty=10)
    }
