from typing import Protocol, TypeVar
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


P = TypeVar("P", contravariant=True)
R = TypeVar("R", covariant=True)


class Handler(Protocol[P, R]):
    async def handle(self, cmd: P) -> R:
        ...


class CreateBatchCmdHandler(Handler[commands.CreateBatch, models.Batch]):
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository]) -> None:
        self._uow = uow

    async def handle(self, cmd: commands.CreateBatch) -> models.Batch:
        async with self._uow:
            product = await self._uow.repo.get(cmd.sku)
            if product is None:
                product = models.Product(sku=cmd.sku, batches=[])
                await self._uow.repo.add(product)
            batch = models.Batch(id=cmd.id, sku=cmd.sku, qty=cmd.qty, eta=cmd.eta)
            product.batches.append(batch)
            await self._uow.commit()
            return batch


class AllocateCmdHandler(Handler[commands.Allocate, UUID]):
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository]) -> None:
        self._uow = uow

    async def handle(self, cmd: commands.Allocate) -> UUID:
        line = models.OrderLine(id=uuid4(), sku=cmd.sku, qty=cmd.qty)
        async with self._uow:
            product = await self._uow.repo.get(line.sku)
            if product is None:
                raise InvalidSku(f"Invalid sku {line.sku}")
            batch_id = product.allocate(line)
            if batch_id is None:
                self._send_email(events.OutOfStock(line.sku))
            else:
                await self._publish(events.Allocated(line.id, line.sku, line.qty, batch_id))
            await self._uow.commit()
            return batch_id

    def _send_email(self, event: events.OutOfStock) -> None:
        email.send("stock@made.com", f"Out of stock for {event.sku}")

    async def _publish(self, event: events.Allocated) -> None:
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


class ChangeBatchQuantityCmdHandler(Handler[commands.ChangeBatchQuantity, list[commands.Allocate]]):
    def __init__(self, uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository]) -> None:
        self._uow = uow

    async def handle(self, cmd: commands.ChangeBatchQuantity) -> list[commands.Allocate]:
        async with self._uow:
            product = await self._uow.repo.get_by_batch_id(cmd.id)
            lines = product.change_batch_quantity(cmd.id, cmd.qty)
            results = [commands.Allocate(line.sku, line.qty) for line in lines]
            await self._uow.commit()
            return results
