"""Session fixture for repository-level PostgreSQL integration tests.

The engine is created per test function (not session-scoped) because
pytest-asyncio gives each async test its own event loop by default, and an
asyncpg connection pool is bound to the loop that created it.
"""

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session(postgres_url: str, clean_tables: None) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(postgres_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessionmaker() as db_session:
            yield db_session
    finally:
        await engine.dispose()
