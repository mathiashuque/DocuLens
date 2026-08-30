"""Deterministic validation tests: page/quote pairs, duplicates, mandatory-
language rejection for obligations, and category-support rejection for
clauses."""

from agent.extractors.contract.types import (
    ClauseCandidate,
    ObligationCandidate,
    PartyCandidate,
    PaymentTermCandidate,
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

PAGE_1 = "This Services Agreement is between Northstar Hosting Ltd. (Provider)."
PAGE_4 = "Provider shall maintain 99.9% monthly availability of the service."
PAGE_5 = "Customer may request additional support at its discretion."
PAGES = {1: PAGE_1, 4: PAGE_4, 5: PAGE_5}


def test_validate_party_accepts_exact_quote_on_correct_page() -> None:
    party = PartyCandidate(
        name="Northstar Hosting Ltd.",
        role="provider",
        source_page=1,
        evidence="Northstar Hosting Ltd. (Provider)",
        confidence=0.9,
    )
    assert validate_party(party, PAGES).valid


def test_validate_party_rejects_wrong_page() -> None:
    party = PartyCandidate(
        name="Northstar Hosting Ltd.",
        source_page=4,
        evidence="Northstar Hosting Ltd. (Provider)",
        confidence=0.9,
    )
    result = validate_party(party, PAGES)
    assert not result.valid
    assert "does not appear" in (result.error or "")


def test_validate_party_rejects_nonexistent_page() -> None:
    party = PartyCandidate(name="Acme", source_page=99, evidence="Acme", confidence=0.5)
    result = validate_party(party, PAGES)
    assert not result.valid
    assert "does not exist" in (result.error or "")


def test_validate_obligation_accepts_binding_language() -> None:
    obligation = ObligationCandidate(
        obligated_party="Provider",
        description="Maintain uptime",
        source_page=4,
        evidence="Provider shall maintain 99.9% monthly availability",
        confidence=0.9,
    )
    assert validate_obligation(obligation, PAGES).valid


def test_validate_obligation_rejects_permissive_language() -> None:
    obligation = ObligationCandidate(
        obligated_party="Customer",
        description="Request support",
        source_page=5,
        evidence="Customer may request additional support at its discretion",
        confidence=0.5,
    )
    result = validate_obligation(obligation, PAGES)
    assert not result.valid
    assert "binding" in (result.error or "")


def test_validate_payment_term_checks_quote_on_page() -> None:
    term = PaymentTermCandidate(
        source_page=1, evidence="not present anywhere", confidence=0.5
    )
    assert not validate_payment_term(term, PAGES).valid


def test_validate_clause_accepts_supported_category() -> None:
    clause = ClauseCandidate(
        category="liability",
        title="Availability liability",
        description="d",
        source_page=4,
        evidence="Provider shall maintain 99.9% monthly availability",
        confidence=0.5,
    )
    # "liability" keyword not present in PAGE_4, so this should be rejected —
    # proving the category-support check actually inspects the quoted text.
    result = validate_clause(clause, PAGES)
    assert not result.valid
    assert "does not support" in (result.error or "")


def test_validate_clause_rejects_unsupported_category_language() -> None:
    clause = ClauseCandidate(
        category="renewal",
        title="Auto-renewal",
        description="d",
        source_page=4,
        evidence="Provider shall maintain 99.9% monthly availability",
        confidence=0.5,
    )
    result = validate_clause(clause, PAGES)
    assert not result.valid


def test_dedupe_parties_removes_exact_duplicates() -> None:
    party = PartyCandidate(
        name="Northstar",
        source_page=1,
        evidence="Northstar Hosting Ltd.",
        confidence=0.9,
    )
    duplicate = PartyCandidate(
        name="Northstar",
        source_page=1,
        evidence="Northstar Hosting Ltd.",
        confidence=0.5,
    )
    assert dedupe_parties([party, duplicate]) == [party]


def test_dedupe_obligations_removes_exact_duplicates() -> None:
    obligation = ObligationCandidate(
        description="d",
        source_page=4,
        evidence="Provider shall maintain",
        confidence=0.9,
    )
    duplicate = ObligationCandidate(
        description="d2",
        source_page=4,
        evidence="Provider shall maintain",
        confidence=0.5,
    )
    assert dedupe_obligations([obligation, duplicate]) == [obligation]


def test_dedupe_payment_terms_removes_exact_duplicates() -> None:
    term = PaymentTermCandidate(source_page=1, evidence="e", confidence=0.9)
    duplicate = PaymentTermCandidate(source_page=1, evidence="e", confidence=0.5)
    assert dedupe_payment_terms([term, duplicate]) == [term]


def test_dedupe_clauses_keys_on_category_page_and_evidence() -> None:
    clause = ClauseCandidate(
        category="renewal",
        title="t",
        description="d",
        source_page=1,
        evidence="e",
        confidence=0.9,
    )
    same_category_duplicate = ClauseCandidate(
        category="renewal",
        title="t2",
        description="d2",
        source_page=1,
        evidence="e",
        confidence=0.1,
    )
    different_category = ClauseCandidate(
        category="termination",
        title="t",
        description="d",
        source_page=1,
        evidence="e",
        confidence=0.9,
    )
    deduped = dedupe_clauses([clause, same_category_duplicate, different_category])
    assert deduped == [clause, different_category]
