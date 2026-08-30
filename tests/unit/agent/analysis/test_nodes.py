"""Direct tests for every graph node, called as plain functions (no graph
runtime involved) so each node's behavior is independently verifiable."""

import pytest

from agent.analysis.nodes.build_extraction_context import build_extraction_context
from agent.analysis.nodes.ensure_classification import ensure_classification
from agent.analysis.nodes.fail_safely import fail_safely
from agent.analysis.nodes.finalize_completed_analysis import finalize_completed_analysis
from agent.analysis.nodes.load_document import load_document
from agent.analysis.nodes.validate_analysis import (
    route_after_precondition,
    route_after_validation,
    validate_analysis,
)
from agent.analysis.provider import ProviderMetadata
from agent.analysis.types import DocumentSummaryCandidate, FindingCandidate


def test_load_document_fails_when_all_pages_blank() -> None:
    result = load_document({"pages": [(1, "  "), (2, "")]})
    assert result["status"] == "failed"
    assert "no extracted text" in result["failure_reason"]


def test_load_document_passes_with_usable_text() -> None:
    result = load_document({"pages": [(1, "hello")]})
    assert result["status"] == "pending"


def test_ensure_classification_fails_without_document_type() -> None:
    result = ensure_classification({"status": "pending"})
    assert result["status"] == "failed"


def test_ensure_classification_noop_when_document_type_present() -> None:
    result = ensure_classification({"status": "pending", "document_type": "generic"})
    assert result == {}


def test_ensure_classification_short_circuits_when_already_failed() -> None:
    result = ensure_classification({"status": "failed"})
    assert result == {}


def test_build_extraction_context_produces_page_labeled_excerpts() -> None:
    result = build_extraction_context(
        {
            "status": "pending",
            "filename": "doc.pdf",
            "pages": [(1, "hello world")],
            "section_titles": [],
        }
    )
    context = result["context"]
    assert context.excerpts[0].page == 1


def test_build_extraction_context_short_circuits_when_failed() -> None:
    assert build_extraction_context({"status": "failed"}) == {}


def test_route_after_precondition() -> None:
    assert route_after_precondition({"status": "failed"}) == "fail"
    assert route_after_precondition({"status": "pending"}) == "continue"


def test_validate_analysis_splits_valid_and_invalid_items() -> None:
    pages = [(1, "The term renews automatically each year.")]
    valid_finding = FindingCandidate(
        title="Auto-renewal",
        description="d",
        category="renewal",
        importance="high",
        source_page=1,
        evidence="renews automatically each year",
        confidence=0.9,
    )
    invalid_finding = FindingCandidate(
        title="Bad",
        description="d",
        category="renewal",
        importance="low",
        source_page=1,
        evidence="not present on the page",
        confidence=0.5,
    )
    result = validate_analysis(
        {
            "status": "pending",
            "pages": pages,
            "pending_findings": [valid_finding, invalid_finding],
            "pending_dates": [],
            "pending_risks": [],
            "valid_findings": [],
            "valid_dates": [],
            "valid_risks": [],
        }
    )
    assert len(result["valid_findings"]) == 1
    assert result["valid_findings"][0].title == "Auto-renewal"
    assert len(result["invalid_items"]) == 1
    assert result["invalid_items"][0]["kind"] == "finding"


def test_validate_analysis_preserves_already_accumulated_valid_items() -> None:
    pages = [(1, "hello world")]
    already_valid = FindingCandidate(
        title="Kept",
        description="d",
        category="c",
        importance="low",
        source_page=1,
        evidence="hello world",
        confidence=0.5,
    )
    result = validate_analysis(
        {
            "status": "pending",
            "pages": pages,
            "pending_findings": [],
            "pending_dates": [],
            "pending_risks": [],
            "valid_findings": [already_valid],
            "valid_dates": [],
            "valid_risks": [],
        }
    )
    assert result["valid_findings"] == [already_valid]
    assert result["invalid_items"] == []


@pytest.mark.parametrize(
    "state,expected",
    [
        ({"status": "failed"}, "fail"),
        ({"status": "pending", "invalid_items": []}, "persist"),
        ({"status": "pending", "invalid_items": [{}], "retry_count": 0}, "retry"),
        ({"status": "pending", "invalid_items": [{}], "retry_count": 1}, "fail"),
    ],
)
def test_route_after_validation(state: dict, expected: str) -> None:
    assert route_after_validation(state) == expected


def test_finalize_completed_analysis_assigns_ids_and_completes() -> None:
    summary = DocumentSummaryCandidate(purpose="p", summary="s")
    result = finalize_completed_analysis(
        {
            "summary": summary,
            "valid_findings": [],
            "valid_dates": [],
            "valid_risks": [],
            "provider_metadata": ProviderMetadata(provider="fake", model="m"),
            "retry_count": 0,
        }
    )
    assert result["status"] == "completed"
    assert result["result"].summary is summary


def test_finalize_completed_analysis_fails_without_metadata() -> None:
    result = finalize_completed_analysis(
        {
            "summary": DocumentSummaryCandidate(purpose="p", summary="s"),
            "valid_findings": [],
            "valid_dates": [],
            "valid_risks": [],
            "provider_metadata": None,
            "retry_count": 0,
        }
    )
    assert result["status"] == "failed"


def test_fail_safely_uses_existing_reason() -> None:
    result = fail_safely({"failure_reason": "custom reason"})
    assert result["status"] == "failed"
    assert result["failure_reason"] == "custom reason"
    assert result["result"] is None


def test_fail_safely_default_reason() -> None:
    result = fail_safely({})
    assert result["status"] == "failed"
    assert result["failure_reason"]
