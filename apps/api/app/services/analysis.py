"""Analysis eligibility, idempotency, classification reuse, graph
invocation, and result persistence orchestration.

Reuses the classification service's own eligibility gate and error types
instead of duplicating them: `classify()` both ensures a completed
classification exists (reusing one if already persisted, exactly as the
classification feature intends) and enforces the same `ocr_required`/
textless/unknown-document gate this feature also needs.
"""

import uuid
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from agent.analysis.graph import run_analysis_graph
from agent.analysis.provider import ProviderUnavailableError
from agent.analysis.providers.openai_provider import OpenAIAnalysisProvider
from agent.analysis.result import AnalysisFailedError
from agent.analysis.state import AnalysisState
from agent.analysis.taxonomy import GENERIC_EXTRACTOR
from agent.classification.taxonomy import DocumentType
from agent.extractors.contract.context import SectionSpan
from agent.extractors.contract.providers.openai_provider import OpenAIContractProvider
from agent.extractors.contract.taxonomy import CONTRACT_EXTRACTOR
from app.core.config import AnalysisSettings, load_analysis_settings
from app.db.analysis_repository import AnalysisRepository
from app.db.repository import DocumentRepository
from app.models.document import Document, DocumentAnalysis
from app.services.classification import DocumentNotFoundError, TextlessDocumentError
from app.services.classification import classify as ensure_classification_result

__all__ = [
    "AnalysisNotFoundError",
    "DocumentNotFoundError",
    "TextlessDocumentError",
    "analyze",
    "get_latest_analysis",
]


class AnalysisNotFoundError(Exception):
    """No completed analysis exists yet for this document."""


def _build_provider(settings: AnalysisSettings) -> OpenAIAnalysisProvider:
    if not settings.api_key:
        raise ProviderUnavailableError("Analysis provider is not configured.")
    return OpenAIAnalysisProvider(
        api_key=settings.api_key,
        model=settings.model,
        timeout_seconds=settings.timeout_seconds,
        max_output_tokens=settings.max_output_tokens,
    )


def _build_contract_provider(settings: AnalysisSettings) -> OpenAIContractProvider:
    """Reuses the same model/timeout/token configuration as the generic
    analysis provider; the contract route does not warrant a second set of
    provider settings."""
    if not settings.api_key:
        raise ProviderUnavailableError("Contract provider is not configured.")
    return OpenAIContractProvider(
        api_key=settings.api_key,
        model=settings.model,
        timeout_seconds=settings.timeout_seconds,
        max_output_tokens=settings.max_output_tokens,
    )


async def _load_document(document_id: uuid.UUID, session: AsyncSession) -> Document:
    document = await DocumentRepository(session).get(document_id)
    if document is None:
        raise DocumentNotFoundError(str(document_id))
    return document


async def analyze(document_id: uuid.UUID, session: AsyncSession) -> DocumentAnalysis:
    """Analyze a document, or return its existing completed result.

    Idempotent for an already-completed document: no second provider call
    (for classification or analysis) is made.
    """
    document = await _load_document(document_id, session)

    analysis_repository = AnalysisRepository(session)
    existing = await analysis_repository.get_latest_completed(document_id)
    if existing is not None:
        return existing

    classification = await ensure_classification_result(document_id, session)

    settings = load_analysis_settings()
    provider = _build_provider(settings)

    pages = [(page.page_number, page.text) for page in document.pages]
    section_titles = [section.title for section in document.sections]
    sections = [
        SectionSpan(
            title=section.title,
            page_start=section.page_start,
            page_end=section.page_end,
        )
        for section in document.sections
    ]
    document_type = cast(DocumentType, classification.document_type)

    initial_state: AnalysisState = {
        "document_id": str(document_id),
        "filename": document.filename,
        "pages": pages,
        "section_titles": section_titles,
        "sections": sections,
        "provider": provider,
        "budget_chars": settings.budget_chars,
        "document_type": document_type,
        "classification_confidence": classification.confidence,
    }
    if document_type == "contract":
        initial_state["contract_provider"] = _build_contract_provider(settings)

    final_state = await run_analysis_graph(initial_state)
    result = final_state.get("result")
    if final_state.get("status") != "completed" or result is None:
        raise AnalysisFailedError(
            final_state.get("failure_reason") or "Analysis failed."
        )

    extractor = (
        CONTRACT_EXTRACTOR if result.specialized is not None else GENERIC_EXTRACTOR
    )
    return await analysis_repository.create(
        document_id=document_id,
        document_type=classification.document_type,
        extractor=extractor,
        result=result,
    )


async def get_latest_analysis(
    document_id: uuid.UUID, session: AsyncSession
) -> DocumentAnalysis:
    document = await DocumentRepository(session).get(document_id)
    if document is None:
        raise DocumentNotFoundError(str(document_id))

    analysis = await AnalysisRepository(session).get_latest_completed(document_id)
    if analysis is None:
        raise AnalysisNotFoundError(str(document_id))
    return analysis
