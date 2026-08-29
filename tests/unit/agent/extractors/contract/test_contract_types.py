"""Typed schema unit tests for the contract extractor: bounds, enums,
nullable/raw values, and empty-list validity."""

import pytest
from pydantic import ValidationError

from agent.extractors.contract.types import (
    ClauseCandidate,
    ContractExtractionCandidate,
    ObligationCandidate,
    PartyCandidate,
    PaymentTermCandidate,
)


def test_party_allows_null_role() -> None:
    party = PartyCandidate(
        name="Northstar Hosting Ltd.",
        role=None,
        source_page=1,
        evidence="Northstar Hosting Ltd. (Provider)",
        confidence=0.9,
    )
    assert party.role is None


def test_party_rejects_non_positive_source_page() -> None:
    with pytest.raises(ValidationError):
        PartyCandidate(name="Acme", source_page=0, evidence="Acme", confidence=0.5)


@pytest.mark.parametrize("confidence", [-0.1, 1.1, float("nan"), float("inf")])
def test_party_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        PartyCandidate(
            name="Acme", source_page=1, evidence="Acme", confidence=confidence
        )


def test_obligation_allows_null_party_and_beneficiary() -> None:
    obligation = ObligationCandidate(
        obligated_party=None,
        description="Maintain records",
        beneficiary=None,
        source_page=2,
        evidence="Records shall be maintained",
        confidence=0.6,
    )
    assert obligation.obligated_party is None
    assert obligation.beneficiary is None
    assert obligation.conditions == []


def test_obligation_strips_blank_conditions() -> None:
    obligation = ObligationCandidate(
        description="d",
        source_page=1,
        evidence="e",
        confidence=0.5,
        conditions=["  ", "upon notice", ""],
    )
    assert obligation.conditions == ["upon notice"]


def test_payment_term_preserves_raw_amount_text() -> None:
    term = PaymentTermCandidate(
        payer="Customer",
        payee="Provider",
        amount_text="$1,000 USD/month",
        schedule_text="due on the 1st of each month",
        source_page=4,
        evidence="Customer shall pay Provider $1,000 USD/month",
        confidence=0.85,
    )
    assert term.amount_text == "$1,000 USD/month"


def test_payment_term_allows_all_optional_fields_null() -> None:
    term = PaymentTermCandidate(
        source_page=1, evidence="no explicit amount stated", confidence=0.3
    )
    assert term.payer is None
    assert term.amount_text is None


def test_clause_requires_allowed_category() -> None:
    with pytest.raises(ValidationError):
        ClauseCandidate(
            category="warranty",  # type: ignore[arg-type]
            title="t",
            description="d",
            source_page=1,
            evidence="e",
            confidence=0.5,
        )


@pytest.mark.parametrize(
    "category", ["renewal", "termination", "liability", "confidentiality"]
)
def test_clause_accepts_each_allowed_category(category: str) -> None:
    clause = ClauseCandidate(
        category=category,  # type: ignore[arg-type]
        title="t",
        description="d",
        source_page=1,
        evidence="e",
        confidence=0.5,
    )
    assert clause.category == category


def test_contract_extraction_candidate_allows_all_empty_categories() -> None:
    candidate = ContractExtractionCandidate(
        parties=[], obligations=[], payment_terms=[], clauses=[]
    )
    assert candidate.parties == []
    assert candidate.obligations == []
    assert candidate.payment_terms == []
    assert candidate.clauses == []
