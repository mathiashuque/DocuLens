"""Grounded single-document question-answering orchestration.

Retrieves fresh document-scoped context for every question, generates a
structured candidate answer, and deterministically validates its citations
against the exact retrieved context and the document's original persisted
page text before ever returning it. At most one targeted repair call is
attempted for a candidate that is structurally usable (status "answered")
but fails citation validation. Never persists the question, answer, prompt,
or retrieved context.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from agent.grounded_qa.prompt import (
    REPAIR_SYSTEM_INSTRUCTION,
    SYSTEM_INSTRUCTION,
    EvidenceBlock,
    render_repair_content,
    render_user_content,
)
from agent.grounded_qa.provider import (
    GroundedQaProvider,
    ProviderRequestError,
    ProviderUnavailableError,
)
from agent.grounded_qa.providers.openai_provider import OpenAIGroundedQaProvider
from app.core.config import GroundedQaSettings, load_grounded_qa_settings
from app.db.repository import DocumentRepository
from app.services.search import (
    DEFAULT_TOP_K,
    DocumentNotFoundError,
    IncompatibleIndexError,
    IndexNotFoundError,
    InvalidQueryError,
    search_document,
)
from retrieval.citation_validation import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    ValidatedCitation,
    validate_candidate,
)
from retrieval.grounded_qa import EvidenceContextItem, build_context

__all__ = [
    "DEFAULT_TOP_K",
    "AnsweredResult",
    "DocumentNotFoundError",
    "IncompatibleIndexError",
    "IndexNotFoundError",
    "InsufficientEvidenceResult",
    "InvalidQueryError",
    "ProviderRequestError",
    "ProviderUnavailableError",
    "answer_question",
]


class InvalidQuestionError(Exception):
    """The question is blank or exceeds the configured maximum length, or
    `top_k` is out of the configured bounds."""


@dataclass(frozen=True)
class AnsweredResult:
    status: str
    answer: str
    citations: tuple[ValidatedCitation, ...]


@dataclass(frozen=True)
class InsufficientEvidenceResult:
    status: str
    answer: str
    citations: tuple[ValidatedCitation, ...]


def _normalize_question(raw_question: str, settings: GroundedQaSettings) -> str:
    question = " ".join(raw_question.split())
    if not question:
        raise InvalidQuestionError("Question must not be blank.")
    if len(question) > settings.max_question_chars:
        raise InvalidQuestionError(
            f"Question exceeds the configured maximum of "
            f"{settings.max_question_chars} characters."
        )
    return question


def _to_blocks(context_items: list[EvidenceContextItem]) -> list[EvidenceBlock]:
    return [
        EvidenceBlock(
            chunk_id=str(item.chunk_id),
            page_start=item.page_start,
            page_end=item.page_end,
            text=item.text,
        )
        for item in context_items
    ]


def _build_provider(settings: GroundedQaSettings) -> GroundedQaProvider:
    if not settings.api_key:
        raise ProviderUnavailableError("Grounded QA provider is not configured.")
    return OpenAIGroundedQaProvider(
        api_key=settings.api_key,
        model=settings.model,
        timeout_seconds=settings.timeout_seconds,
        max_output_tokens=settings.max_output_tokens,
    )


_INSUFFICIENT = InsufficientEvidenceResult(
    status="insufficient_evidence",
    answer=INSUFFICIENT_EVIDENCE_MESSAGE,
    citations=(),
)


async def answer_question(
    document_id: uuid.UUID,
    raw_question: str,
    top_k: int,
    session: AsyncSession,
    *,
    provider: GroundedQaProvider | None = None,
    quota_identity: str | None = None,
) -> AnsweredResult | InsufficientEvidenceResult:
    """Answer one bounded question for one completed document index.

    `provider` may be injected for tests; production callers omit it and get
    the configured OpenAI adapter, constructed lazily so a missing key never
    breaks retrieval-only or unrelated requests.

    Raises `DocumentNotFoundError`/`IndexNotFoundError` for 404s,
    `InvalidQuestionError`/`InvalidQueryError` for bad input,
    `IncompatibleIndexError` if the index predates the current embedding
    configuration, and the provider's own errors (mapped to 502/503 at the
    route) on failure.
    """
    settings = load_grounded_qa_settings()
    question = _normalize_question(raw_question, settings)

    if quota_identity is None:
        # Keeps the established injectable search boundary unchanged in
        # unmetered local/tests; reserve_quota is also a no-op in this mode.
        _, results = await search_document(document_id, question, top_k, session)
    else:
        _, results = await search_document(
            document_id,
            question,
            top_k,
            session,
            quota_identity=quota_identity,
        )

    context_items = build_context(
        results,
        max_chunks=settings.max_context_chunks,
        max_chars=settings.max_context_chars,
    )
    if not context_items:
        return _INSUFFICIENT

    document = await DocumentRepository(session).get(document_id)
    assert document is not None  # search_document already confirmed existence
    document_pages = {page.page_number: page.text for page in document.pages}

    active_provider = provider if provider is not None else _build_provider(settings)
    blocks = _to_blocks(context_items)
    user_content = render_user_content(question, blocks)

    candidate, _ = await active_provider.answer(
        system_instruction=SYSTEM_INSTRUCTION, user_content=user_content
    )
    validation = validate_candidate(
        candidate, context_items=context_items, document_pages=document_pages
    )

    if candidate.status == "insufficient_evidence":
        return _INSUFFICIENT

    if not validation.valid:
        repair_content = render_repair_content(
            question, blocks, list(validation.errors)
        )
        repaired, _ = await active_provider.repair(
            system_instruction=REPAIR_SYSTEM_INSTRUCTION, user_content=repair_content
        )
        if repaired.status == "insufficient_evidence":
            return _INSUFFICIENT
        repaired_validation = validate_candidate(
            repaired, context_items=context_items, document_pages=document_pages
        )
        if not repaired_validation.valid:
            return _INSUFFICIENT
        return AnsweredResult(
            status="answered",
            answer=repaired.answer,
            citations=repaired_validation.citations,
        )

    return AnsweredResult(
        status="answered", answer=candidate.answer, citations=validation.citations
    )
