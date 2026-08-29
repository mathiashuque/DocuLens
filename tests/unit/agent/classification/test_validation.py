"""Deterministic evidence validation: valid quotes, wrong/missing pages,
empty/duplicate quotes, whitespace normalization, and page mismatches."""

from agent.classification.types import ClassificationCandidate
from agent.classification.validation import normalize_whitespace, validate_evidence


def _candidate(evidence: list[dict[str, object]]) -> ClassificationCandidate:
    return ClassificationCandidate.model_validate(
        {
            "document_type": "contract",
            "confidence": 0.9,
            "reason": "reason",
            "evidence": evidence,
        }
    )


def test_valid_quote_on_correct_page_passes() -> None:
    pages = {1: "This Agreement is entered into by the parties."}
    candidate = _candidate([{"page": 1, "text": "This Agreement is entered into"}])

    result = validate_evidence(candidate, pages)

    assert result.valid is True
    assert len(result.deduplicated_evidence) == 1


def test_missing_page_fails() -> None:
    pages = {1: "some text"}
    candidate = _candidate([{"page": 2, "text": "some text"}])

    result = validate_evidence(candidate, pages)

    assert result.valid is False
    assert "page 2" in result.errors[0]


def test_quote_not_present_on_cited_page_fails() -> None:
    pages = {1: "The rent is due monthly."}
    candidate = _candidate([{"page": 1, "text": "This clause does not exist here"}])

    result = validate_evidence(candidate, pages)

    assert result.valid is False


def test_paraphrased_quote_is_rejected_not_repaired() -> None:
    pages = {1: "The tenant shall pay rent on the first day of each month."}
    candidate = _candidate([{"page": 1, "text": "Rent is due monthly"}])

    result = validate_evidence(candidate, pages)

    assert result.valid is False


def test_whitespace_normalization_tolerates_line_wraps() -> None:
    pages = {1: "This Agreement\nis entered   into by\nthe parties."}
    candidate = _candidate([{"page": 1, "text": "This Agreement is entered into by"}])

    result = validate_evidence(candidate, pages)

    assert result.valid is True


def test_normalize_whitespace_collapses_runs_and_strips() -> None:
    assert normalize_whitespace("  a\n\tb   c  ") == "a b c"


def test_duplicate_evidence_items_are_deduplicated() -> None:
    pages = {1: "Payment terms are net thirty days."}
    candidate = _candidate(
        [
            {"page": 1, "text": "Payment terms are net thirty days"},
            {"page": 1, "text": "Payment terms are   net thirty days"},
        ]
    )

    result = validate_evidence(candidate, pages)

    assert result.valid is True
    assert len(result.deduplicated_evidence) == 1


def test_mixed_valid_and_invalid_evidence_fails_overall() -> None:
    pages = {1: "Valid clause text here."}
    candidate = _candidate(
        [
            {"page": 1, "text": "Valid clause text"},
            {"page": 3, "text": "Valid clause text"},
        ]
    )

    result = validate_evidence(candidate, pages)

    assert result.valid is False
