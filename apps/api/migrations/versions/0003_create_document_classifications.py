"""create document_classifications table

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_classifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(length=30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="completed"
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "document_type IN ('contract', 'technical_specification', 'generic')",
            name="ck_document_classifications_document_type_valid",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_document_classifications_confidence_range",
        ),
        sa.CheckConstraint(
            "status = 'completed'", name="ck_document_classifications_status_valid"
        ),
        sa.CheckConstraint(
            "char_length(reason) > 0", name="ck_document_classifications_reason_nonempty"
        ),
        sa.UniqueConstraint(
            "document_id", name="uq_document_classifications_document_id"
        ),
    )


def downgrade() -> None:
    op.drop_table("document_classifications")
