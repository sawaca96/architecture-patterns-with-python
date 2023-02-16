from asyncio import current_task
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import config

ENGINE = create_async_engine(config.PG_DSN, echo=False)
SESSION_FACTORY = async_scoped_session(
    sessionmaker(autocommit=False, class_=AsyncSession, bind=ENGINE), scopefunc=current_task
)


class DB:
    def __init__(self, url: str) -> None:
        self._engine = create_async_engine(url, echo=False)
        self._session_factory = async_scoped_session(
            sessionmaker(
                autocommit=False,
                class_=AsyncSession,
                bind=self._engine,
            ),
            scopefunc=current_task,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        session: AsyncSession = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await self._session_factory.remove()
