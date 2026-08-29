"""create contract_parties/obligations/payment_terms/clauses tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contract_parties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint("ordinal > 0", name="ck_contract_parties_ordinal_positive"),
        sa.CheckConstraint(
            "source_page > 0", name="ck_contract_parties_source_page_positive"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_contract_parties_confidence_range",
        ),
        sa.CheckConstraint(
            "char_length(name) > 0", name="ck_contract_parties_name_nonempty"
        ),
        sa.CheckConstraint(
            "char_length(evidence) > 0", name="ck_contract_parties_evidence_nonempty"
        ),
        sa.UniqueConstraint(
            "analysis_id", "ordinal", name="uq_contract_parties_analysis_ordinal"
        ),
    )

    op.create_table(
        "contract_obligations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("obligated_party", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("beneficiary", sa.Text(), nullable=True),
        sa.Column("conditions", postgresql.JSONB(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "ordinal > 0", name="ck_contract_obligations_ordinal_positive"
        ),
        sa.CheckConstraint(
            "source_page > 0", name="ck_contract_obligations_source_page_positive"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_contract_obligations_confidence_range",
        ),
        sa.CheckConstraint(
            "char_length(description) > 0",
            name="ck_contract_obligations_description_nonempty",
        ),
        sa.CheckConstraint(
            "char_length(evidence) > 0",
            name="ck_contract_obligations_evidence_nonempty",
        ),
        sa.UniqueConstraint(
            "analysis_id", "ordinal", name="uq_contract_obligations_analysis_ordinal"
        ),
    )

    op.create_table(
        "contract_payment_terms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("payer", sa.Text(), nullable=True),
        sa.Column("payee", sa.Text(), nullable=True),
        sa.Column("amount_text", sa.Text(), nullable=True),
        sa.Column("schedule_text", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "ordinal > 0", name="ck_contract_payment_terms_ordinal_positive"
        ),
        sa.CheckConstraint(
            "source_page > 0", name="ck_contract_payment_terms_source_page_positive"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_contract_payment_terms_confidence_range",
        ),
        sa.CheckConstraint(
            "char_length(evidence) > 0",
            name="ck_contract_payment_terms_evidence_nonempty",
        ),
        sa.UniqueConstraint(
            "analysis_id",
            "ordinal",
            name="uq_contract_payment_terms_analysis_ordinal",
        ),
    )

    op.create_table(
        "contract_clauses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("conditions", postgresql.JSONB(), nullable=False),
        sa.Column("notice_period_text", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint("ordinal > 0", name="ck_contract_clauses_ordinal_positive"),
        sa.CheckConstraint(
            "source_page > 0", name="ck_contract_clauses_source_page_positive"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_contract_clauses_confidence_range",
        ),
        sa.CheckConstraint(
            "category IN ('renewal', 'termination', 'liability', 'confidentiality')",
            name="ck_contract_clauses_category_valid",
        ),
        sa.CheckConstraint(
            "char_length(title) > 0", name="ck_contract_clauses_title_nonempty"
        ),
        sa.CheckConstraint(
            "char_length(evidence) > 0", name="ck_contract_clauses_evidence_nonempty"
        ),
        sa.UniqueConstraint(
            "analysis_id", "ordinal", name="uq_contract_clauses_analysis_ordinal"
        ),
    )


def downgrade() -> None:
    op.drop_table("contract_clauses")
    op.drop_table("contract_payment_terms")
    op.drop_table("contract_obligations")
    op.drop_table("contract_parties")
