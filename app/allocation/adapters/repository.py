import abc

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.allocation.domain import models


class AbstractProductRepository(abc.ABC):
    @abc.abstractmethod
    async def add(self, product: models.Product) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, sku: str) -> models.Product:
        raise NotImplementedError


class PGProductRepository(AbstractProductRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, product: models.Product) -> None:
        self._session.add(product)
        await self._session.flush()

    async def get(self, sku: str) -> models.Product:
        # async sqlalchemy doesn't support relationship
        # It raise 'greenlet_spawn has not been called; can't call await_() here. Was IO attempted in an unexpected place?' # noqa E501
        result = await self._session.execute(
            sa.select(models.Product)
            .where(models.Product.sku == sku)
            .options(
                selectinload(models.Product.batches).options(selectinload(models.Batch.allocations))
            )
        )
        # TODO: joinedload?
        return result.scalar_one_or_none()
