# pylint: disable=no-self-use
from datetime import date
from typing import Any
from unittest import mock
from uuid import UUID, uuid4

import pytest

from app.allocation.adapters import repository
from app.allocation.domain import commands, models
from app.allocation.service_layer import handlers, messagebus, unit_of_work


class FakeRepository(repository.AbstractProductRepository):
    def __init__(self, products: list[models.Product]) -> None:
        super().__init__()
        self._products = set(products)

    async def add(self, product: models.Product) -> None:
        self._products.add(product)

    async def get(self, sku: str) -> models.Product:
        return next((p for p in self._products if p.sku == sku), None)

    async def get_by_batch_id(self, batch_id: UUID) -> models.Product:
        return next((p for p in self._products for b in p.batches if b.id == batch_id), None)


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork[repository.AbstractProductRepository]):
    def __init__(self) -> None:
        self._repo = FakeRepository([])
        self.committed = False

    async def __aexit__(self, *args: Any) -> None:
        await self.rollback()

    @property
    def repo(self) -> repository.AbstractProductRepository:
        return self._repo

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


class TestAddBatch:
    async def test_for_new_product(self) -> None:
        uow = FakeUnitOfWork()
        await messagebus.handle(commands.CreateBatch(uuid4(), "CRUNCHY-ARMCHAIR", 100), uow)
        assert await uow.repo.get("CRUNCHY-ARMCHAIR") is not None
        assert uow.committed

    async def test_for_existing_product(self) -> None:
        uow = FakeUnitOfWork()
        await messagebus.handle(
            commands.CreateBatch(UUID("5103f447-4568-4615-bc28-70447d1a7436"), "GARISH-RUG", 100),
            uow,
        )
        await messagebus.handle(
            commands.CreateBatch(UUID("6c381ae2-c9fc-4b52-aacb-3e496f0aacef"), "GARISH-RUG", 99),
            uow,
        )
        assert UUID("5103f447-4568-4615-bc28-70447d1a7436") in [
            b.id for b in (await uow.repo.get("GARISH-RUG")).batches
        ]
        assert UUID("6c381ae2-c9fc-4b52-aacb-3e496f0aacef") in [
            b.id for b in (await uow.repo.get("GARISH-RUG")).batches
        ]


class TestAllocate:
    async def test_returns_allocation(self) -> None:
        uow = FakeUnitOfWork()
        await messagebus.handle(
            commands.CreateBatch(
                UUID("b4cf5213-6e1f-46cc-8302-aac1f12ac617"), "COMPLICATED-LAMP", 100
            ),
            uow,
        )
        results = await messagebus.handle(commands.Allocate("COMPLICATED-LAMP", 10), uow)
        assert results.pop(0) == UUID("b4cf5213-6e1f-46cc-8302-aac1f12ac617")

    async def test_errors_for_invalid_sku(self) -> None:
        uow = FakeUnitOfWork()
        with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            await messagebus.handle(commands.Allocate("NONEXISTENTSKU", 10), uow)

    async def test_commits(self) -> None:
        uow = FakeUnitOfWork()
        await messagebus.handle(commands.CreateBatch(uuid4(), "OMINOUS-MIRROR", 100, None), uow)
        await messagebus.handle(commands.Allocate("OMINOUS-MIRROR", 10), uow)
        assert uow.committed

    async def test_sends_email_on_out_of_stock_error(self) -> None:
        uow = FakeUnitOfWork()
        await messagebus.handle(commands.CreateBatch(uuid4(), "POPULAR-CURTAINS", 9, None), uow)
        with mock.patch("app.allocation.adapters.email.send") as mock_send_mail:
            await messagebus.handle(commands.Allocate("POPULAR-CURTAINS", 10), uow)
            assert mock_send_mail.call_args == mock.call(
                "stock@made.com", "Out of stock for POPULAR-CURTAINS"
            )


class TestChangeBatchQuantity:
    async def test_changes_available_quantity(self) -> None:
        uow = FakeUnitOfWork()
        await messagebus.handle(
            commands.CreateBatch(
                UUID("05e2c957-154b-4dcf-9d24-d172f26e4b12"), "ADORABLE-SETTEE", 100, None
            ),
            uow,
        )
        [batch] = (await uow.repo.get(sku="ADORABLE-SETTEE")).batches
        assert batch.available_quantity == 100

        await messagebus.handle(
            commands.ChangeBatchQuantity(UUID("05e2c957-154b-4dcf-9d24-d172f26e4b12"), 50), uow
        )

        assert batch.available_quantity == 50

    async def test_reallocates_if_necessary(self) -> None:
        uow = FakeUnitOfWork()
        event_history = [
            commands.CreateBatch(
                UUID("874c6d0d-84e6-4307-b9d5-e23ec78bb727"), "INDIFFERENT-TABLE", 50, None
            ),
            commands.CreateBatch(uuid4(), "INDIFFERENT-TABLE", 50, date.today()),
            commands.Allocate("INDIFFERENT-TABLE", 20),
            commands.Allocate("INDIFFERENT-TABLE", 20),
        ]
        for e in event_history:
            await messagebus.handle(e, uow)
        [batch1, batch2] = (await uow.repo.get(sku="INDIFFERENT-TABLE")).batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        await messagebus.handle(
            commands.ChangeBatchQuantity(UUID("874c6d0d-84e6-4307-b9d5-e23ec78bb727"), 25), uow
        )

        # order1 or order2 will be deallocated, so we'll have 25 - 20
        assert batch1.available_quantity == 5
        # and 20 will be reallocated to the next batch
        assert batch2.available_quantity == 30
