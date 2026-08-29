"""enable pgvector and create document_indexes/document_chunks tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Fixed at the configured embedding provider's output dimension
# (`text-embedding-3-small` default). Must stay consistent with
# `app.models.retrieval.EMBEDDING_DIMENSION` and
# `app.core.config.DEFAULT_EMBEDDING_DIMENSION`; changing it requires a new
# migration and an explicit reindex, never an in-place column edit.
EMBEDDING_DIMENSION = 1536


def upgrade() -> None:
    # Requires CREATEDB/superuser-equivalent privilege on first run in an
    # environment that has not already enabled this extension; the
    # `pgvector/pgvector` image ships the extension files so no OS-level
    # install step is needed. Safe to run repeatedly.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "document_indexes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
        sa.Column("chunker_version", sa.String(length=20), nullable=False),
        sa.Column("chunking_config", sa.String(length=100), nullable=False),
        sa.Column("embedding_provider", sa.String(length=50), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("document_id", name="uq_document_indexes_document_id"),
        sa.CheckConstraint(
            "status = 'completed'", name="ck_document_indexes_status_valid"
        ),
        sa.CheckConstraint(
            "chunk_count > 0", name="ck_document_indexes_chunk_count_positive"
        ),
        sa.CheckConstraint(
            "dimension > 0", name="ck_document_indexes_dimension_positive"
        ),
        sa.CheckConstraint(
            "char_length(chunker_version) > 0",
            name="ck_document_indexes_chunker_version_nonempty",
        ),
    )
    op.create_index(
        "ix_document_indexes_document_id", "document_indexes", ["document_id"]
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "index_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_indexes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column(
            "section_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_sections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("section_title", sa.Text(), nullable=True),
        sa.Column(
            "section_path",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "index_id", "chunk_index", name="uq_document_chunks_index_chunk_index"
        ),
        sa.CheckConstraint(
            "chunk_index >= 0", name="ck_document_chunks_chunk_index_valid"
        ),
        sa.CheckConstraint(
            "page_start > 0", name="ck_document_chunks_page_start_positive"
        ),
        sa.CheckConstraint(
            "page_end >= page_start", name="ck_document_chunks_page_end_gte_start"
        ),
        sa.CheckConstraint(
            "char_length(text) > 0", name="ck_document_chunks_text_nonempty"
        ),
        sa.CheckConstraint(
            "token_estimate > 0", name="ck_document_chunks_token_estimate_positive"
        ),
    )
    # Document-scoped lookups (index compatibility checks, search) always
    # filter by document_id first; a plain btree index is sufficient at this
    # single-document baseline's scale. An approximate ANN index (HNSW/
    # IVFFlat) is deferred until measured corpus size justifies its
    # recall/build-time tradeoff — exact cosine search is used instead.
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_table("document_indexes")
    # The `vector` extension is left in place on downgrade: dropping a
    # database-wide extension as part of a table rollback risks breaking
    # any other schema object that came to depend on it, and recreating it
    # is a cheap, idempotent no-op on the next upgrade. Extension lifecycle
    # is an explicit operational decision, not implied by this migration.
