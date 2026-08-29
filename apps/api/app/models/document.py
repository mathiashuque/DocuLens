"""Persistence models for documents and their page-preserving parse output."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent.analysis.taxonomy import ALLOWED_IMPORTANCE, ALLOWED_SEVERITY
from agent.classification.taxonomy import ALLOWED_DOCUMENT_TYPES
from agent.extractors.contract.taxonomy import ALLOWED_CLAUSE_CATEGORIES
from agent.extractors.technical_spec.taxonomy import (
    ALLOWED_CONSTRAINT_CATEGORIES,
    ALLOWED_PRIORITIES,
    ALLOWED_REQUIREMENT_CATEGORIES,
)
from app.models.base import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("page_count > 0", name="ck_documents_page_count_positive"),
        CheckConstraint(
            "status IN ('parsed', 'ocr_required')", name="ck_documents_status_valid"
        ),
        CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'", name="ck_documents_content_hash_format"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentPage.page_number",
    )
    sections: Mapped[list["DocumentSection"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentSection.ordinal",
    )
    classification: Mapped["DocumentClassification | None"] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    analysis: Mapped["DocumentAnalysis | None"] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "page_number", name="uq_document_pages_document_page_number"
        ),
        CheckConstraint(
            "page_number > 0", name="ck_document_pages_page_number_positive"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="pages")


class DocumentSection(Base):
    __tablename__ = "document_sections"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "ordinal", name="uq_document_sections_document_ordinal"
        ),
        CheckConstraint("ordinal > 0", name="ck_document_sections_ordinal_positive"),
        CheckConstraint("level > 0", name="ck_document_sections_level_positive"),
        CheckConstraint(
            "page_start > 0", name="ck_document_sections_page_start_positive"
        ),
        CheckConstraint(
            "page_end >= page_start", name="ck_document_sections_page_end_gte_start"
        ),
        CheckConstraint(
            "parent_section_id IS NULL OR parent_section_id != id",
            name="ck_document_sections_not_self_parent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_sections.id", ondelete="CASCADE"),
        nullable=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    section_path: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="sections")


class DocumentClassification(Base):
    """The single persisted completed classification for a document.

    Only completed, evidence-validated results are persisted; failed
    attempts are never stored. That, plus the unique `document_id`, is what
    makes POST idempotent and GET's "latest completed" lookup a direct
    single-row fetch.
    """

    __tablename__ = "document_classifications"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_document_classifications_document_id"),
        CheckConstraint(
            "document_type IN ("
            + ", ".join(f"'{value}'" for value in ALLOWED_DOCUMENT_TYPES)
            + ")",
            name="ck_document_classifications_document_type_valid",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_document_classifications_confidence_range",
        ),
        CheckConstraint(
            "status = 'completed'", name="ck_document_classifications_status_valid"
        ),
        CheckConstraint(
            "char_length(reason) > 0",
            name="ck_document_classifications_reason_nonempty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="classification")


class DocumentAnalysis(Base):
    """The single persisted completed generic analysis run for a document.

    Only completed, evidence-validated results are persisted; failed runs
    are never stored. As with classification, the unique `document_id` is
    what makes POST idempotent and GET a direct single-row fetch.
    """

    __tablename__ = "document_analyses"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_document_analyses_document_id"),
        CheckConstraint(
            "document_type IN ("
            + ", ".join(f"'{value}'" for value in ALLOWED_DOCUMENT_TYPES)
            + ")",
            name="ck_document_analyses_document_type_valid",
        ),
        CheckConstraint(
            "status = 'completed'", name="ck_document_analyses_status_valid"
        ),
        CheckConstraint(
            "char_length(summary_purpose) > 0",
            name="ck_document_analyses_summary_purpose_nonempty",
        ),
        CheckConstraint(
            "char_length(summary_text) > 0",
            name="ck_document_analyses_summary_text_nonempty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    extractor: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    summary_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_purpose: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary_key_topics: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="analysis")
    findings: Mapped[list["AnalysisFinding"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="AnalysisFinding.ordinal",
    )
    important_dates: Mapped[list["AnalysisImportantDate"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="AnalysisImportantDate.ordinal",
    )
    risks: Mapped[list["AnalysisRisk"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="AnalysisRisk.ordinal",
    )
    contract_parties: Mapped[list["ContractParty"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="ContractParty.ordinal",
    )
    contract_obligations: Mapped[list["ContractObligation"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="ContractObligation.ordinal",
    )
    contract_payment_terms: Mapped[list["ContractPaymentTerm"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="ContractPaymentTerm.ordinal",
    )
    contract_clauses: Mapped[list["ContractClause"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="ContractClause.ordinal",
    )
    technical_requirements: Mapped[list["TechnicalRequirement"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="TechnicalRequirement.ordinal",
    )
    technical_constraints: Mapped[list["TechnicalConstraint"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="TechnicalConstraint.ordinal",
    )
    technical_dependencies: Mapped[list["TechnicalDependency"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="TechnicalDependency.ordinal",
    )


class AnalysisFinding(Base):
    __tablename__ = "analysis_findings"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "ordinal", name="uq_analysis_findings_analysis_ordinal"
        ),
        CheckConstraint("ordinal > 0", name="ck_analysis_findings_ordinal_positive"),
        CheckConstraint(
            "source_page > 0", name="ck_analysis_findings_source_page_positive"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_analysis_findings_confidence_range",
        ),
        CheckConstraint(
            "importance IN (" + ", ".join(f"'{v}'" for v in ALLOWED_IMPORTANCE) + ")",
            name="ck_analysis_findings_importance_valid",
        ),
        CheckConstraint(
            "char_length(evidence) > 0", name="ck_analysis_findings_evidence_nonempty"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    importance: Mapped[str] = mapped_column(String(20), nullable=False)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    analysis: Mapped["DocumentAnalysis"] = relationship(back_populates="findings")


class AnalysisImportantDate(Base):
    __tablename__ = "analysis_important_dates"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "ordinal", name="uq_analysis_dates_analysis_ordinal"
        ),
        CheckConstraint("ordinal > 0", name="ck_analysis_dates_ordinal_positive"),
        CheckConstraint(
            "source_page > 0", name="ck_analysis_dates_source_page_positive"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_analysis_dates_confidence_range",
        ),
        CheckConstraint(
            "char_length(evidence) > 0", name="ck_analysis_dates_evidence_nonempty"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    analysis: Mapped["DocumentAnalysis"] = relationship(
        back_populates="important_dates"
    )


class AnalysisRisk(Base):
    __tablename__ = "analysis_risks"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "ordinal", name="uq_analysis_risks_analysis_ordinal"
        ),
        CheckConstraint("ordinal > 0", name="ck_analysis_risks_ordinal_positive"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_analysis_risks_confidence_range",
        ),
        CheckConstraint(
            "severity IN (" + ", ".join(f"'{v}'" for v in ALLOWED_SEVERITY) + ")",
            name="ck_analysis_risks_severity_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    analysis: Mapped["DocumentAnalysis"] = relationship(back_populates="risks")
    evidence: Mapped[list["AnalysisRiskEvidence"]] = relationship(
        back_populates="risk",
        cascade="all, delete-orphan",
        order_by="AnalysisRiskEvidence.ordinal",
    )


class AnalysisRiskEvidence(Base):
    __tablename__ = "analysis_risk_evidence"
    __table_args__ = (
        UniqueConstraint(
            "risk_id", "ordinal", name="uq_analysis_risk_evidence_risk_ordinal"
        ),
        CheckConstraint(
            "ordinal > 0", name="ck_analysis_risk_evidence_ordinal_positive"
        ),
        CheckConstraint("page > 0", name="ck_analysis_risk_evidence_page_positive"),
        CheckConstraint(
            "char_length(text) > 0", name="ck_analysis_risk_evidence_text_nonempty"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    risk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_risks.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    risk: Mapped["AnalysisRisk"] = relationship(back_populates="evidence")


class ContractParty(Base):
    __tablename__ = "contract_parties"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "ordinal", name="uq_contract_parties_analysis_ordinal"
        ),
        CheckConstraint("ordinal > 0", name="ck_contract_parties_ordinal_positive"),
        CheckConstraint(
            "source_page > 0", name="ck_contract_parties_source_page_positive"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_contract_parties_confidence_range",
        ),
        CheckConstraint(
            "char_length(name) > 0", name="ck_contract_parties_name_nonempty"
        ),
        CheckConstraint(
            "char_length(evidence) > 0", name="ck_contract_parties_evidence_nonempty"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    analysis: Mapped["DocumentAnalysis"] = relationship(
        back_populates="contract_parties"
    )


class ContractObligation(Base):
    __tablename__ = "contract_obligations"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "ordinal", name="uq_contract_obligations_analysis_ordinal"
        ),
        CheckConstraint("ordinal > 0", name="ck_contract_obligations_ordinal_positive"),
        CheckConstraint(
            "source_page > 0", name="ck_contract_obligations_source_page_positive"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_contract_obligations_confidence_range",
        ),
        CheckConstraint(
            "char_length(description) > 0",
            name="ck_contract_obligations_description_nonempty",
        ),
        CheckConstraint(
            "char_length(evidence) > 0",
            name="ck_contract_obligations_evidence_nonempty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    obligated_party: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    beneficiary: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    analysis: Mapped["DocumentAnalysis"] = relationship(
        back_populates="contract_obligations"
    )


class ContractPaymentTerm(Base):
    __tablename__ = "contract_payment_terms"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "ordinal", name="uq_contract_payment_terms_analysis_ordinal"
        ),
        CheckConstraint(
            "ordinal > 0", name="ck_contract_payment_terms_ordinal_positive"
        ),
        CheckConstraint(
            "source_page > 0", name="ck_contract_payment_terms_source_page_positive"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_contract_payment_terms_confidence_range",
        ),
        CheckConstraint(
            "char_length(evidence) > 0",
            name="ck_contract_payment_terms_evidence_nonempty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    payer: Mapped[str | None] = mapped_column(Text, nullable=True)
    payee: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    schedule_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    analysis: Mapped["DocumentAnalysis"] = relationship(
        back_populates="contract_payment_terms"
    )


class ContractClause(Base):
    __tablename__ = "contract_clauses"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "ordinal", name="uq_contract_clauses_analysis_ordinal"
        ),
        CheckConstraint("ordinal > 0", name="ck_contract_clauses_ordinal_positive"),
        CheckConstraint(
            "source_page > 0", name="ck_contract_clauses_source_page_positive"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_contract_clauses_confidence_range",
        ),
        CheckConstraint(
            "category IN ("
            + ", ".join(f"'{value}'" for value in ALLOWED_CLAUSE_CATEGORIES)
            + ")",
            name="ck_contract_clauses_category_valid",
        ),
        CheckConstraint(
            "char_length(title) > 0", name="ck_contract_clauses_title_nonempty"
        ),
        CheckConstraint(
            "char_length(evidence) > 0", name="ck_contract_clauses_evidence_nonempty"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    notice_period_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    analysis: Mapped["DocumentAnalysis"] = relationship(
        back_populates="contract_clauses"
    )


class TechnicalRequirement(Base):
    __tablename__ = "technical_requirements"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "ordinal", name="uq_technical_requirements_analysis_ordinal"
        ),
        CheckConstraint(
            "ordinal > 0", name="ck_technical_requirements_ordinal_positive"
        ),
        CheckConstraint(
            "source_page > 0", name="ck_technical_requirements_source_page_positive"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_technical_requirements_confidence_range",
        ),
        CheckConstraint(
            "category IN ("
            + ", ".join(f"'{value}'" for value in ALLOWED_REQUIREMENT_CATEGORIES)
            + ")",
            name="ck_technical_requirements_category_valid",
        ),
        CheckConstraint(
            "priority IN ("
            + ", ".join(f"'{value}'" for value in ALLOWED_PRIORITIES)
            + ")",
            name="ck_technical_requirements_priority_valid",
        ),
        CheckConstraint(
            "char_length(statement) > 0",
            name="ck_technical_requirements_statement_nonempty",
        ),
        CheckConstraint(
            "char_length(evidence) > 0",
            name="ck_technical_requirements_evidence_nonempty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    identifier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    actor: Mapped[str | None] = mapped_column(Text, nullable=True)
    measurable_criterion: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    analysis: Mapped["DocumentAnalysis"] = relationship(
        back_populates="technical_requirements"
    )


class TechnicalConstraint(Base):
    __tablename__ = "technical_constraints"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "ordinal", name="uq_technical_constraints_analysis_ordinal"
        ),
        CheckConstraint(
            "ordinal > 0", name="ck_technical_constraints_ordinal_positive"
        ),
        CheckConstraint(
            "source_page > 0", name="ck_technical_constraints_source_page_positive"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_technical_constraints_confidence_range",
        ),
        CheckConstraint(
            "category IN ("
            + ", ".join(f"'{value}'" for value in ALLOWED_CONSTRAINT_CATEGORIES)
            + ")",
            name="ck_technical_constraints_category_valid",
        ),
        CheckConstraint(
            "char_length(statement) > 0",
            name="ck_technical_constraints_statement_nonempty",
        ),
        CheckConstraint(
            "char_length(evidence) > 0",
            name="ck_technical_constraints_evidence_nonempty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    analysis: Mapped["DocumentAnalysis"] = relationship(
        back_populates="technical_constraints"
    )


class TechnicalDependency(Base):
    __tablename__ = "technical_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "ordinal", name="uq_technical_dependencies_analysis_ordinal"
        ),
        CheckConstraint(
            "ordinal > 0", name="ck_technical_dependencies_ordinal_positive"
        ),
        CheckConstraint(
            "source_page > 0", name="ck_technical_dependencies_source_page_positive"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_technical_dependencies_confidence_range",
        ),
        CheckConstraint(
            "char_length(name) > 0", name="ck_technical_dependencies_name_nonempty"
        ),
        CheckConstraint(
            "char_length(description) > 0",
            name="ck_technical_dependencies_description_nonempty",
        ),
        CheckConstraint(
            "char_length(evidence) > 0",
            name="ck_technical_dependencies_evidence_nonempty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    dependency_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    analysis: Mapped["DocumentAnalysis"] = relationship(
        back_populates="technical_dependencies"
    )
