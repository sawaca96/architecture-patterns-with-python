import asyncio
from uuid import UUID

import orjson
import sqlalchemy as sa

from app.allocation.adapters.db import DB
from app.allocation.adapters.orm import start_mappers
from app.allocation.adapters.redis import redis
from app.allocation.constants import BATCH_QUANTITY_CHANGED_CHANNEL, ORDER_ALLOCATED_CHANNEL, ORDER_DEALLOCATED_CHANNEL
from app.allocation.domain import commands, events
from app.allocation.service_layer import handlers, unit_of_work
from app.config import config

start_mappers()
db = DB(config.PG_DSN)


async def main() -> None:
    pubsub = redis.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(BATCH_QUANTITY_CHANGED_CHANNEL, ORDER_ALLOCATED_CHANNEL, ORDER_DEALLOCATED_CHANNEL)

    async for m in pubsub.listen():
        channel = m["channel"].decode("utf-8")
        data = orjson.loads(m["data"])
        if channel == BATCH_QUANTITY_CHANGED_CHANNEL:
            await handlers.ChangeBatchQuantityCmdHandler(unit_of_work.PGUnitOfWork()).handle(
                commands.ChangeBatchQuantity(id=UUID(data["id"]), qty=data["qty"]),
            )
        elif channel == ORDER_ALLOCATED_CHANNEL:
            await _add_allocation_to_read_model(
                events.Allocated(
                    order_id=UUID(data["order_id"]), sku=data["sku"], qty=data["qty"], batch_id=UUID(data["batch_id"])
                ),
            )
        elif channel == ORDER_DEALLOCATED_CHANNEL:
            event = events.Deallocated(order_id=UUID(data["order_id"]), sku=data["sku"], qty=data["qty"])
            await _remove_allocation_from_read_model(event)
            await _remove_order(event)
            await handlers.AllocateCmdHandler(unit_of_work.PGUnitOfWork()).handle(
                commands.Allocate(order_id=event.order_id, sku=event.sku, qty=event.qty)
            )


async def _add_allocation_to_read_model(event: events.Allocated) -> None:
    async with db.session() as session:
        await session.execute(
            sa.text("INSERT INTO allocations_view (order_id, sku, batch_id) VALUES (:order_id, :sku, :batch_id)"),
            dict(order_id=event.order_id, sku=event.sku, batch_id=event.batch_id),
        )


async def _remove_order(event: events.Deallocated) -> None:
    async with db.session() as session:
        await session.execute(
            sa.text('DELETE FROM "order" WHERE id = :order_id'),
            dict(order_id=event.order_id),
        )


async def _remove_allocation_from_read_model(event: events.Deallocated) -> None:
    async with db.session() as session:
        await session.execute(
            sa.text("DELETE FROM allocations_view WHERE order_id = :order_id AND sku = :sku"),
            dict(order_id=event.order_id, sku=event.sku),
        )


if __name__ == "__main__":
    asyncio.run(main())
