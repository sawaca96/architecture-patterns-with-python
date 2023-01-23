from __future__ import annotations

import abc
from asyncio import current_task
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.allocation.adapters.repository import AbstractBatchRepository, PGBatchRepository
from app.config import get_config

config = get_config()

Repo = TypeVar("Repo")


class AbstractUnitOfWork(abc.ABC, Generic[Repo]):
    async def __aenter__(self) -> AbstractUnitOfWork[Repo]:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.rollback()

    @abc.abstractproperty
    def repo(self) -> Repo:
        raise NotImplementedError

    @abc.abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError


class BatchUnitOfWork(AbstractUnitOfWork[AbstractBatchRepository]):
    def __init__(self) -> None:
        self._engine = create_async_engine(config.PG_DSN, echo=False)
        self._session_factory = async_scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                class_=AsyncSession,
                bind=self._engine,
            ),
            scopefunc=current_task,
        )

    @property
    def repo(self) -> AbstractBatchRepository:
        return self._batches

    async def __aenter__(self) -> AbstractUnitOfWork[AbstractBatchRepository]:
        self._session: AsyncSession = self._session_factory()
        self._batches = PGBatchRepository(self._session)
        return await super().__aenter__()

    async def __aexit__(self, *args: Any) -> None:
        await super().__aexit__(*args)
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
