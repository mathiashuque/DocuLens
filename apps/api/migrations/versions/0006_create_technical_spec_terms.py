"""create technical_requirements/constraints/dependencies tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "technical_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("identifier", sa.String(length=50), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("actor", sa.Text(), nullable=True),
        sa.Column("measurable_criterion", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "ordinal > 0", name="ck_technical_requirements_ordinal_positive"
        ),
        sa.CheckConstraint(
            "source_page > 0", name="ck_technical_requirements_source_page_positive"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_technical_requirements_confidence_range",
        ),
        sa.CheckConstraint(
            "category IN ('functional', 'non_functional', 'security', 'integration')",
            name="ck_technical_requirements_category_valid",
        ),
        sa.CheckConstraint(
            "priority IN ('must', 'should', 'may', 'unspecified')",
            name="ck_technical_requirements_priority_valid",
        ),
        sa.CheckConstraint(
            "char_length(statement) > 0",
            name="ck_technical_requirements_statement_nonempty",
        ),
        sa.CheckConstraint(
            "char_length(evidence) > 0",
            name="ck_technical_requirements_evidence_nonempty",
        ),
        sa.UniqueConstraint(
            "analysis_id",
            "ordinal",
            name="uq_technical_requirements_analysis_ordinal",
        ),
    )

    op.create_table(
        "technical_constraints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "ordinal > 0", name="ck_technical_constraints_ordinal_positive"
        ),
        sa.CheckConstraint(
            "source_page > 0", name="ck_technical_constraints_source_page_positive"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_technical_constraints_confidence_range",
        ),
        sa.CheckConstraint(
            "category IN ('technology', 'performance', 'deployment', 'compatibility')",
            name="ck_technical_constraints_category_valid",
        ),
        sa.CheckConstraint(
            "char_length(statement) > 0",
            name="ck_technical_constraints_statement_nonempty",
        ),
        sa.CheckConstraint(
            "char_length(evidence) > 0",
            name="ck_technical_constraints_evidence_nonempty",
        ),
        sa.UniqueConstraint(
            "analysis_id",
            "ordinal",
            name="uq_technical_constraints_analysis_ordinal",
        ),
    )

    op.create_table(
        "technical_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("dependency_type", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "ordinal > 0", name="ck_technical_dependencies_ordinal_positive"
        ),
        sa.CheckConstraint(
            "source_page > 0", name="ck_technical_dependencies_source_page_positive"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_technical_dependencies_confidence_range",
        ),
        sa.CheckConstraint(
            "char_length(name) > 0", name="ck_technical_dependencies_name_nonempty"
        ),
        sa.CheckConstraint(
            "char_length(description) > 0",
            name="ck_technical_dependencies_description_nonempty",
        ),
        sa.CheckConstraint(
            "char_length(evidence) > 0",
            name="ck_technical_dependencies_evidence_nonempty",
        ),
        sa.UniqueConstraint(
            "analysis_id",
            "ordinal",
            name="uq_technical_dependencies_analysis_ordinal",
        ),
    )


def downgrade() -> None:
    op.drop_table("technical_dependencies")
    op.drop_table("technical_constraints")
    op.drop_table("technical_requirements")
