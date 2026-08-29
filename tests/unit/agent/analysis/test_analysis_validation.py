"""Deterministic per-item validation: valid quotes, wrong/missing pages,
duplicates, date normalization contradictions, and empty lists."""

from agent.analysis.types import FindingCandidate, ImportantDateCandidate, RiskCandidate
from agent.analysis.validation import (
    dedupe_dates,
    dedupe_findings,
    dedupe_risks,
    validate_finding,
    validate_important_date,
    validate_risk,
)

PAGES = {1: "This Agreement renews automatically each year on January 1, 2027."}


def _finding(**overrides: object) -> FindingCandidate:
    base: dict[str, object] = {
        "title": "Auto-renewal",
        "description": "Renews automatically.",
        "category": "renewal",
        "importance": "high",
        "source_page": 1,
        "evidence": "renews automatically each year",
        "confidence": 0.9,
    }
    base.update(overrides)
    return FindingCandidate.model_validate(base)


def _date(**overrides: object) -> ImportantDateCandidate:
    base: dict[str, object] = {
        "label": "Renewal date",
        "raw_value": "January 1, 2027",
        "normalized_date": "2027-01-01",
        "source_page": 1,
        "evidence": "each year on January 1, 2027",
        "confidence": 0.8,
    }
    base.update(overrides)
    return ImportantDateCandidate.model_validate(base)


def _risk(**overrides: object) -> RiskCandidate:
    base: dict[str, object] = {
        "title": "Auto-renewal risk",
        "description": "May renew without notice.",
        "category": "renewal",
        "severity": "medium",
        "evidence": [{"page": 1, "text": "renews automatically each year"}],
        "confidence": 0.7,
    }
    base.update(overrides)
    return RiskCandidate.model_validate(base)


def test_valid_finding_passes() -> None:
    assert validate_finding(_finding(), PAGES).valid is True


def test_finding_missing_page_fails() -> None:
    result = validate_finding(_finding(source_page=9), PAGES)
    assert result.valid is False
    assert "page 9" in (result.error or "")


def test_finding_quote_not_on_page_fails() -> None:
    result = validate_finding(_finding(evidence="not present anywhere"), PAGES)
    assert result.valid is False


def test_valid_date_passes() -> None:
    assert validate_important_date(_date(), PAGES).valid is True


def test_date_with_null_normalized_value_passes() -> None:
    result = validate_important_date(_date(normalized_date=None), PAGES)
    assert result.valid is True


def test_date_normalized_year_contradicts_raw_value_fails() -> None:
    result = validate_important_date(_date(normalized_date="2099-01-01"), PAGES)
    assert result.valid is False
    assert "contradicts" in (result.error or "")


def test_date_malformed_normalized_date_fails() -> None:
    result = validate_important_date(_date(normalized_date="not-a-date"), PAGES)
    assert result.valid is False


def test_valid_risk_passes() -> None:
    assert validate_risk(_risk(), PAGES).valid is True


def test_risk_with_invalid_evidence_page_fails() -> None:
    result = validate_risk(
        _risk(evidence=[{"page": 5, "text": "renews automatically each year"}]), PAGES
    )
    assert result.valid is False


def test_risk_with_duplicate_internal_evidence_fails() -> None:
    result = validate_risk(
        _risk(
            evidence=[
                {"page": 1, "text": "renews automatically each year"},
                {"page": 1, "text": "renews   automatically  each year"},
            ]
        ),
        PAGES,
    )
    assert result.valid is False


def test_dedupe_findings_by_page_and_normalized_evidence() -> None:
    findings = [_finding(), _finding(evidence="renews  automatically each  year")]
    assert len(dedupe_findings(findings)) == 1


def test_dedupe_dates_by_page_and_normalized_evidence() -> None:
    dates = [_date(), _date(evidence="each  year on January 1, 2027")]
    assert len(dedupe_dates(dates)) == 1


def test_dedupe_risks_by_evidence_set() -> None:
    risks = [_risk(), _risk()]
    assert len(dedupe_risks(risks)) == 1


def test_empty_lists_dedupe_to_empty() -> None:
    assert dedupe_findings([]) == []
    assert dedupe_dates([]) == []
    assert dedupe_risks([]) == []
