import functools
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.allocation.adapters.db import DB
from app.allocation.adapters.repository import AbstractProductRepository, PGProductRepository
from app.allocation.service_layer.unit_of_work import AbstractUnitOfWork, ProductUnitOfWork
from app.config import config


@functools.lru_cache
def db() -> DB:
    return DB(config.PG_DSN)


async def session(db: DB = Depends(db)) -> AsyncGenerator[AsyncSession, None]:
    async with db.session() as session:
        yield session


def repository(
    session: AsyncSession = Depends(session),
) -> AbstractProductRepository:
    return PGProductRepository(session)


def batch_uow() -> AbstractUnitOfWork[AbstractProductRepository]:
    return ProductUnitOfWork()
