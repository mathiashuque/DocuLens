"""Classification eligibility, idempotency, provider invocation, and
threshold/persistence orchestration.

Keeps FastAPI/SQLAlchemy details out of the pure `agent.classification`
functions and provider SDK types out of this module's own contract.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from agent.classification.classifier import ClassifiedResult, classify_document
from agent.classification.provider import ProviderUnavailableError
from agent.classification.providers.openai_provider import OpenAIClassificationProvider
from app.core.config import ClassificationSettings, load_classification_settings
from app.db.classification_repository import ClassificationRepository
from app.db.repository import DocumentRepository
from app.models.document import Document, DocumentClassification


class DocumentNotFoundError(Exception):
    """No document exists for the given ID."""


class TextlessDocumentError(Exception):
    """The document is `ocr_required` or otherwise has no extracted text."""


class ClassificationNotFoundError(Exception):
    """No completed classification exists yet for this document."""


def has_usable_text(document: Document) -> bool:
    if document.status == "ocr_required":
        return False
    return any(page.text.strip() for page in document.pages)


def _build_provider(
    settings: ClassificationSettings,
) -> OpenAIClassificationProvider:
    if not settings.api_key:
        raise ProviderUnavailableError("Classification provider is not configured.")
    return OpenAIClassificationProvider(
        api_key=settings.api_key,
        model=settings.model,
        timeout_seconds=settings.timeout_seconds,
        max_output_tokens=settings.max_output_tokens,
    )


async def _load_eligible_document(
    document_id: uuid.UUID, session: AsyncSession
) -> Document:
    document = await DocumentRepository(session).get(document_id)
    if document is None:
        raise DocumentNotFoundError(str(document_id))
    if not has_usable_text(document):
        raise TextlessDocumentError(str(document_id))
    return document


def _to_evidence_rows(result: ClassifiedResult) -> list[dict[str, object]]:
    return [{"page": item.page, "text": item.text} for item in result.evidence]


async def classify(
    document_id: uuid.UUID, session: AsyncSession
) -> DocumentClassification:
    """Classify a document, or return its existing completed result.

    Idempotent for an already-completed document: no second provider call is
    made.
    """
    document = await _load_eligible_document(document_id, session)

    classification_repository = ClassificationRepository(session)
    existing = await classification_repository.get_latest_completed(document_id)
    if existing is not None:
        return existing

    settings = load_classification_settings()
    provider = _build_provider(settings)

    section_titles = [section.title for section in document.sections]
    pages = [(page.page_number, page.text) for page in document.pages]

    result = await classify_document(
        filename=document.filename,
        pages=pages,
        section_titles=section_titles,
        provider=provider,
        confidence_threshold=settings.confidence_threshold,
    )

    return await classification_repository.create(
        document_id=document_id,
        document_type=result.document_type,
        confidence=result.confidence,
        reason=result.reason,
        evidence=_to_evidence_rows(result),
        provider=result.provider,
        model=result.model,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )


async def get_latest_classification(
    document_id: uuid.UUID, session: AsyncSession
) -> DocumentClassification:
    document = await DocumentRepository(session).get(document_id)
    if document is None:
        raise DocumentNotFoundError(str(document_id))

    classification = await ClassificationRepository(session).get_latest_completed(
        document_id
    )
    if classification is None:
        raise ClassificationNotFoundError(str(document_id))
    return classification
