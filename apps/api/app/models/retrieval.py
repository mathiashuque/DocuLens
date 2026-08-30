"""Persistence models for structure-aware retrieval: one completed index
record per document plus its durable chunks and embeddings.

Only a `completed` index, with every chunk row present, is ever visible;
the indexing service inserts the index row and all chunk rows in one
transaction and never marks an index complete with missing chunks.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.document import Document

# Fixed at the configured embedding provider's output dimension. Changing
# this requires an explicit migration/reindex decision, not a silent
# runtime change; see `app/core/config.py::EmbeddingSettings`.
EMBEDDING_DIMENSION = 1536


class DocumentIndex(Base):
    """The single persisted completed index for a document.

    The unique `document_id` constraint is what makes POST idempotent and
    lets search resolve "the" index for a document with a direct lookup,
    mirroring `DocumentClassification`/`DocumentAnalysis`.
    """

    __tablename__ = "document_indexes"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_document_indexes_document_id"),
        CheckConstraint(
            "status = 'completed'", name="ck_document_indexes_status_valid"
        ),
        CheckConstraint(
            "chunk_count > 0", name="ck_document_indexes_chunk_count_positive"
        ),
        CheckConstraint("dimension > 0", name="ck_document_indexes_dimension_positive"),
        CheckConstraint(
            "char_length(chunker_version) > 0",
            name="ck_document_indexes_chunker_version_nonempty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    chunker_version: Mapped[str] = mapped_column(String(20), nullable=False)
    chunking_config: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    document: Mapped["Document"] = relationship()
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="index",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "index_id", "chunk_index", name="uq_document_chunks_index_chunk_index"
        ),
        CheckConstraint(
            "chunk_index >= 0", name="ck_document_chunks_chunk_index_valid"
        ),
        CheckConstraint(
            "page_start > 0", name="ck_document_chunks_page_start_positive"
        ),
        CheckConstraint(
            "page_end >= page_start", name="ck_document_chunks_page_end_gte_start"
        ),
        CheckConstraint(
            "char_length(text) > 0", name="ck_document_chunks_text_nonempty"
        ),
        CheckConstraint(
            "token_estimate > 0", name="ck_document_chunks_token_estimate_positive"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    index_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_indexes.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_sections.id", ondelete="SET NULL"),
        nullable=True,
    )
    section_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_path: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSION), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    index: Mapped["DocumentIndex"] = relationship(back_populates="chunks")
