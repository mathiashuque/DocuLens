"""Typed schema unit tests: bounded fields, enums, and finite confidence."""

import pytest
from pydantic import ValidationError

from agent.analysis.types import (
    DocumentSummaryCandidate,
    FindingCandidate,
    GenericAnalysisCandidate,
    ImportantDateCandidate,
    RiskCandidate,
)


def test_summary_dedupes_key_topics() -> None:
    summary = DocumentSummaryCandidate(
        purpose="p", summary="s", key_topics=["a", "a", " b ", ""]
    )
    assert summary.key_topics == ["a", "b"]


def test_finding_requires_valid_importance() -> None:
    with pytest.raises(ValidationError):
        FindingCandidate(
            title="t",
            description="d",
            category="c",
            importance="urgent",  # type: ignore[arg-type]
            source_page=1,
            evidence="e",
            confidence=0.5,
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.1, float("nan"), float("inf")])
def test_finding_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        FindingCandidate(
            title="t",
            description="d",
            category="c",
            importance="high",
            source_page=1,
            evidence="e",
            confidence=confidence,
        )


def test_finding_rejects_non_positive_source_page() -> None:
    with pytest.raises(ValidationError):
        FindingCandidate(
            title="t",
            description="d",
            category="c",
            importance="high",
            source_page=0,
            evidence="e",
            confidence=0.5,
        )


def test_important_date_allows_null_normalized_date() -> None:
    date = ImportantDateCandidate(
        label="Renewal",
        raw_value="sometime next spring",
        normalized_date=None,
        source_page=2,
        evidence="renews next spring",
        confidence=0.4,
    )
    assert date.normalized_date is None


def test_risk_requires_at_least_one_evidence_item() -> None:
    with pytest.raises(ValidationError):
        RiskCandidate(
            title="t",
            description="d",
            category="c",
            severity="high",
            evidence=[],
            confidence=0.5,
        )


def test_risk_rejects_more_than_three_evidence_items() -> None:
    with pytest.raises(ValidationError):
        RiskCandidate(
            title="t",
            description="d",
            category="c",
            severity="high",
            evidence=[{"page": i, "text": f"q{i}"} for i in range(1, 5)],
            confidence=0.5,
        )


def test_generic_analysis_candidate_allows_empty_lists() -> None:
    candidate = GenericAnalysisCandidate(
        summary=DocumentSummaryCandidate(purpose="p", summary="s"),
        findings=[],
        important_dates=[],
        risks=[],
    )
    assert candidate.findings == []
    assert candidate.important_dates == []
    assert candidate.risks == []
