import abc
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import subqueryload

from app.allocation.domain import models


class BatchAbstractRepository(abc.ABC):
    @abc.abstractmethod
    async def add(self, batch: models.Batch) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, id: UUID) -> models.Batch:
        raise NotImplementedError

    @abc.abstractmethod
    async def list(self) -> list[models.Batch]:
        raise NotImplementedError


class PGBatchRepository(BatchAbstractRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, batch: models.Batch) -> None:
        self._session.add(batch)
        await self._session.flush()

    async def get(self, id: UUID) -> models.Batch:
        return await self._session.get(models.Batch, id)

    async def list(self) -> list[models.Batch]:
        result = await self._session.execute(
            sa.select(models.Batch).options(subqueryload(models.Batch.allocations))
        )
        return [r[0] for r in result.fetchall()]
