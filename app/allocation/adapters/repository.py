import abc
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, subqueryload

from app.allocation.domain import models


class AbstractProductRepository(abc.ABC):
    def __init__(self) -> None:
        self._seen: set[models.Product] = set()

    @property
    def seen(self) -> set[models.Product]:
        return self._seen

    async def add(self, product: models.Product) -> None:
        await self._add(product)
        self._seen.add(product)

    async def get(self, sku: str) -> models.Product:
        product = await self._get(sku)
        if product:
            self._seen.add(product)
        return product

    async def get_by_batch_id(self, batch_id: UUID) -> models.Product:
        product = await self._get_by_batch_id(batch_id)
        if product:
            self._seen.add(product)
        return product

    @abc.abstractmethod
    async def _add(self, product: models.Product) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def _get(self, sku: str) -> models.Product:
        raise NotImplementedError

    @abc.abstractmethod
    async def _get_by_batch_id(self, batch_id: UUID) -> models.Product:
        raise NotImplementedError


class PGProductRepository(AbstractProductRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self._session = session

    async def _add(self, product: models.Product) -> None:
        self._session.add(product)
        await self._session.flush()

    async def _get(self, sku: str) -> models.Product:
        # async sqlalchemy doesn't support relationship
        # It raise 'greenlet_spawn has not been called; can't call await_() here. Was IO attempted in an unexpected place?' # noqa E501
        result = await self._session.execute(
            sa.select(models.Product)
            .where(models.Product.sku == sku)
            .options(
                selectinload(models.Product.batches).options(selectinload(models.Batch.allocations))
            )
        )
        return result.scalar_one_or_none()

    async def _get_by_batch_id(self, batch_id: UUID) -> models.Product:
        result = await self._session.execute(
            sa.select(models.Product)
            .where(models.Product.batches.any(models.Batch.id == batch_id))  # type: ignore
            .options(
                subqueryload(models.Product.batches).options(subqueryload(models.Batch.allocations))
            )
        )
        return result.scalar_one_or_none()
