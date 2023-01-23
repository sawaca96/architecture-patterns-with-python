from datetime import date
from uuid import UUID

from app.allocation.adapters.repository import AbstractBatchRepository
from app.allocation.domain import models
from app.allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


async def add_batch(
    batch_id: UUID,
    sku: str,
    qty: int,
    eta: date | None,
    uow: unit_of_work.AbstractUnitOfWork[AbstractBatchRepository],
) -> None:
    async with uow:
        await uow.repo.add(models.Batch(id=batch_id, sku=sku, qty=qty, eta=eta))
        await uow.commit()


async def allocate(
    line_id: UUID, sku: str, qty: int, uow: unit_of_work.AbstractUnitOfWork[AbstractBatchRepository]
) -> UUID:
    line = models.OrderLine(id=line_id, sku=sku, qty=qty)
    async with uow:
        batches = await uow.repo.list()
        if not _is_valid_sku(line.sku, batches):
            raise InvalidSku(f"Invalid sku {line.sku}")
        batch_id = models.allocate(line, batches)
        await uow.commit()
    return batch_id


def _is_valid_sku(sku: str, batches: list[models.Batch]) -> bool:
    return sku in {b.sku for b in batches}
