"""Anonymous-session validation and atomic PostgreSQL quota reservations."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Literal

from fastapi import Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.anonymous_session import InvalidAnonymousSessionError, verify_token
from app.core.config import (
    AnonymousQuotaSettings,
    InvalidConfigurationError,
    load_anonymous_quota_settings,
)
from app.models.quota import AnonymousUsageBucket

QuotaCategory = Literal["analysis", "index", "question"]


@dataclass
class QuotaExceededError(Exception):
    category: QuotaCategory
    limit: int
    retry_at: datetime | None


@dataclass(frozen=True)
class UsageAllowance:
    category: QuotaCategory
    limit: int
    remaining: int
    retry_at: datetime | None


def require_anonymous_identity(
    x_doculens_anonymous_session: str | None = Header(default=None),
) -> str | None:
    try:
        settings = load_anonymous_quota_settings()
    except InvalidConfigurationError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Usage protection is not configured."
        ) from exc
    if not settings.public_demo_mode:
        return None
    if not x_doculens_anonymous_session or settings.secret is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "A valid anonymous session is required."
        )
    try:
        return verify_token(
            x_doculens_anonymous_session,
            settings.secret,
            max_age_seconds=settings.session_max_age_seconds,
        ).session_digest
    except InvalidAnonymousSessionError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "A valid anonymous session is required."
        ) from exc


def _bucket(
    category: QuotaCategory,
    document_id: uuid.UUID | None,
    now: datetime,
    settings: AnonymousQuotaSettings,
) -> tuple[uuid.UUID | None, datetime, datetime | None, int]:
    if category == "question":
        assert document_id is not None
        return (
            document_id,
            datetime(1970, 1, 1, tzinfo=UTC),
            None,
            settings.max_questions_per_document,
        )
    start = datetime.combine(now.date(), time.min, tzinfo=UTC)
    limit = (
        settings.max_analyses_per_day
        if category == "analysis"
        else settings.max_indexes_per_day
    )
    return None, start, start + timedelta(days=1), limit


async def reserve_quota(
    session: AsyncSession,
    identity: str | None,
    category: QuotaCategory,
    *,
    document_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> int | None:
    settings = load_anonymous_quota_settings()
    if not settings.public_demo_mode:
        return None
    if identity is None:
        raise RuntimeError("public-mode quota reservation requires an identity")
    current = (now or datetime.now(UTC)).astimezone(UTC)
    scope_id, window_start, window_end, limit = _bucket(
        category, document_id, current, settings
    )
    insert_statement = insert(AnonymousUsageBucket).values(
        id=uuid.uuid4(),
        session_digest=identity,
        category=category,
        scope_id=scope_id,
        window_start=window_start,
        window_end=window_end,
        consumed=1,
    )
    statement = insert_statement.on_conflict_do_update(
        constraint="uq_anonymous_usage_logical_bucket",
        set_={"consumed": AnonymousUsageBucket.consumed + 1, "updated_at": current},
        where=AnonymousUsageBucket.consumed < limit,
    ).returning(AnonymousUsageBucket.consumed)
    consumed = (await session.execute(statement)).scalar_one_or_none()
    if consumed is None:
        raise QuotaExceededError(category, limit, window_end)
    # Reserve in its own transaction so later provider failures cannot refund
    # work that may already have incurred cost.
    await session.commit()
    return limit - consumed


async def get_usage_allowances(
    session: AsyncSession,
    identity: str | None,
    *,
    document_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> tuple[bool, list[UsageAllowance]]:
    """Return only the caller's aggregate allowance; never identity or bucket data."""
    settings = load_anonymous_quota_settings()
    if not settings.public_demo_mode:
        return False, []
    if identity is None:
        raise RuntimeError("public-mode usage lookup requires an identity")

    current = (now or datetime.now(UTC)).astimezone(UTC)
    categories: list[tuple[QuotaCategory, uuid.UUID | None]] = [
        ("analysis", None),
        ("index", None),
    ]
    if document_id is not None:
        categories.append(("question", document_id))

    allowances: list[UsageAllowance] = []
    for category, scope in categories:
        scope_id, window_start, window_end, limit = _bucket(
            category, scope, current, settings
        )
        statement = select(AnonymousUsageBucket.consumed).where(
            AnonymousUsageBucket.session_digest == identity,
            AnonymousUsageBucket.category == category,
            AnonymousUsageBucket.window_start == window_start,
        )
        if scope_id is None:
            statement = statement.where(AnonymousUsageBucket.scope_id.is_(None))
        else:
            statement = statement.where(AnonymousUsageBucket.scope_id == scope_id)
        consumed = (await session.execute(statement)).scalar_one_or_none() or 0
        allowances.append(
            UsageAllowance(category, limit, max(0, limit - consumed), window_end)
        )
    return True, allowances
