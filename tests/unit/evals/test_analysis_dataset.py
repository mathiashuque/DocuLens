"""Dataset fixture checks, and running real validation logic (not a stored
mock) over fixture predictions to exercise the invalid-evidence, duplicate-
claim, and uncertain-date scenarios end to end."""

import json
from pathlib import Path

from agent.analysis.types import FindingCandidate, ImportantDateCandidate
from agent.analysis.validation import (
    dedupe_findings,
    validate_finding,
    validate_important_date,
)
from agent.classification.taxonomy import ALLOWED_DOCUMENT_TYPES

DATASET_PATH = (
    Path(__file__).resolve().parents[3] / "evals" / "datasets" / "analysis_v1.json"
)


def _load_samples() -> list[dict]:
    return json.loads(DATASET_PATH.read_text())["samples"]


def test_dataset_covers_all_required_scenarios() -> None:
    samples = {sample["sample_id"] for sample in _load_samples()}
    required = {
        "generic-findings-and-date-001",
        "contract-fallback-001",
        "technical-spec-fallback-001",
        "expected-empty-001",
        "invalid-evidence-001",
        "duplicate-claims-001",
        "uncertain-date-001",
        "prompt-injection-001",
    }
    assert required.issubset(samples)


def test_dataset_document_types_are_supported() -> None:
    for sample in _load_samples():
        assert sample["document_type"] in ALLOWED_DOCUMENT_TYPES


def test_dataset_sample_ids_are_unique() -> None:
    ids = [sample["sample_id"] for sample in _load_samples()]
    assert len(ids) == len(set(ids))


def _pages_for(sample: dict) -> dict[int, str]:
    return {int(page): text for page, text in sample["pages"].items()}


def _finding_from_expected(expected: dict) -> FindingCandidate:
    return FindingCandidate(
        title="t",
        description="d",
        category="c",
        importance="medium",
        source_page=expected["source_page"],
        evidence=expected["evidence_contains"],
        confidence=0.7,
    )


def test_expected_findings_validate_against_their_own_pages() -> None:
    """A well-formed extractor's evidence (matching the expected item
    verbatim) must validate — proves the fixtures are internally consistent."""
    for sample in _load_samples():
        pages = _pages_for(sample)
        for expected in sample["expected_findings"]:
            finding = _finding_from_expected(expected)
            result = validate_finding(finding, pages)
            assert result.valid, f"{sample['sample_id']}: {result.error}"


def test_invalid_evidence_sample_is_rejected() -> None:
    sample = next(
        s for s in _load_samples() if s["sample_id"] == "invalid-evidence-001"
    )
    pages = _pages_for(sample)
    bad_finding = FindingCandidate(
        title="t",
        description="d",
        category="c",
        importance="low",
        source_page=1,
        evidence="text that does not appear on the page at all",
        confidence=0.5,
    )
    result = validate_finding(bad_finding, pages)
    assert result.valid is False


def test_duplicate_claims_sample_dedupes_to_one_finding() -> None:
    sample = next(
        s for s in _load_samples() if s["sample_id"] == "duplicate-claims-001"
    )
    expected = sample["expected_findings"][0]
    duplicated = [_finding_from_expected(expected), _finding_from_expected(expected)]

    assert len(dedupe_findings(duplicated)) == 1


def test_uncertain_date_sample_keeps_normalized_date_null() -> None:
    sample = next(s for s in _load_samples() if s["sample_id"] == "uncertain-date-001")
    pages = _pages_for(sample)
    expected = sample["expected_dates"][0]
    date = ImportantDateCandidate(
        label="Renewal",
        raw_value="next spring",
        normalized_date=None,
        source_page=expected["source_page"],
        evidence=expected["evidence_contains"],
        confidence=0.4,
    )
    result = validate_important_date(date, pages)
    assert result.valid is True
    assert date.normalized_date is None


def test_expected_empty_sample_has_no_expected_items_in_any_category() -> None:
    sample = next(s for s in _load_samples() if s["sample_id"] == "expected-empty-001")
    assert sample["expected_findings"] == []
    assert sample["expected_dates"] == []
    assert sample["expected_risks"] == []
