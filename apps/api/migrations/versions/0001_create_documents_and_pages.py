"""create documents and document_pages tables

Revision ID: 0001
Revises:
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("page_count > 0", name="ck_documents_page_count_positive"),
        sa.CheckConstraint(
            "status IN ('parsed', 'ocr_required')", name="ck_documents_status_valid"
        ),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'", name="ck_documents_content_hash_format"
        ),
    )
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])

    op.create_table(
        "document_pages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "page_number > 0", name="ck_document_pages_page_number_positive"
        ),
        sa.UniqueConstraint(
            "document_id", "page_number", name="uq_document_pages_document_page_number"
        ),
    )


def downgrade() -> None:
    op.drop_table("document_pages")
    op.drop_table("documents")
