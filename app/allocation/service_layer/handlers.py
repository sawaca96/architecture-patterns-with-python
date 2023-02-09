from uuid import UUID

from app.allocation.adapters import email
from app.allocation.adapters.repository import AbstractProductRepository
from app.allocation.domain import events, models
from app.allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


async def add_batch(
    event: events.BatchCreated,
    uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository],
) -> None:
    async with uow:
        product = await uow.repo.get(event.sku)
        if product is None:
            product = models.Product(sku=event.sku, batches=[])
            await uow.repo.add(product)
        product.batches.append(
            models.Batch(id=event.id, sku=event.sku, qty=event.qty, eta=event.eta)
        )
        await uow.commit()


async def allocate(
    event: events.AllocationRequired,
    uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository],
) -> UUID:
    line = models.OrderLine(id=event.order_id, sku=event.sku, qty=event.qty)
    async with uow:
        product = await uow.repo.get(line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch_id = product.allocate(line)
        await uow.commit()
        return batch_id


async def change_batch_quantity(
    event: events.BatchQuantityChanged,
    uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository],
) -> None:
    async with uow:
        product = await uow.repo.get_by_batch_id(event.id)
        product.change_batch_quantity(event.id, event.qty)
        await uow.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock, uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository]
) -> None:
    email.send("stock@made.com", f"Out of stock for {event.sku}")
