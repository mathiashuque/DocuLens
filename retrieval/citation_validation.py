"""Deterministic application-logic validation of a grounded-answer
candidate's citations against the exact context supplied to the provider and
the document's original persisted page text.

Runs after provider structured-output parsing and before the candidate is
ever returned to a caller. Never repairs a quote semantically and never
accepts a paraphrase: every citation's evidence must appear verbatim (after
the one documented, conservative whitespace normalization) both in the
context block the provider actually saw and in the original persisted text
of the exact physical page it claims.
"""

import uuid
from dataclasses import dataclass

from agent.classification.validation import normalize_whitespace
from agent.grounded_qa.types import CitationCandidate, GroundedAnswerCandidate
from retrieval.grounded_qa import EvidenceContextItem

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "The document does not contain enough evidence to answer this question."
)


@dataclass(frozen=True)
class ValidatedCitation:
    chunk_id: uuid.UUID
    page: int
    evidence: str


@dataclass(frozen=True)
class CitationValidationResult:
    valid: bool
    errors: tuple[str, ...]
    citations: tuple[ValidatedCitation, ...]


def _validate_one_citation(
    citation: CitationCandidate,
    context_by_id: dict[str, EvidenceContextItem],
    document_pages: dict[int, str],
) -> tuple[ValidatedCitation | None, str | None]:
    context_item = context_by_id.get(citation.chunk_id)
    if context_item is None:
        return (
            None,
            f"citation references chunk {citation.chunk_id!r}, which was not in the retrieved context for this request",
        )

    if not (context_item.page_start <= citation.page <= context_item.page_end):
        return None, (
            f"citation claims page {citation.page}, outside chunk "
            f"{citation.chunk_id!r}'s page range "
            f"{context_item.page_start}-{context_item.page_end}"
        )

    normalized_evidence = normalize_whitespace(citation.evidence)
    if not normalized_evidence:
        return None, f"citation for chunk {citation.chunk_id!r} has empty evidence"

    if normalized_evidence not in normalize_whitespace(context_item.text):
        return None, (
            f"citation evidence for chunk {citation.chunk_id!r} was not present "
            "in the context supplied to the generator"
        )

    page_text = document_pages.get(citation.page)
    if page_text is None:
        return None, f"citation claims page {citation.page}, which does not exist"

    if normalized_evidence not in normalize_whitespace(page_text):
        return None, (
            f"citation evidence for chunk {citation.chunk_id!r} does not appear "
            f"on page {citation.page}'s original text"
        )

    return (
        ValidatedCitation(
            chunk_id=context_item.chunk_id,
            page=citation.page,
            evidence=citation.evidence,
        ),
        None,
    )


def validate_candidate(
    candidate: GroundedAnswerCandidate,
    *,
    context_items: list[EvidenceContextItem],
    document_pages: dict[int, str],
) -> CitationValidationResult:
    """Validate one generated candidate against the exact retrieved context
    and the document's original page text.

    `document_pages` maps physical page number to that page's exact
    persisted text, scoped to the requested document only (so a citation can
    never resolve against another document's pages).
    """
    if candidate.status == "insufficient_evidence":
        if candidate.citations:
            return CitationValidationResult(
                valid=False,
                errors=("insufficient_evidence candidate must not include citations",),
                citations=(),
            )
        return CitationValidationResult(valid=True, errors=(), citations=())

    if not candidate.answer.strip():
        return CitationValidationResult(
            valid=False,
            errors=("answered candidate has an empty answer",),
            citations=(),
        )
    if not candidate.citations:
        return CitationValidationResult(
            valid=False,
            errors=("answered candidate must include at least one citation",),
            citations=(),
        )

    context_by_id = {str(item.chunk_id): item for item in context_items}
    errors: list[str] = []
    seen: set[tuple[uuid.UUID, int, str]] = set()
    validated: list[ValidatedCitation] = []

    for citation in candidate.citations:
        result, error = _validate_one_citation(citation, context_by_id, document_pages)
        if error is not None:
            errors.append(error)
            continue
        assert result is not None
        key = (result.chunk_id, result.page, normalize_whitespace(result.evidence))
        if key in seen:
            continue
        seen.add(key)
        validated.append(result)

    if errors:
        return CitationValidationResult(valid=False, errors=tuple(errors), citations=())
    if not validated:
        return CitationValidationResult(
            valid=False,
            errors=("no citation remained after validation",),
            citations=(),
        )
    return CitationValidationResult(valid=True, errors=(), citations=tuple(validated))
