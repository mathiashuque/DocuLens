"""add precomputed demo metadata and anonymous usage buckets

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("demo_slug", sa.String(80), nullable=True))
    op.add_column("documents", sa.Column("demo_version", sa.String(40), nullable=True))
    op.add_column("documents", sa.Column("demo_title", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("demo_description", sa.Text(), nullable=True))
    op.add_column(
        "documents", sa.Column("demo_document_type", sa.String(30), nullable=True)
    )
    op.add_column(
        "documents",
        sa.Column("demo_questions", postgresql.JSONB(), nullable=True),
    )
    op.create_index("uq_documents_demo_slug", "documents", ["demo_slug"], unique=True)
    op.create_check_constraint(
        "ck_documents_demo_metadata_complete",
        "documents",
        "(demo_slug IS NULL AND demo_version IS NULL AND demo_title IS NULL "
        "AND demo_description IS NULL AND demo_document_type IS NULL "
        "AND demo_questions IS NULL) OR "
        "(demo_slug IS NOT NULL AND demo_version IS NOT NULL AND demo_title IS NOT NULL "
        "AND demo_description IS NOT NULL AND demo_document_type IS NOT NULL "
        "AND demo_questions IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_documents_demo_type_valid",
        "documents",
        "demo_document_type IS NULL OR demo_document_type IN "
        "('contract', 'technical_specification', 'generic')",
    )

    # The existing technical extractor identifier is longer than VARCHAR(30).
    op.alter_column(
        "document_analyses",
        "extractor",
        existing_type=sa.String(30),
        type_=sa.String(50),
        existing_nullable=False,
    )

    op.create_table(
        "anonymous_usage_buckets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_digest", sa.String(64), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "session_digest",
            "category",
            "scope_id",
            "window_start",
            name="uq_anonymous_usage_logical_bucket",
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint(
            "category IN ('analysis', 'index', 'question')",
            name="ck_anonymous_usage_category_valid",
        ),
        sa.CheckConstraint(
            "consumed >= 0", name="ck_anonymous_usage_consumed_nonnegative"
        ),
        sa.CheckConstraint(
            "(category = 'question' AND scope_id IS NOT NULL AND window_end IS NULL) OR "
            "(category IN ('analysis', 'index') AND scope_id IS NULL AND window_end IS NOT NULL)",
            name="ck_anonymous_usage_scope_window",
        ),
    )
    op.create_index(
        "ix_anonymous_usage_session_category",
        "anonymous_usage_buckets",
        ["session_digest", "category"],
    )


def downgrade() -> None:
    op.drop_table("anonymous_usage_buckets")
    # Intentionally retain VARCHAR(50): the production technical extractor
    # identifier does not fit VARCHAR(30), so narrowing could destroy or reject
    # already-valid analyses. This compatibility fix is roll-forward only.
    op.drop_constraint("ck_documents_demo_type_valid", "documents", type_="check")
    op.drop_constraint(
        "ck_documents_demo_metadata_complete", "documents", type_="check"
    )
    op.drop_index("uq_documents_demo_slug", table_name="documents")
    for column in (
        "demo_questions",
        "demo_document_type",
        "demo_description",
        "demo_title",
        "demo_version",
        "demo_slug",
    ):
        op.drop_column("documents", column)
