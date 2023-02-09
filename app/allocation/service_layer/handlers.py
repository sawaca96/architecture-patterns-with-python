from uuid import UUID

from app.allocation.adapters import email
from app.allocation.adapters.repository import AbstractProductRepository
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
    line = models.OrderLine(id=cmd.order_id, sku=cmd.sku, qty=cmd.qty)
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


def send_out_of_stock_notification(
    event: events.OutOfStock, uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository]
) -> None:
    email.send("stock@made.com", f"Out of stock for {event.sku}")
