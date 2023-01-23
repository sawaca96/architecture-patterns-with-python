from typing import Any
from uuid import UUID, uuid4

import pytest

from app.allocation.adapters.repository import AbstractBatchRepository
from app.allocation.domain import models
from app.allocation.service_layer import services, unit_of_work


class FakeRepository(AbstractBatchRepository):
    def __init__(self, batches: list[models.Batch]) -> None:
        self._batches = set(batches)

    async def add(self, batch: models.Batch) -> None:
        self._batches.add(batch)

    async def get(self, id: UUID) -> models.Batch:
        return next(b for b in self._batches if b.id == id)

    async def list(self) -> list[models.Batch]:
        return list(self._batches)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork[AbstractBatchRepository]):
    def __init__(self) -> None:
        self.batches = FakeRepository([])
        self.committed = False

    async def __aexit__(self, *args: Any) -> None:
        await self.rollback()

    @property
    def repo(self) -> AbstractBatchRepository:
        return self.batches

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


async def test_add_batch() -> None:
    # Given
    uow = FakeUnitOfWork()

    # When
    await services.add_batch(
        UUID("3a80e50e-22f4-4907-afb3-8aa37e0c27b8"), "CRUNCHY-ARMCHAIR", 100, None, uow
    )

    # Then
    assert await uow.batches.get(UUID("3a80e50e-22f4-4907-afb3-8aa37e0c27b8")) is not None
    assert uow.committed


async def test_allocate_returns_allocation() -> None:
    # Given
    uow = FakeUnitOfWork()
    await services.add_batch(
        UUID("f0e9d78e-ccc7-4f9b-a0e9-4b286b6d8ca5"), "OMINOUS-MIRROR", 100, None, uow
    )

    # When
    result = await services.allocate(uuid4(), "OMINOUS-MIRROR", 10, uow)

    # Then
    assert result == UUID("f0e9d78e-ccc7-4f9b-a0e9-4b286b6d8ca5")


async def test_allocate_error_for_invalid_sku() -> None:
    # Given
    uow = FakeUnitOfWork()
    await services.add_batch(uuid4(), "SKU", 100, None, uow)

    # When & Then
    with pytest.raises(services.InvalidSku, match="Invalid sku UNKNOWN"):
        await services.allocate(uuid4(), "UNKNOWN", 10, uow)


async def test_allocate_commits() -> None:
    # Given
    uow = FakeUnitOfWork()
    await services.add_batch(uuid4(), "OMINOUS-MIRROR", 100, None, uow)

    # When
    await services.allocate(uuid4(), "OMINOUS-MIRROR", 10, uow)

    # Then
    assert uow.committed
