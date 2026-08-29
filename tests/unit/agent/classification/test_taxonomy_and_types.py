"""Taxonomy/schema unit tests: only supported types, bounded structured output."""

import pytest
from pydantic import ValidationError

from agent.classification.taxonomy import ALLOWED_DOCUMENT_TYPES
from agent.classification.types import ClassificationCandidate


def _candidate(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "document_type": "contract",
        "confidence": 0.9,
        "reason": "Defines parties and obligations.",
        "evidence": [{"page": 1, "text": "This Agreement is entered into by..."}],
    }
    base.update(overrides)
    return base


def test_allowed_types_are_exactly_the_mvp_taxonomy() -> None:
    assert set(ALLOWED_DOCUMENT_TYPES) == {
        "contract",
        "technical_specification",
        "generic",
    }


def test_valid_candidate_parses() -> None:
    candidate = ClassificationCandidate.model_validate(_candidate())
    assert candidate.document_type == "contract"


def test_unsupported_document_type_rejected() -> None:
    with pytest.raises(ValidationError):
        ClassificationCandidate.model_validate(_candidate(document_type="invoice"))


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("nan"), float("inf")])
def test_non_finite_or_out_of_range_confidence_rejected(confidence: float) -> None:
    with pytest.raises(ValidationError):
        ClassificationCandidate.model_validate(_candidate(confidence=confidence))


def test_blank_reason_rejected() -> None:
    with pytest.raises(ValidationError):
        ClassificationCandidate.model_validate(_candidate(reason="   "))


def test_zero_evidence_items_rejected() -> None:
    with pytest.raises(ValidationError):
        ClassificationCandidate.model_validate(_candidate(evidence=[]))


def test_more_than_three_evidence_items_rejected() -> None:
    evidence = [{"page": 1, "text": f"quote {i}"} for i in range(4)]
    with pytest.raises(ValidationError):
        ClassificationCandidate.model_validate(_candidate(evidence=evidence))


def test_empty_evidence_text_rejected() -> None:
    with pytest.raises(ValidationError):
        ClassificationCandidate.model_validate(
            _candidate(evidence=[{"page": 1, "text": "   "}])
        )


def test_non_positive_evidence_page_rejected() -> None:
    with pytest.raises(ValidationError):
        ClassificationCandidate.model_validate(
            _candidate(evidence=[{"page": 0, "text": "quote"}])
        )
