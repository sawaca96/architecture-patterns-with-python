from __future__ import annotations

import abc
from asyncio import current_task
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.allocation.adapters.repository import AbstractProductRepository, PGProductRepository
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


class ProductUnitOfWork(AbstractUnitOfWork[AbstractProductRepository]):
    def __init__(self) -> None:
        engine = create_async_engine(
            config.PG_DSN,
            echo=False,
            isolation_level="SERIALIZABLE",
        )
        self._session_factory = async_scoped_session(
            sessionmaker(
                autocommit=False,
                expire_on_commit=False,
                class_=AsyncSession,
                bind=engine,
            ),
            scopefunc=current_task,
        )

    @property
    def repo(self) -> AbstractProductRepository:
        return self._repo

    async def __aenter__(self) -> AbstractUnitOfWork[AbstractProductRepository]:
        self._session: AsyncSession = self._session_factory()
        self._repo = PGProductRepository(self._session)
        return await super().__aenter__()

    async def __aexit__(self, *args: Any) -> None:
        await super().__aexit__(*args)
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
