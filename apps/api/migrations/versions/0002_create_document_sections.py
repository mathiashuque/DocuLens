"""create document_sections table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_section_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_sections.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("section_path", postgresql.JSONB(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.CheckConstraint("ordinal > 0", name="ck_document_sections_ordinal_positive"),
        sa.CheckConstraint("level > 0", name="ck_document_sections_level_positive"),
        sa.CheckConstraint(
            "page_start > 0", name="ck_document_sections_page_start_positive"
        ),
        sa.CheckConstraint(
            "page_end >= page_start", name="ck_document_sections_page_end_gte_start"
        ),
        sa.CheckConstraint(
            "parent_section_id IS NULL OR parent_section_id != id",
            name="ck_document_sections_not_self_parent",
        ),
        sa.UniqueConstraint(
            "document_id", "ordinal", name="uq_document_sections_document_ordinal"
        ),
    )


def downgrade() -> None:
    op.drop_table("document_sections")
