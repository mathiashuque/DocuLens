"""Pure, deterministic validation of generic analysis candidate items.

Reuses classification's whitespace normalization (the one documented,
conservative rule both features share) instead of redefining it. Each
finding/date/risk is validated independently so a caller can retry only the
invalid subset while keeping already-valid items untouched.
"""

import re
from dataclasses import dataclass

from agent.analysis.types import FindingCandidate, ImportantDateCandidate, RiskCandidate
from agent.classification.validation import normalize_whitespace

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FOUR_DIGIT_YEAR = re.compile(r"(?<!\d)(\d{4})(?!\d)")


@dataclass(frozen=True)
class ItemValidationResult:
    valid: bool
    error: str | None = None


def _quote_on_page(text: str, page: int, pages: dict[int, str]) -> str | None:
    page_text = pages.get(page)
    if page_text is None:
        return f"cites page {page}, which does not exist"
    normalized_quote = normalize_whitespace(text)
    if not normalized_quote:
        return "evidence quote is empty"
    if normalized_quote not in normalize_whitespace(page_text):
        return f"evidence quote does not appear on page {page}"
    return None


def validate_finding(
    finding: FindingCandidate, pages: dict[int, str]
) -> ItemValidationResult:
    error = _quote_on_page(finding.evidence, finding.source_page, pages)
    if error:
        return ItemValidationResult(valid=False, error=error)
    return ItemValidationResult(valid=True)


def validate_important_date(
    date: ImportantDateCandidate, pages: dict[int, str]
) -> ItemValidationResult:
    error = _quote_on_page(date.evidence, date.source_page, pages)
    if error:
        return ItemValidationResult(valid=False, error=error)

    if date.normalized_date is not None:
        if not _ISO_DATE.match(date.normalized_date):
            return ItemValidationResult(
                valid=False,
                error="normalized_date is not a valid ISO YYYY-MM-DD date",
            )
        raw_year_match = _FOUR_DIGIT_YEAR.search(date.raw_value)
        if raw_year_match and raw_year_match.group(1) != date.normalized_date[:4]:
            return ItemValidationResult(
                valid=False,
                error="normalized_date year contradicts raw_value",
            )
        evidence_year_match = _FOUR_DIGIT_YEAR.search(date.evidence)
        if (
            evidence_year_match
            and evidence_year_match.group(1) != date.normalized_date[:4]
        ):
            return ItemValidationResult(
                valid=False,
                error="normalized_date year contradicts evidence",
            )

    return ItemValidationResult(valid=True)


def validate_risk(risk: RiskCandidate, pages: dict[int, str]) -> ItemValidationResult:
    seen: set[tuple[int, str]] = set()
    for item in risk.evidence:
        error = _quote_on_page(item.text, item.page, pages)
        if error:
            return ItemValidationResult(valid=False, error=error)
        key = (item.page, normalize_whitespace(item.text))
        if key in seen:
            return ItemValidationResult(
                valid=False, error="duplicate evidence item within the same risk"
            )
        seen.add(key)
    return ItemValidationResult(valid=True)


def dedupe_findings(findings: list[FindingCandidate]) -> list[FindingCandidate]:
    seen: set[tuple[int, str]] = set()
    deduped: list[FindingCandidate] = []
    for finding in findings:
        key = (finding.source_page, normalize_whitespace(finding.evidence))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped


def dedupe_dates(dates: list[ImportantDateCandidate]) -> list[ImportantDateCandidate]:
    seen: set[tuple[int, str]] = set()
    deduped: list[ImportantDateCandidate] = []
    for date in dates:
        key = (date.source_page, normalize_whitespace(date.evidence))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(date)
    return deduped


def dedupe_risks(risks: list[RiskCandidate]) -> list[RiskCandidate]:
    seen: set[tuple[tuple[int, str], ...]] = set()
    deduped: list[RiskCandidate] = []
    for risk in risks:
        key = tuple(
            sorted(
                (item.page, normalize_whitespace(item.text)) for item in risk.evidence
            )
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(risk)
    return deduped
