"""Alembic migration coverage against a real, disposable PostgreSQL database."""

import asyncio
import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
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
    assert "document_sections" in table_names
    assert "document_classifications" in table_names
    assert "document_analyses" in table_names
    assert "analysis_findings" in table_names
    assert "analysis_important_dates" in table_names
    assert "analysis_risks" in table_names
    assert "analysis_risk_evidence" in table_names
    assert "document_indexes" in table_names
    assert "document_chunks" in table_names


@pytest.mark.asyncio
async def test_upgrade_head_enables_vector_extension(postgres_url: str) -> None:
    engine = create_async_engine(postgres_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            )
            assert result.scalar_one_or_none() == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_document_chunks_embedding_column_has_configured_dimension(
    postgres_url: str,
) -> None:
    engine = create_async_engine(postgres_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT atttypmod FROM pg_attribute "
                    "WHERE attrelid = 'document_chunks'::regclass "
                    "AND attname = 'embedding'"
                )
            )
            # pgvector stores the configured dimension directly as the
            # column's type modifier.
            assert result.scalar_one() == 1536
    finally:
        await engine.dispose()


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


async def _insert_document_and_page_async(
    postgres_url: str, document_id: uuid.UUID
) -> None:
    engine = create_async_engine(postgres_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO documents "
                    "(id, filename, content_hash, page_count, status) "
                    "VALUES (:id, 'a.pdf', :hash, 1, 'parsed')"
                ),
                {"id": document_id, "hash": "a" * 64},
            )
            await connection.execute(
                text(
                    "INSERT INTO document_pages (document_id, page_number, text) "
                    "VALUES (:id, 1, 'hello')"
                ),
                {"id": document_id},
            )
    finally:
        await engine.dispose()


def _insert_document_and_page(postgres_url: str, document_id: uuid.UUID) -> None:
    asyncio.run(_insert_document_and_page_async(postgres_url, document_id))


async def _row_counts_async(
    postgres_url: str, document_id: uuid.UUID
) -> tuple[int, int, int]:
    engine = create_async_engine(postgres_url)
    try:
        async with engine.connect() as connection:
            document_count = (
                await connection.execute(
                    text("SELECT count(*) FROM documents WHERE id = :id"),
                    {"id": document_id},
                )
            ).scalar_one()
            page_count = (
                await connection.execute(
                    text("SELECT count(*) FROM document_pages WHERE document_id = :id"),
                    {"id": document_id},
                )
            ).scalar_one()
            section_count = (
                await connection.execute(
                    text(
                        "SELECT count(*) FROM document_sections WHERE document_id = :id"
                    ),
                    {"id": document_id},
                )
            ).scalar_one()
            return document_count, page_count, section_count
    finally:
        await engine.dispose()


def _row_counts(postgres_url: str, document_id: uuid.UUID) -> tuple[int, int, int]:
    return asyncio.run(_row_counts_async(postgres_url, document_id))


def test_document_section_migration_preserves_existing_document_rows(
    postgres_url: str,
) -> None:
    """Downgrading only the section table's own revision must not touch
    existing document/page rows, and re-upgrading fabricates no sections."""
    document_id = uuid.uuid4()
    _insert_document_and_page(postgres_url, document_id)

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = postgres_url
    try:
        config = Config(str(ALEMBIC_INI))
        command.downgrade(config, "0001")
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous

    document_count, page_count, section_count = _row_counts(postgres_url, document_id)
    assert document_count == 1
    assert page_count == 1
    assert section_count == 0


def test_document_analysis_migration_preserves_existing_document_rows(
    postgres_url: str,
) -> None:
    """Downgrading only the analysis table's own revision must not touch
    existing document/page rows, and re-upgrading fabricates nothing."""
    document_id = uuid.uuid4()
    _insert_document_and_page(postgres_url, document_id)

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = postgres_url
    try:
        config = Config(str(ALEMBIC_INI))
        command.downgrade(config, "0003")
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous

    document_count, page_count, section_count = _row_counts(postgres_url, document_id)
    assert document_count == 1
    assert page_count == 1
    assert section_count == 0


def test_retrieval_migration_preserves_existing_document_rows(
    postgres_url: str,
) -> None:
    """Downgrading only the retrieval revision (0007) must not touch
    existing document/page rows, and re-upgrading fabricates no index or
    chunk rows; the `vector` extension is intentionally left enabled."""
    document_id = uuid.uuid4()
    _insert_document_and_page(postgres_url, document_id)

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = postgres_url
    try:
        config = Config(str(ALEMBIC_INI))
        command.downgrade(config, "0006")
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous

    document_count, page_count, section_count = _row_counts(postgres_url, document_id)
    assert document_count == 1
    assert page_count == 1
    assert section_count == 0


def test_document_classification_migration_preserves_existing_document_rows(
    postgres_url: str,
) -> None:
    """Downgrading only the classification table's own revision must not
    touch existing document/page rows, and re-upgrading fabricates nothing."""
    document_id = uuid.uuid4()
    _insert_document_and_page(postgres_url, document_id)

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = postgres_url
    try:
        config = Config(str(ALEMBIC_INI))
        command.downgrade(config, "0002")
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous

    document_count, page_count, section_count = _row_counts(postgres_url, document_id)
    assert document_count == 1
    assert page_count == 1
    assert section_count == 0
