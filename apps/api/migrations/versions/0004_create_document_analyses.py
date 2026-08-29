"""create document_analyses and child finding/date/risk tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(length=30), nullable=False),
        sa.Column("extractor", sa.String(length=30), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="completed"
        ),
        sa.Column("summary_title", sa.Text(), nullable=True),
        sa.Column("summary_purpose", sa.Text(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("summary_key_topics", postgresql.JSONB(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column(
            "retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")
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
            name="ck_document_analyses_document_type_valid",
        ),
        sa.CheckConstraint(
            "status = 'completed'", name="ck_document_analyses_status_valid"
        ),
        sa.CheckConstraint(
            "char_length(summary_purpose) > 0",
            name="ck_document_analyses_summary_purpose_nonempty",
        ),
        sa.CheckConstraint(
            "char_length(summary_text) > 0",
            name="ck_document_analyses_summary_text_nonempty",
        ),
        sa.UniqueConstraint("document_id", name="uq_document_analyses_document_id"),
    )

    op.create_table(
        "analysis_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("importance", sa.String(length=20), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint("ordinal > 0", name="ck_analysis_findings_ordinal_positive"),
        sa.CheckConstraint(
            "source_page > 0", name="ck_analysis_findings_source_page_positive"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_analysis_findings_confidence_range",
        ),
        sa.CheckConstraint(
            "importance IN ('low', 'medium', 'high', 'critical')",
            name="ck_analysis_findings_importance_valid",
        ),
        sa.CheckConstraint(
            "char_length(evidence) > 0", name="ck_analysis_findings_evidence_nonempty"
        ),
        sa.UniqueConstraint(
            "analysis_id", "ordinal", name="uq_analysis_findings_analysis_ordinal"
        ),
    )

    op.create_table(
        "analysis_important_dates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=False),
        sa.Column("normalized_date", sa.String(length=10), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint("ordinal > 0", name="ck_analysis_dates_ordinal_positive"),
        sa.CheckConstraint(
            "source_page > 0", name="ck_analysis_dates_source_page_positive"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_analysis_dates_confidence_range",
        ),
        sa.CheckConstraint(
            "char_length(evidence) > 0", name="ck_analysis_dates_evidence_nonempty"
        ),
        sa.UniqueConstraint(
            "analysis_id", "ordinal", name="uq_analysis_dates_analysis_ordinal"
        ),
    )

    op.create_table(
        "analysis_risks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint("ordinal > 0", name="ck_analysis_risks_ordinal_positive"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_analysis_risks_confidence_range",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_analysis_risks_severity_valid",
        ),
        sa.UniqueConstraint(
            "analysis_id", "ordinal", name="uq_analysis_risks_analysis_ordinal"
        ),
    )

    op.create_table(
        "analysis_risk_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "risk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_risks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "ordinal > 0", name="ck_analysis_risk_evidence_ordinal_positive"
        ),
        sa.CheckConstraint("page > 0", name="ck_analysis_risk_evidence_page_positive"),
        sa.CheckConstraint(
            "char_length(text) > 0", name="ck_analysis_risk_evidence_text_nonempty"
        ),
        sa.UniqueConstraint(
            "risk_id", "ordinal", name="uq_analysis_risk_evidence_risk_ordinal"
        ),
    )


def downgrade() -> None:
    op.drop_table("analysis_risk_evidence")
    op.drop_table("analysis_risks")
    op.drop_table("analysis_important_dates")
    op.drop_table("analysis_findings")
    op.drop_table("document_analyses")
