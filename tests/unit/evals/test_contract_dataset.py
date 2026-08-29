"""Dataset fixture checks, and running real validation logic (not a stored
mock) over fixture predictions to exercise the invalid-page, obligation
language, and clause-category scenarios end to end."""

import json
from pathlib import Path

from agent.classification.taxonomy import ALLOWED_DOCUMENT_TYPES
from agent.extractors.contract.types import (
    ClauseCandidate,
    ObligationCandidate,
    PartyCandidate,
)
from agent.extractors.contract.validation import (
    dedupe_clauses,
    validate_clause,
    validate_obligation,
    validate_party,
)

DATASET_PATH = (
    Path(__file__).resolve().parents[3] / "evals" / "datasets" / "contract_v1.json"
)


def _load_samples() -> list[dict]:
    return json.loads(DATASET_PATH.read_text())["samples"]


def test_dataset_covers_all_required_scenarios() -> None:
    samples = {sample["sample_id"] for sample in _load_samples()}
    required = {
        "contract-parties-001",
        "contract-obligations-conditional-001",
        "contract-payment-amount-001",
        "contract-no-amount-001",
        "contract-renewal-termination-001",
        "contract-liability-confidentiality-001",
        "contract-expected-empty-001",
        "contract-permissive-recital-001",
        "contract-invalid-page-001",
        "contract-duplicate-clauses-001",
        "contract-prompt-injection-001",
        "generic-routing-001",
        "technical-spec-routing-001",
        "contract-specialized-invalid-generic-valid-001",
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


def test_expected_parties_validate_against_their_own_pages() -> None:
    for sample in _load_samples():
        pages = _pages_for(sample)
        for expected in sample["expected_parties"]:
            party = PartyCandidate(
                name="n",
                source_page=expected["source_page"],
                evidence=expected["evidence_contains"],
                confidence=0.7,
            )
            result = validate_party(party, pages)
            assert result.valid, f"{sample['sample_id']}: {result.error}"


def test_expected_obligations_validate_against_their_own_pages() -> None:
    for sample in _load_samples():
        pages = _pages_for(sample)
        for expected in sample["expected_obligations"]:
            obligation = ObligationCandidate(
                description="d",
                source_page=expected["source_page"],
                evidence=expected["evidence_contains"],
                confidence=0.7,
            )
            result = validate_obligation(obligation, pages)
            assert result.valid, f"{sample['sample_id']}: {result.error}"


def test_invalid_page_sample_is_rejected() -> None:
    sample = next(
        s for s in _load_samples() if s["sample_id"] == "contract-invalid-page-001"
    )
    pages = _pages_for(sample)
    bad_obligation = ObligationCandidate(
        description="d",
        source_page=2,  # sample only has page 1
        evidence="Provider shall maintain the confidentiality of Customer data",
        confidence=0.5,
    )
    result = validate_obligation(bad_obligation, pages)
    assert result.valid is False


def test_permissive_recital_sample_is_not_a_valid_obligation() -> None:
    """Proves the mandatory-language check rejects permissive/recital text
    even when it appears verbatim on the cited page."""
    sample = next(
        s
        for s in _load_samples()
        if s["sample_id"] == "contract-permissive-recital-001"
    )
    pages = _pages_for(sample)
    permissive_obligation = ObligationCandidate(
        description="d",
        source_page=3,
        evidence="Customer may request additional support services at its sole discretion",
        confidence=0.5,
    )
    result = validate_obligation(permissive_obligation, pages)
    assert result.valid is False
    assert sample["non_mandatory_text_present"] is True


def test_duplicate_clauses_sample_dedupes_to_one_clause() -> None:
    sample = next(
        s for s in _load_samples() if s["sample_id"] == "contract-duplicate-clauses-001"
    )
    expected = sample["expected_clauses"][0]
    clause = ClauseCandidate(
        category="renewal",
        title="t",
        description="d",
        source_page=expected["source_page"],
        evidence=expected["evidence_contains"],
        confidence=0.7,
    )
    duplicated = [clause, clause.model_copy()]

    assert len(dedupe_clauses(duplicated)) == 1


def test_renewal_and_termination_clauses_validate_against_category_language() -> None:
    sample = next(
        s
        for s in _load_samples()
        if s["sample_id"] == "contract-renewal-termination-001"
    )
    pages = _pages_for(sample)
    renewal_expected, termination_expected = sample["expected_clauses"]

    renewal = ClauseCandidate(
        category="renewal",
        title="t",
        description="d",
        source_page=renewal_expected["source_page"],
        evidence=renewal_expected["evidence_contains"],
        confidence=0.7,
    )
    termination = ClauseCandidate(
        category="termination",
        title="t",
        description="d",
        source_page=termination_expected["source_page"],
        evidence=termination_expected["evidence_contains"],
        confidence=0.7,
    )
    assert validate_clause(renewal, pages).valid
    assert validate_clause(termination, pages).valid


def test_prompt_injection_sample_expected_items_ignore_injected_instructions() -> None:
    sample = next(
        s for s in _load_samples() if s["sample_id"] == "contract-prompt-injection-001"
    )
    assert "Ignore all previous instructions" in sample["pages"]["1"]
    for expected in sample["expected_obligations"]:
        assert "system prompt" not in expected["evidence_contains"]


def test_expected_empty_sample_has_no_expected_items_in_any_category() -> None:
    sample = next(
        s for s in _load_samples() if s["sample_id"] == "contract-expected-empty-001"
    )
    assert sample["expected_parties"] == []
    assert sample["expected_obligations"] == []
    assert sample["expected_payment_terms"] == []
    assert sample["expected_clauses"] == []
