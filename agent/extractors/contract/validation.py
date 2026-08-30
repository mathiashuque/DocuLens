"""Pure, deterministic validation of contract extraction candidate items.

Mirrors `agent.analysis.validation`'s exact-quote-on-page checking (reusing
its `ItemValidationResult` shape and `normalize_whitespace`) and adds two
lexical, non-legal support checks: an obligation must contain plain binding
language, and a clause's evidence must loosely support its claimed category.
Neither check offers a legal conclusion — they only reject items whose own
quoted text contradicts the claim being made about it.
"""

from agent.analysis.validation import ItemValidationResult
from agent.classification.validation import normalize_whitespace
from agent.extractors.contract.types import (
    ClauseCandidate,
    ObligationCandidate,
    PartyCandidate,
    PaymentTermCandidate,
)

_BINDING_KEYWORDS: tuple[str, ...] = (
    "shall",
    "must",
    "is required to",
    "are required to",
    "is obligated",
    "are obligated",
    "agrees to",
    "agree to",
    "undertakes",
    "will maintain",
    "will provide",
    "will pay",
)

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "renewal": ("renew",),
    "termination": ("terminat",),
    "liability": ("liab",),
    "confidentiality": ("confidential",),
}


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


def validate_party(
    party: PartyCandidate, pages: dict[int, str]
) -> ItemValidationResult:
    error = _quote_on_page(party.evidence, party.source_page, pages)
    if error:
        return ItemValidationResult(valid=False, error=error)
    return ItemValidationResult(valid=True)


def validate_obligation(
    obligation: ObligationCandidate, pages: dict[int, str]
) -> ItemValidationResult:
    error = _quote_on_page(obligation.evidence, obligation.source_page, pages)
    if error:
        return ItemValidationResult(valid=False, error=error)
    lowered = obligation.evidence.lower()
    if not any(keyword in lowered for keyword in _BINDING_KEYWORDS):
        return ItemValidationResult(
            valid=False,
            error="evidence does not contain mandatory/binding language",
        )
    return ItemValidationResult(valid=True)


def validate_payment_term(
    term: PaymentTermCandidate, pages: dict[int, str]
) -> ItemValidationResult:
    error = _quote_on_page(term.evidence, term.source_page, pages)
    if error:
        return ItemValidationResult(valid=False, error=error)
    return ItemValidationResult(valid=True)


def validate_clause(
    clause: ClauseCandidate, pages: dict[int, str]
) -> ItemValidationResult:
    error = _quote_on_page(clause.evidence, clause.source_page, pages)
    if error:
        return ItemValidationResult(valid=False, error=error)
    keywords = _CATEGORY_KEYWORDS[clause.category]
    lowered = clause.evidence.lower()
    if not any(keyword in lowered for keyword in keywords):
        return ItemValidationResult(
            valid=False,
            error=f"evidence does not support the {clause.category} category",
        )
    return ItemValidationResult(valid=True)


def dedupe_parties(parties: list[PartyCandidate]) -> list[PartyCandidate]:
    seen: set[tuple[int, str]] = set()
    deduped: list[PartyCandidate] = []
    for party in parties:
        key = (party.source_page, normalize_whitespace(party.evidence))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(party)
    return deduped


def dedupe_obligations(
    obligations: list[ObligationCandidate],
) -> list[ObligationCandidate]:
    seen: set[tuple[int, str]] = set()
    deduped: list[ObligationCandidate] = []
    for obligation in obligations:
        key = (obligation.source_page, normalize_whitespace(obligation.evidence))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(obligation)
    return deduped


def dedupe_payment_terms(
    terms: list[PaymentTermCandidate],
) -> list[PaymentTermCandidate]:
    seen: set[tuple[int, str]] = set()
    deduped: list[PaymentTermCandidate] = []
    for term in terms:
        key = (term.source_page, normalize_whitespace(term.evidence))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(term)
    return deduped


def dedupe_clauses(clauses: list[ClauseCandidate]) -> list[ClauseCandidate]:
    seen: set[tuple[str, int, str]] = set()
    deduped: list[ClauseCandidate] = []
    for clause in clauses:
        key = (
            clause.category,
            clause.source_page,
            normalize_whitespace(clause.evidence),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(clause)
    return deduped
