"""Pure validation node: deduplicates and validates the current pending
items, accumulating already-valid items and collecting invalid ones for a
possible targeted retry. Runs once after first extraction and once more
after the repair retry (over the merged remainder), never regenerating
items already accepted as valid.
"""

from typing import Any

from agent.analysis.state import AnalysisState, InvalidItem
from agent.analysis.validation import (
    dedupe_dates,
    dedupe_findings,
    dedupe_risks,
    validate_finding,
    validate_important_date,
    validate_risk,
)


def validate_analysis(state: AnalysisState) -> dict[str, Any]:
    if state.get("status") == "failed":
        return {}

    pages = dict(state["pages"])
    valid_findings = list(state.get("valid_findings", []))
    valid_dates = list(state.get("valid_dates", []))
    valid_risks = list(state.get("valid_risks", []))
    invalid_items: list[InvalidItem] = []

    for finding in dedupe_findings(state.get("pending_findings", [])):
        result = validate_finding(finding, pages)
        if result.valid:
            valid_findings.append(finding)
        else:
            invalid_items.append(
                InvalidItem(
                    kind="finding",
                    description=f"finding {finding.title!r} citing page {finding.source_page}",
                    error=result.error or "invalid",
                )
            )

    for date in dedupe_dates(state.get("pending_dates", [])):
        result = validate_important_date(date, pages)
        if result.valid:
            valid_dates.append(date)
        else:
            invalid_items.append(
                InvalidItem(
                    kind="date",
                    description=f"date {date.label!r} citing page {date.source_page}",
                    error=result.error or "invalid",
                )
            )

    for risk in dedupe_risks(state.get("pending_risks", [])):
        result = validate_risk(risk, pages)
        if result.valid:
            valid_risks.append(risk)
        else:
            invalid_items.append(
                InvalidItem(
                    kind="risk",
                    description=f"risk {risk.title!r}",
                    error=result.error or "invalid",
                )
            )

    return {
        "valid_findings": valid_findings,
        "valid_dates": valid_dates,
        "valid_risks": valid_risks,
        "invalid_items": invalid_items,
    }


def route_after_validation(state: AnalysisState) -> str:
    if state.get("status") == "failed":
        return "fail"
    if not state.get("invalid_items"):
        return "persist"
    if state.get("retry_count", 0) < 1:
        return "retry"
    return "fail"


def route_after_precondition(state: AnalysisState) -> str:
    return "fail" if state.get("status") == "failed" else "continue"
