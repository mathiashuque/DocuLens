"""Durable anonymous usage buckets; raw session identifiers are never stored."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AnonymousUsageBucket(Base):
    __tablename__ = "anonymous_usage_buckets"
    __table_args__ = (
        UniqueConstraint(
            "session_digest",
            "category",
            "scope_id",
            "window_start",
            name="uq_anonymous_usage_logical_bucket",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "category IN ('analysis', 'index', 'question')",
            name="ck_anonymous_usage_category_valid",
        ),
        CheckConstraint(
            "consumed >= 0", name="ck_anonymous_usage_consumed_nonnegative"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    session_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
