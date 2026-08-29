"""Disposable PostgreSQL fixture for persistence integration tests.

Prefers an already-running service (`TEST_DATABASE_URL`, e.g. a CI service
container). Otherwise starts and tears down a uniquely named, unpublished-by-
default local container for the test session only — never the developer's
own Compose project or volume.
"""

import asyncio
import os
import shutil
import socket
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = REPO_ROOT / "apps" / "api" / "alembic.ini"
IMAGE = "pgvector/pgvector:pg16"
TEST_DB = "doculens_test"
TEST_USER = "doculens_test"
TEST_PASSWORD = "test_only_password"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def _wait_ready(url: str, attempts: int = 60) -> None:
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url)
    try:
        for _ in range(attempts):
            try:
                async with engine.connect():
                    return
            except (OSError, DBAPIError):
                await asyncio.sleep(0.5)
        raise RuntimeError("PostgreSQL did not become ready in time.")
    finally:
        await engine.dispose()


def _run_migrations(url: str) -> None:
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        command.upgrade(Config(str(ALEMBIC_INI)), "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    external_url = os.environ.get("TEST_DATABASE_URL")
    if external_url:
        _run_migrations(external_url)
        yield external_url
        return

    if shutil.which("docker") is None:
        pytest.skip("Docker is unavailable; no PostgreSQL for integration tests.")

    container_name = f"doculens-test-db-{uuid.uuid4().hex[:8]}"
    port = _free_port()
    run = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-e",
            f"POSTGRES_DB={TEST_DB}",
            "-e",
            f"POSTGRES_USER={TEST_USER}",
            "-e",
            f"POSTGRES_PASSWORD={TEST_PASSWORD}",
            "-p",
            f"127.0.0.1:{port}:5432",
            IMAGE,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode != 0:
        pytest.skip(
            f"Could not start a disposable PostgreSQL container: {run.stderr.strip()}"
        )

    url = f"postgresql+asyncpg://{TEST_USER}:{TEST_PASSWORD}@127.0.0.1:{port}/{TEST_DB}"
    try:
        asyncio.run(_wait_ready(url))
        _run_migrations(url)
        yield url
    finally:
        subprocess.run(
            ["docker", "rm", "-f", container_name], capture_output=True, check=False
        )


@pytest_asyncio.fixture
async def clean_tables(postgres_url: str) -> None:
    """Truncate this slice's own tables before each test for isolation."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(postgres_url)
    async with engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE TABLE document_pages, documents CASCADE")
        )
    await engine.dispose()
