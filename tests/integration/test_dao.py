from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.allocation.adapters import dao
from app.allocation.adapters.dto import Allocation


async def test_allocations_view(session: AsyncSession) -> None:
    # Given
    await session.execute(
        sa.text("INSERT INTO allocations_view (order_id, sku, batch_id) VALUES (:order_id, :sku, :batch_id)"),
        dict(
            order_id=UUID("b0764de0-5348-47b0-9895-6dabce8e093f"),
            sku="sku1",
            batch_id=UUID("5ed8a924-d4d7-41c4-af06-0bb85248ed6b"),
        ),
    )
    await session.execute(
        sa.text('INSERT INTO "order" (id, sku, qty) VALUES (:order_id, :sku, :qty)'),
        dict(order_id=UUID("b0764de0-5348-47b0-9895-6dabce8e093f"), sku="sku1", qty=22),
    )
    await session.execute(
        sa.text("INSERT INTO allocations_view (order_id, sku, batch_id) VALUES (:order_id, :sku, :batch_id)"),
        dict(
            order_id=UUID("4f7e2d27-f2f7-4741-927b-02d1384a1d2c"),
            sku="sku2",
            batch_id=UUID("450fac40-d02c-43a4-b9cb-f63d75c0a2e6"),
        ),
    )
    await session.execute(
        sa.text('INSERT INTO "order" (id, sku, qty) VALUES (:order_id, :sku, :qty)'),
        dict(order_id=UUID("4f7e2d27-f2f7-4741-927b-02d1384a1d2c"), sku="sku2", qty=33),
    )

    # When
    result = await dao.allocations("sku1", session)

    # Then
    assert result == [
        Allocation(
            order_id=UUID("b0764de0-5348-47b0-9895-6dabce8e093f"),
            sku="sku1",
            qty=22,
            batch_id=UUID("5ed8a924-d4d7-41c4-af06-0bb85248ed6b"),
        )
    ]
