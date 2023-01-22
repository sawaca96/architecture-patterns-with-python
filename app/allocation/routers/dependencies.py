import functools
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.allocation.adapters.db import DB
from app.allocation.adapters.repository import BatchAbstractRepository, PGBatchRepository
from app.config import get_config

config = get_config()


@functools.lru_cache
def db() -> DB:
    return DB(config.PG_DSN)


async def session(db: DB = Depends(db)) -> AsyncGenerator[AsyncSession, None]:
    async with db.session() as session:
        yield session


def repository(
    session: AsyncSession = Depends(session),
) -> BatchAbstractRepository:
    return PGBatchRepository(session)
