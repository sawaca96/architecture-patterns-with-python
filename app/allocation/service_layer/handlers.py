from typing import Protocol, TypeVar
from uuid import UUID

import orjson

from app.allocation.adapters import email
from app.allocation.adapters.redis import redis
from app.allocation.constants import ORDER_ALLOCATED_CHANNEL, ORDER_DEALLOCATED_CHANNEL
from app.allocation.domain import commands, events, models
from app.allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


P = TypeVar("P", contravariant=True)
R = TypeVar("R", covariant=True)


class Handler(Protocol[P, R]):
    async def handle(self, cmd: P) -> R:
        ...


class CreateBatchCmdHandler(Handler[commands.CreateBatch, models.Batch]):
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork) -> None:
        self._uow = uow

    async def handle(self, cmd: commands.CreateBatch) -> models.Batch:
        async with self._uow:
            product = await self._uow.products.get(cmd.sku)
            if product is None:
                product = models.Product(sku=cmd.sku, batches=[])
                await self._uow.products.add(product)
            batch = models.Batch(id=cmd.id, sku=cmd.sku, qty=cmd.qty, eta=cmd.eta)
            product.batches.append(batch)
            await self._uow.commit()
            return batch


class AllocateCmdHandler(Handler[commands.Allocate, UUID]):
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork) -> None:
        self._uow = uow

    async def handle(self, cmd: commands.Allocate) -> UUID:
        order = models.Order(id=cmd.order_id, sku=cmd.sku, qty=cmd.qty)
        async with self._uow:
            product = await self._uow.products.get(order.sku)
            if product is None:
                raise InvalidSku(f"Invalid sku {order.sku}")
            batch_id = product.allocate(order)
            if batch_id is None:
                self._send_email(events.OutOfStock(order.sku))
            else:
                await self._publish(events.Allocated(order.id, order.sku, order.qty, batch_id))
            await self._uow.commit()
            return batch_id

    def _send_email(self, event: events.OutOfStock) -> None:
        email.send("stock@made.com", f"Out of stock for {event.sku}")

    async def _publish(self, event: events.Allocated) -> None:
        await redis.publish(
            ORDER_ALLOCATED_CHANNEL,
            orjson.dumps(
                dict(
                    order_id=str(event.order_id),
                    sku=event.sku,
                    qty=event.qty,
                    batch_id=str(event.batch_id),
                )
            ),
        )


class ChangeBatchQuantityCmdHandler(Handler[commands.ChangeBatchQuantity, None]):
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork) -> None:
        self._uow = uow

    async def handle(self, cmd: commands.ChangeBatchQuantity) -> None:
        async with self._uow:
            product = await self._uow.products.get_by_batch_id(cmd.id)
            orders = product.change_batch_quantity(cmd.id, cmd.qty)
            deallocated_events = [events.Deallocated(order.id, order.sku, order.qty) for order in orders]
            if deallocated_events:
                await self._publish(deallocated_events)
            await self._uow.commit()

    async def _publish(self, event: list[events.Deallocated]) -> None:
        pipe = redis.pipeline()
        for e in event:
            pipe.publish(
                ORDER_DEALLOCATED_CHANNEL,
                orjson.dumps(dict(order_id=str(e.order_id), sku=e.sku, qty=e.qty)),
            )
        await pipe.execute()
