import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db.session import dispose_engine
from app.demo.seed import DemoSeedError, seed_demos
from app.models.document import Document, DocumentAnalysis
from app.models.quota import AnonymousUsageBucket
from app.services.quota import QuotaExceededError, reserve_quota
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_demo_seed_creates_exactly_three_then_is_a_noop(
    postgres_url: str, clean_tables: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    await dispose_engine()
    try:
        assert await seed_demos() == (3, 0)
        assert await seed_demos() == (0, 3)
        engine = create_async_engine(postgres_url)
        async with async_sessionmaker(engine)() as session:
            rows = list(
                (
                    await session.execute(
                        select(Document).where(Document.demo_slug.is_not(None))
                    )
                ).scalars()
            )
            assert {row.demo_slug for row in rows} == {
                "sample-contract",
                "sample-technical-specification",
                "sample-generic-report",
            }
            analysis_count = (
                await session.execute(select(func.count(DocumentAnalysis.id)))
            ).scalar_one()
            assert analysis_count == 3
            await session.execute(
                delete(DocumentAnalysis).where(
                    DocumentAnalysis.document_id == rows[0].id
                )
            )
            await session.commit()
        await engine.dispose()
        with pytest.raises(DemoSeedError, match="mismatch"):
            await seed_demos()
    finally:
        await dispose_engine()


@pytest.mark.asyncio
async def test_atomic_daily_quota_admits_only_the_limit_under_concurrency(
    postgres_url: str, clean_tables: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv(
        "ANONYMOUS_SESSION_SECRET", "integration-test-secret-at-least-thirty-two-bytes"
    )
    monkeypatch.setenv("MAX_ANALYSES_PER_DAY", "3")
    engine = create_async_engine(postgres_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 8, 29, 12, tzinfo=UTC)

    async def attempt() -> bool:
        async with sessions() as session:
            try:
                await reserve_quota(session, "d" * 64, "analysis", now=now)
                await session.commit()
                return True
            except QuotaExceededError:
                await session.rollback()
                return False

    assert sum(await asyncio.gather(*(attempt() for _ in range(5)))) == 3
    async with sessions() as session:
        assert (
            await session.execute(select(func.max(AnonymousUsageBucket.consumed)))
        ).scalar_one() == 3
        assert (
            await reserve_quota(
                session, "d" * 64, "analysis", now=now + timedelta(days=1)
            )
            == 2
        )
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_question_quota_is_lifetime_per_document_with_no_fake_reset(
    postgres_url: str, clean_tables: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv(
        "ANONYMOUS_SESSION_SECRET", "integration-test-secret-at-least-thirty-two-bytes"
    )
    monkeypatch.setenv("MAX_QUESTIONS_PER_DOCUMENT", "1")
    engine = create_async_engine(postgres_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    first_document = uuid.uuid4()
    second_document = uuid.uuid4()
    now = datetime(2026, 8, 29, 23, 59, tzinfo=UTC)

    async with sessions() as session:
        assert (
            await reserve_quota(
                session,
                "q" * 64,
                "question",
                document_id=first_document,
                now=now,
            )
            == 0
        )
        with pytest.raises(QuotaExceededError) as exhausted:
            await reserve_quota(
                session,
                "q" * 64,
                "question",
                document_id=first_document,
                now=now + timedelta(days=30),
            )
        assert exhausted.value.retry_at is None
        assert (
            await reserve_quota(
                session,
                "q" * 64,
                "question",
                document_id=second_document,
                now=now + timedelta(days=30),
            )
            == 0
        )
    await engine.dispose()
