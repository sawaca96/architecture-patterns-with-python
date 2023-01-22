import functools
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_config
from app.db import DB
from app.repository import BatchAbstractRepository, PGBatchRepository

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
