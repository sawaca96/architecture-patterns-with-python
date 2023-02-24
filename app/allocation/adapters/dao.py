import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.allocation.adapters.dto import Allocation


async def allocations(sku: str, session: AsyncSession) -> list[Allocation]:
    result = await session.execute(
        sa.text(
            "SELECT allocations_view.order_id, allocations_view.batch_id, "
            'allocations_view.sku, "order".qty FROM allocations_view JOIN "order" '
            'ON allocations_view.order_id = "order".id WHERE allocations_view.sku = :sku'
        ),
        dict(sku=sku),
    )
    return [Allocation(**dict(r)) for r in result.fetchall()]
