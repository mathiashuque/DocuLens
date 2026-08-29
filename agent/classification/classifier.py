"""Classification orchestration: context selection, provider call, evidence
validation, one bounded corrective retry, and confidence thresholding.

Pure of any FastAPI/SQLAlchemy concerns. A later LangGraph node can call
`classify_document` directly without touching provider/validation logic.
"""

from dataclasses import dataclass

from agent.classification.context import select_classification_context
from agent.classification.prompt import SYSTEM_INSTRUCTION, render_user_content
from agent.classification.provider import (
    ProviderRequestError,
    StructuredClassificationProvider,
)
from agent.classification.taxonomy import DocumentType
from agent.classification.types import (
    ClassificationCandidate,
    ClassificationEvidenceItem,
)
from agent.classification.validation import validate_evidence

MAX_ATTEMPTS = 2


class ClassificationFailedError(Exception):
    """Both attempts produced invalid structured output or evidence.

    No completed classification is persisted; the caller maps this to a
    safe HTTP 502.
    """


@dataclass(frozen=True)
class ClassifiedResult:
    document_type: DocumentType
    confidence: float
    reason: str
    evidence: tuple[ClassificationEvidenceItem, ...]
    provider: str
    model: str
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None


def _apply_threshold(
    candidate: ClassificationCandidate, threshold: float
) -> tuple[DocumentType, str]:
    if candidate.document_type != "generic" and candidate.confidence < threshold:
        reason = (
            f"Classification was uncertain (confidence {candidate.confidence:.2f} "
            f"below the {threshold:.2f} threshold); routed to generic. "
            f"Original assessment: {candidate.reason}"
        )
        return "generic", reason
    return candidate.document_type, candidate.reason


def _correction_feedback(user_content: str, errors: tuple[str, ...]) -> str:
    joined = "; ".join(errors)
    return (
        f"{user_content}\n\n<correction_feedback>\n"
        f"Your previous response failed validation: {joined}. Return corrected "
        "structured output using only exact quotes copied verbatim from the "
        "excerpts above, each with its accurate page number.\n"
        "</correction_feedback>"
    )


async def classify_document(
    *,
    filename: str,
    pages: list[tuple[int, str]],
    section_titles: list[str],
    provider: StructuredClassificationProvider,
    confidence_threshold: float,
) -> ClassifiedResult:
    context = select_classification_context(
        filename=filename, pages=pages, section_titles=section_titles
    )
    pages_by_number = dict(pages)
    base_user_content = render_user_content(context)

    errors: tuple[str, ...] = ()
    for attempt in range(MAX_ATTEMPTS):
        user_content = (
            _correction_feedback(base_user_content, errors)
            if errors
            else base_user_content
        )
        try:
            candidate, metadata = await provider.classify(
                system_instruction=SYSTEM_INSTRUCTION, user_content=user_content
            )
        except ProviderRequestError as exc:
            is_last_attempt = attempt == MAX_ATTEMPTS - 1
            if not exc.retryable or is_last_attempt:
                raise
            errors = (str(exc),)
            continue

        result = validate_evidence(candidate, pages_by_number)
        if result.valid:
            final_type, final_reason = _apply_threshold(candidate, confidence_threshold)
            return ClassifiedResult(
                document_type=final_type,
                confidence=candidate.confidence,
                reason=final_reason,
                evidence=result.deduplicated_evidence,
                provider=metadata.provider,
                model=metadata.model,
                latency_ms=metadata.latency_ms,
                input_tokens=metadata.input_tokens,
                output_tokens=metadata.output_tokens,
            )

        if attempt == MAX_ATTEMPTS - 1:
            raise ClassificationFailedError(
                "Classification evidence failed validation after retry."
            )
        errors = result.errors

    raise ClassificationFailedError("Classification failed.")  # unreachable safeguard
