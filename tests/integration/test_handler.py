# pylint: disable=no-self-use
from datetime import date
from typing import Any
from collections.abc import AsyncGenerator
from unittest import mock
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncEngine

from app.allocation.adapters.orm import metadata
from app.allocation.domain import commands
from app.allocation.service_layer import handlers, unit_of_work


@pytest.fixture(autouse=True)
async def clear_db(engine: AsyncEngine) -> AsyncGenerator[AsyncEngine, Any]:
    # TODO: session and function tests pass, but module tests fail due to start_mappers issue.
    yield engine
    async with engine.begin() as conn:
        for table in reversed(metadata.sorted_tables):
            await conn.execute(table.delete())


class TestAddBatch:
    async def test_for_new_product(self) -> None:
        uow = unit_of_work.PGUnitOfWork()
        await handlers.CreateBatchCmdHandler(uow).handle(commands.CreateBatch(uuid4(), "CRUNCHY-ARMCHAIR", 100))
        async with uow:
            assert await uow.products.get("CRUNCHY-ARMCHAIR") is not None

    async def test_for_existing_product(self) -> None:
        uow = unit_of_work.PGUnitOfWork()

        await handlers.CreateBatchCmdHandler(uow).handle(
            commands.CreateBatch(UUID("5103f447-4568-4615-bc28-70447d1a7436"), "GARISH-RUG", 100)
        )
        await handlers.CreateBatchCmdHandler(uow).handle(
            commands.CreateBatch(UUID("6c381ae2-c9fc-4b52-aacb-3e496f0aacef"), "GARISH-RUG", 99)
        )

        async with uow:
            assert UUID("5103f447-4568-4615-bc28-70447d1a7436") in [
                b.id for b in (await uow.products.get("GARISH-RUG")).batches
            ]
            assert UUID("6c381ae2-c9fc-4b52-aacb-3e496f0aacef") in [
                b.id for b in (await uow.products.get("GARISH-RUG")).batches
            ]


class TestAllocate:
    async def test_returns_allocation(self, mocker: MockerFixture) -> None:
        uow = unit_of_work.PGUnitOfWork()
        mock_redis = mocker.patch("app.allocation.service_layer.handlers.redis", return_value=mock.AsyncMock)
        mock_redis.attach_mock(mock_redis, "publish")

        await handlers.CreateBatchCmdHandler(uow).handle(
            commands.CreateBatch(UUID("b4cf5213-6e1f-46cc-8302-aac1f12ac617"), "COMPLICATED-LAMP", 100)
        )
        batch_id = await handlers.AllocateCmdHandler(uow).handle(
            commands.Allocate(UUID("c3370153-5d1c-4059-9a2a-4a39267afc27"), "COMPLICATED-LAMP", 10)
        )

        async with uow:
            assert mock_redis.call_args == mock.call(
                "allocation:order_allocated:v1",
                b'{"order_id":"c3370153-5d1c-4059-9a2a-4a39267afc27","sku":"COMPLICATED-LAMP","qty":10,"batch_id":"b4cf5213-6e1f-46cc-8302-aac1f12ac617"}',
            )
            assert batch_id == UUID("b4cf5213-6e1f-46cc-8302-aac1f12ac617")

    async def test_errors_for_invalid_sku(self) -> None:
        uow = unit_of_work.PGUnitOfWork()
        with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            await handlers.AllocateCmdHandler(uow).handle(commands.Allocate(uuid4(), "NONEXISTENTSKU", 10))

    async def test_allocate_handler_commit(self, mocker: MockerFixture) -> None:
        uow = unit_of_work.PGUnitOfWork()
        mock_redis = mocker.patch("app.allocation.service_layer.handlers.redis", return_value=mock.AsyncMock)
        mock_redis.attach_mock(mock_redis, "publish")

        await handlers.CreateBatchCmdHandler(uow).handle(
            commands.CreateBatch(UUID("0cf8c64c-efd3-4b18-994b-9254ee7c3c93"), "OMINOUS-MIRROR", 100, None)
        )
        await handlers.AllocateCmdHandler(uow).handle(
            commands.Allocate(UUID("1156164c-1ed1-4726-b315-5db7ac65ebb5"), "OMINOUS-MIRROR", 10)
        )

        assert mock_redis.call_args == mock.call(
            "allocation:order_allocated:v1",
            b'{"order_id":"1156164c-1ed1-4726-b315-5db7ac65ebb5","sku":"OMINOUS-MIRROR","qty":10,"batch_id":"0cf8c64c-efd3-4b18-994b-9254ee7c3c93"}',
        )

    async def test_sends_email_on_out_of_stock_error(self, mocker: MockerFixture) -> None:
        uow = unit_of_work.PGUnitOfWork()
        mock_send_mail = mocker.patch("app.allocation.adapters.email.send")

        await handlers.CreateBatchCmdHandler(uow).handle(commands.CreateBatch(uuid4(), "POPULAR-CURTAINS", 9, None))
        await handlers.AllocateCmdHandler(uow).handle(commands.Allocate(uuid4(), "POPULAR-CURTAINS", 10))

        assert mock_send_mail.call_args == mock.call("stock@made.com", "Out of stock for POPULAR-CURTAINS")


class TestChangeBatchQuantity:
    async def test_changes_available_quantity(self) -> None:
        uow = unit_of_work.PGUnitOfWork()
        await handlers.CreateBatchCmdHandler(uow).handle(
            commands.CreateBatch(UUID("05e2c957-154b-4dcf-9d24-d172f26e4b12"), "ADORABLE-SETTEE", 100, None)
        )

        await handlers.ChangeBatchQuantityCmdHandler(uow).handle(
            commands.ChangeBatchQuantity(UUID("05e2c957-154b-4dcf-9d24-d172f26e4b12"), 50)
        )
        async with uow:
            [batch] = (await uow.products.get(sku="ADORABLE-SETTEE")).batches
            assert batch.available_quantity == 50

    async def test_reallocates_if_necessary(self, mocker: MockerFixture) -> None:
        # Given
        uow = unit_of_work.PGUnitOfWork()

        await handlers.CreateBatchCmdHandler(uow).handle(
            commands.CreateBatch(UUID("874c6d0d-84e6-4307-b9d5-e23ec78bb727"), "INDIFFERENT-TABLE", 50, None)
        )
        await handlers.CreateBatchCmdHandler(uow).handle(
            commands.CreateBatch(UUID("e9c6851c-e74a-40ac-8e86-3956f4762853"), "INDIFFERENT-TABLE", 50, date.today())
        )
        with mock.patch("app.allocation.service_layer.handlers.redis", return_value=mock.AsyncMock) as mock_redis:
            mock_redis.attach_mock(mock_redis, "publish")
            await handlers.AllocateCmdHandler(uow).handle(
                commands.Allocate(UUID("57e0e250-93f2-4378-b44e-307838b4c367"), "INDIFFERENT-TABLE", 40)
            )
            await handlers.AllocateCmdHandler(uow).handle(
                commands.Allocate(UUID("1406c359-13b6-422d-8507-b24a0c763abd"), "INDIFFERENT-TABLE", 20)
            )

        async with uow:
            [batch1, batch2] = (await uow.products.get(sku="INDIFFERENT-TABLE")).batches
            assert batch1.available_quantity == 10
            assert batch2.available_quantity == 30

        # When
        def mock_publish(channel: str, message: bytes) -> None:
            assert channel == "allocation:order_deallocated:v1"
            assert message == b'{"order_id":"57e0e250-93f2-4378-b44e-307838b4c367","sku":"INDIFFERENT-TABLE","qty":40}'

        mock_pipeline = mock.AsyncMock()
        mock_pipeline.publish = mock_publish
        mocker.patch(
            "app.allocation.service_layer.handlers.redis.pipeline",
            return_value=mock_pipeline,
        )
        await handlers.ChangeBatchQuantityCmdHandler(uow).handle(
            commands.ChangeBatchQuantity(UUID("874c6d0d-84e6-4307-b9d5-e23ec78bb727"), 25)
        )

        # Then
        async with uow:
            [batch1, batch2] = (await uow.products.get(sku="INDIFFERENT-TABLE")).batches
            assert batch2.available_quantity == 25
