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
from agent.extractors.contract.validation import (
    dedupe_clauses,
    dedupe_obligations,
    dedupe_parties,
    dedupe_payment_terms,
    validate_clause,
    validate_obligation,
    validate_party,
    validate_payment_term,
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

    valid_parties = list(state.get("valid_parties", []))
    valid_obligations = list(state.get("valid_obligations", []))
    valid_payment_terms = list(state.get("valid_payment_terms", []))
    valid_clauses = list(state.get("valid_clauses", []))

    for party in dedupe_parties(state.get("pending_parties", [])):
        result = validate_party(party, pages)
        if result.valid:
            valid_parties.append(party)
        else:
            invalid_items.append(
                InvalidItem(
                    kind="party",
                    description=f"party {party.name!r} citing page {party.source_page}",
                    error=result.error or "invalid",
                )
            )

    for obligation in dedupe_obligations(state.get("pending_obligations", [])):
        result = validate_obligation(obligation, pages)
        if result.valid:
            valid_obligations.append(obligation)
        else:
            invalid_items.append(
                InvalidItem(
                    kind="obligation",
                    description=(
                        f"obligation on page {obligation.source_page}: "
                        f"{obligation.description}"
                    ),
                    error=result.error or "invalid",
                )
            )

    for term in dedupe_payment_terms(state.get("pending_payment_terms", [])):
        result = validate_payment_term(term, pages)
        if result.valid:
            valid_payment_terms.append(term)
        else:
            invalid_items.append(
                InvalidItem(
                    kind="payment_term",
                    description=f"payment term citing page {term.source_page}",
                    error=result.error or "invalid",
                )
            )

    for clause in dedupe_clauses(state.get("pending_clauses", [])):
        result = validate_clause(clause, pages)
        if result.valid:
            valid_clauses.append(clause)
        else:
            invalid_items.append(
                InvalidItem(
                    kind="clause",
                    description=(
                        f"{clause.category} clause {clause.title!r} citing page "
                        f"{clause.source_page}"
                    ),
                    error=result.error or "invalid",
                )
            )

    return {
        "valid_findings": valid_findings,
        "valid_dates": valid_dates,
        "valid_risks": valid_risks,
        "valid_parties": valid_parties,
        "valid_obligations": valid_obligations,
        "valid_payment_terms": valid_payment_terms,
        "valid_clauses": valid_clauses,
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
