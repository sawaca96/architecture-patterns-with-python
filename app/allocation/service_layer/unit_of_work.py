from __future__ import annotations

import abc
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.allocation.adapters.db import SESSION_FACTORY, async_scoped_session
from app.allocation.adapters.repository import AbstractProductRepository, PGProductRepository


class AbstractUnitOfWork(abc.ABC):
    async def __aenter__(self) -> AbstractUnitOfWork:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.rollback()

    @abc.abstractproperty
    def products(self) -> AbstractProductRepository:
        raise NotImplementedError

    @abc.abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError


class PGUnitOfWork(AbstractUnitOfWork):
    def __init__(self) -> None:
        self._session_factory: async_scoped_session = None
        self._session: AsyncSession = None
        self._products: PGProductRepository = None

    @property
    def products(self) -> AbstractProductRepository:
        return self._products

    async def __aenter__(self) -> AbstractUnitOfWork:
        # put below code to __init__, and then run test it will raise error "no event loop"
        # because async client do not create event loop at depends level
        self._session_factory = SESSION_FACTORY
        self._session = self._session_factory()
        self._products = PGProductRepository(self._session)
        return await super().__aenter__()

    async def __aexit__(self, *args: Any) -> None:
        await super().__aexit__(*args)
        await self._session_factory.remove()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
