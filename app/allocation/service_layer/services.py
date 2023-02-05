from datetime import date
from uuid import UUID

from app.allocation.adapters.repository import AbstractProductRepository
from app.allocation.domain import models
from app.allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


async def add_batch(
    batch_id: UUID,
    sku: str,
    qty: int,
    eta: date | None,
    uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository],
) -> None:
    async with uow:
        product = await uow.repo.get(sku)
        if product is None:
            product = models.Product(sku=sku, batches=[])
            await uow.repo.add(product)
        product.batches.append(models.Batch(id=batch_id, sku=sku, qty=qty, eta=eta))
        await uow.commit()


async def allocate(
    line_id: UUID,
    sku: str,
    qty: int,
    uow: unit_of_work.AbstractUnitOfWork[AbstractProductRepository],
) -> UUID:
    line = models.OrderLine(id=line_id, sku=sku, qty=qty)
    async with uow:
        product = await uow.repo.get(line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch_id = product.allocate(line)
        await uow.commit()
        return batch_id
