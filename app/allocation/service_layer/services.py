from uuid import UUID

from app.allocation.adapters.repository import BatchAbstractRepository
from app.allocation.domain import models
from app.allocation.domain.models import OrderLine


class InvalidSku(Exception):
    pass


async def allocate(line: OrderLine, repo: BatchAbstractRepository) -> UUID:
    batches = await repo.list()
    if not _is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batch_id = models.allocate(line, batches)
    return batch_id


def _is_valid_sku(sku: str, batches: list[models.Batch]) -> bool:
    return sku in {b.sku for b in batches}
