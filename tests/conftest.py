from typing import Any, AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import clear_mappers, sessionmaker

from app.orm import metadata, start_mappers


@pytest.fixture
async def in_memory_db() -> AsyncEngine:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    return engine


@pytest.fixture
async def session(in_memory_db: AsyncEngine) -> AsyncGenerator[AsyncSession, Any]:
    start_mappers()
    session = sessionmaker(bind=in_memory_db, expire_on_commit=False, class_=AsyncSession)()
    yield session
    await session.close()
    clear_mappers()
