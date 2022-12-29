import abc

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app import models


class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, batch: models.Batch) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, reference: str) -> models.Batch:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, batch: models.Batch) -> None:
        self._session.add(batch)

    async def get(self, reference: str) -> models.Batch:
        batch = await self._session.get(models.Batch, reference)
        return batch

    async def list(self) -> list[models.Batch]:
        result = await self._session.execute(sa.select(models.Batch))
        return [models.Batch(**dict(r)) for r in result.fetchall()]
