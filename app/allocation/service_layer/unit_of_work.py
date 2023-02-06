from __future__ import annotations

import abc
from typing import Any, Generic, TypeVar

from app.allocation.adapters.db import SESSION_FACTORY
from app.allocation.adapters.repository import (
    AbstractProductRepository,
    PGProductRepository,
)
from app.allocation.service_layer import messagebus
from app.config import get_config

config = get_config()

Repo = TypeVar("Repo", bound=AbstractProductRepository)


class AbstractUnitOfWork(abc.ABC, Generic[Repo]):
    async def __aenter__(self) -> AbstractUnitOfWork[Repo]:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.rollback()

    @abc.abstractproperty
    def repo(self) -> Repo:
        raise NotImplementedError

    async def commit(self) -> None:
        await self._commit()
        await self._publish_events()

    async def _publish_events(self) -> None:
        for product in self.repo._seen:
            while product.events:
                event = product.events.pop(0)
                await messagebus.handle(event)

    @abc.abstractmethod
    async def _commit(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError


class ProductUnitOfWork(AbstractUnitOfWork[AbstractProductRepository]):
    @property
    def repo(self) -> AbstractProductRepository:
        return self._repo

    async def __aenter__(self) -> AbstractUnitOfWork[AbstractProductRepository]:
        self._session = SESSION_FACTORY()
        self._repo = PGProductRepository(self._session)
        return await super().__aenter__()

    async def __aexit__(self, *args: Any) -> None:
        await super().__aexit__(*args)
        await SESSION_FACTORY.remove()

    async def _commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
