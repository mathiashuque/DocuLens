"""Alembic migration coverage against a real, disposable PostgreSQL database."""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration.conftest import ALEMBIC_INI


@pytest.mark.asyncio
async def test_upgrade_head_creates_expected_tables(postgres_url: str) -> None:
    engine = create_async_engine(postgres_url)
    try:
        async with engine.connect() as connection:
            table_names = await connection.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
    finally:
        await engine.dispose()

    assert "documents" in table_names
    assert "document_pages" in table_names


def test_downgrade_then_upgrade_round_trip(postgres_url: str) -> None:
    """Leaves the database migrated to head for subsequent tests."""
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = postgres_url
    try:
        config = Config(str(ALEMBIC_INI))
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
