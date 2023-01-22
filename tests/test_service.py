from uuid import UUID

import pytest

from app import models, services
from app.repository import BatchAbstractRepository


class FakeRepository(BatchAbstractRepository):
    def __init__(self, batches: list[models.Batch]) -> None:
        self._batches = set(batches)

    def add(self, batch: models.Batch) -> None:
        self._batches.add(batch)

    async def get(self, id: UUID) -> models.Batch:
        return next(b for b in self._batches if b.id == id)

    async def list(self) -> list[models.Batch]:
        return list(self._batches)


async def test_returns_allocation() -> None:
    # Given
    lint = models.OrderLine(id=UUID("4382a3d5-e3eb-44cd-972b-3a90e793060b"), sku="SKU", qty=10)
    batch = models.Batch(UUID("f0e9d78e-ccc7-4f9b-a0e9-4b286b6d8ca5"), "SKU", 100, eta=None)
    repo = FakeRepository([batch])

    # When
    result = await services.allocate(lint, repo)

    # Then
    assert result == UUID("f0e9d78e-ccc7-4f9b-a0e9-4b286b6d8ca5")


async def test_error_for_invalid_sku() -> None:
    # Given
    lint = models.OrderLine(id=UUID("7970dba1-6d92-47e8-9664-f512493febfc"), sku="UNKNOWN", qty=10)
    batch = models.Batch(UUID("1cb92bac-98aa-421c-afe6-7cbba08b050c"), "SKU", 100, eta=None)
    repo = FakeRepository([batch])

    # When & Then
    with pytest.raises(services.InvalidSku, match="Invalid sku UNKNOWN"):
        await services.allocate(lint, repo)
