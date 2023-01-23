import abc
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, subqueryload

from app.allocation.domain import models


class AbstractBatchRepository(abc.ABC):
    @abc.abstractmethod
    async def add(self, batch: models.Batch) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, id: UUID) -> models.Batch:
        raise NotImplementedError

    @abc.abstractmethod
    async def list(self) -> list[models.Batch]:
        raise NotImplementedError


class PGBatchRepository(AbstractBatchRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, batch: models.Batch) -> None:
        self._session.add(batch)
        await self._session.flush()

    async def get(self, id: UUID) -> models.Batch:
        # async sqlalchemy doesn't support relationship
        # It raise 'greenlet_spawn has not been called; can't call await_() here. Was IO attempted in an unexpected place?' # noqa E501
        result = await self._session.execute(
            sa.select(models.Batch)
            .where(models.Batch.id == id)
            .options(selectinload(models.Batch.allocations))
        )
        return result.scalar_one()

    async def list(self) -> list[models.Batch]:
        result = await self._session.execute(
            sa.select(models.Batch).options(subqueryload(models.Batch.allocations))
        )
        return [r[0] for r in result.fetchall()]
