from typing import Any
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture

from app.allocation.adapters.repository import AbstractProductRepository
from app.allocation.domain import models
from app.allocation.service_layer import services, unit_of_work


class FakeRepository(AbstractProductRepository):
    def __init__(self, products: list[models.Product]) -> None:
        self._seen: set[models.Product] = set()
        self._products = set(products)

    async def _add(self, product: models.Product) -> None:
        self._products.add(product)

    async def _get(self, sku: str) -> models.Product:
        return next((p for p in self._products if p.sku == sku), None)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork[AbstractProductRepository]):
    def __init__(self) -> None:
        self._repo = FakeRepository([])
        self.committed = False

    async def __aexit__(self, *args: Any) -> None:
        await self.rollback()

    @property
    def repo(self) -> AbstractProductRepository:
        return self._repo

    async def _commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


async def test_add_batch() -> None:
    # Given
    uow = FakeUnitOfWork()

    # When
    await services.add_batch(uuid4(), "CRUNCHY-ARMCHAIR", 100, None, uow)

    # Then
    assert await uow.repo.get("CRUNCHY-ARMCHAIR") is not None
    assert uow.committed


async def test_add_batch_for_existing_product() -> None:
    # Given
    uow = FakeUnitOfWork()

    # When
    await services.add_batch(
        UUID("766f526a-b73f-45ed-b6b9-00fd964b02e5"), "CRUNCHY-ARMCHAIR", 100, None, uow
    )
    await services.add_batch(
        UUID("46faff56-8729-4f0d-8a8f-75a1dfb3741c"), "CRUNCHY-ARMCHAIR", 99, None, uow
    )

    # Then
    batches = (await uow.repo.get("CRUNCHY-ARMCHAIR")).batches
    assert UUID("766f526a-b73f-45ed-b6b9-00fd964b02e5") in [b.id for b in batches]
    assert UUID("46faff56-8729-4f0d-8a8f-75a1dfb3741c") in [b.id for b in batches]


async def test_allocate_returns_allocated_batch_id() -> None:
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


async def test_allocate_excute_commits() -> None:
    # Given
    uow = FakeUnitOfWork()
    await services.add_batch(uuid4(), "OMINOUS-MIRROR", 100, None, uow)

    # When
    await services.allocate(uuid4(), "OMINOUS-MIRROR", 10, uow)

    # Then
    assert uow.committed


async def test_sends_email_on_out_of_stock_error(mocker: MockerFixture) -> None:
    uow = FakeUnitOfWork()
    await services.add_batch(uuid4(), "OMINOUS-MIRROR", 1, None, uow)

    mock_send_mail = mocker.patch("app.allocation.adapters.email.send_mail")
    await services.allocate(uuid4(), "OMINOUS-MIRROR", 10, uow)
    assert mock_send_mail.call_args == mocker.call(
        "stock@made.com",
        "Out of stock for OMINOUS-MIRROR",
    )
