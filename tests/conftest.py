import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import clear_mappers

from app.config import get_config
from app.db import DB
from app.orm import metadata, start_mappers

config = get_config()
db = DB(config.PG_DSN)


@pytest.fixture(scope="session")
def event_loop() -> Generator[Any, Any, Any]:
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(config.PG_DSN)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    start_mappers()
    yield engine
    clear_mappers()
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, Any]:
    trans = await engine.begin()
    session = AsyncSession(bind=engine)
    yield session
    await session.close()
    await trans.rollback()
