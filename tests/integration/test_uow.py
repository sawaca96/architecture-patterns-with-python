from typing import Any
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.allocation.adapters.orm import metadata
from app.allocation.domain import models
from app.allocation.service_layer.unit_of_work import BatchUnitOfWork


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, Any]:
    session = sessionmaker(bind=engine, class_=AsyncSession)()
    yield session
    await session.close()


@pytest.fixture(autouse=True)
async def clear_db(session: AsyncSession) -> AsyncGenerator[Any, Any]:
    yield session
    for table in reversed(metadata.sorted_tables):
        await session.execute(table.delete())


async def test_uow_can_retrieve_a_batch_and_allocate_line_to_batch(session: AsyncSession) -> None:
    # Given
    await session.execute(
        sa.text(
            "INSERT INTO batch (id, sku, qty, eta) VALUES "
            "('9c5d341f-4876-4a54-81f7-720a390884fb',  'RETRO-CLOCK', 100, null)"
        )
    )
    await session.commit()
    uow = BatchUnitOfWork()

    # When
    async with uow:
        batch = await uow.repo.get(UUID("9c5d341f-4876-4a54-81f7-720a390884fb"))
        line = models.OrderLine(
            id=UUID("cd7b01d0-00b5-4237-b1f6-ebb8c50dd7da"), sku="RETRO-CLOCK", qty=10
        )
        batch.allocate(line)
        await uow.commit()

    # Then
    [[batch_id]] = await session.execute(
        sa.text("SELECT batch_id FROM allocation"),
        dict(
            order_line_id=UUID("cd7b01d0-00b5-4237-b1f6-ebb8c50dd7da"),
            batch_id=UUID("9c5d341f-4876-4a54-81f7-720a390884fb"),
        ),
    )
    assert batch_id == UUID("9c5d341f-4876-4a54-81f7-720a390884fb")


async def test_rollback_uncommitted_work_by_default(session: AsyncSession) -> None:
    # Given
    uow = BatchUnitOfWork()

    # When
    async with uow:
        batch = models.Batch(id=uuid4(), sku="RETRO-CLOCK", qty=100, eta=None)
        await uow.repo.add(batch)

    # Then
    result = await session.execute(sa.text("SELECT * FROM batch"))
    assert list(result) == []


async def test_rollsback_on_error(session: AsyncSession) -> None:
    class MyException(Exception):
        pass

    uow = BatchUnitOfWork()
    with pytest.raises(MyException):
        async with uow:
            batch = models.Batch(id=uuid4(), sku="RETRO-CLOCK", qty=100, eta=None)
            await uow.repo.add(batch)
            raise MyException()

    result = await session.execute(sa.text("SELECT * FROM batch"))
    assert list(result) == []
