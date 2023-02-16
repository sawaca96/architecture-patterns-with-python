from uuid import UUID, uuid4

import orjson

from app.allocation.adapters import email
from app.allocation.adapters.redis import redis
from app.allocation.adapters.repository import AbstractProductRepository
from app.allocation.constants import LINE_ALLOCATED_CHANNEL
from app.allocation.domain import commands, events, models
from app.allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


async def add_batch(
    cmd: commands.CreateBatch,
    uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository],
) -> None:
    async with uow:
        product = await uow.repo.get(cmd.sku)
        if product is None:
            product = models.Product(sku=cmd.sku, batches=[])
            await uow.repo.add(product)
        product.batches.append(models.Batch(id=cmd.id, sku=cmd.sku, qty=cmd.qty, eta=cmd.eta))
        await uow.commit()


async def allocate(
    cmd: commands.Allocate,
    uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository],
) -> UUID:
    line = models.OrderLine(id=uuid4(), sku=cmd.sku, qty=cmd.qty)
    async with uow:
        product = await uow.repo.get(line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch_id = product.allocate(line)
        await uow.commit()
        return batch_id


async def change_batch_quantity(
    cmd: commands.ChangeBatchQuantity,
    uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository],
) -> None:
    async with uow:
        product = await uow.repo.get_by_batch_id(cmd.id)
        product.change_batch_quantity(cmd.id, cmd.qty)
        await uow.commit()


def send_out_of_stock_notification(event: events.OutOfStock) -> None:
    email.send("stock@made.com", f"Out of stock for {event.sku}")


async def publish_allocated_event(event: events.Allocated) -> None:
    await redis.publish(
        LINE_ALLOCATED_CHANNEL,
        orjson.dumps(
            dict(
                order_id=str(event.order_id),
                sku=event.sku,
                qty=event.qty,
                batch_id=str(event.batch_id),
            )
        ),
    )
