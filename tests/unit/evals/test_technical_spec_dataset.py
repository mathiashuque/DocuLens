"""Dataset fixture checks, and running real validation logic (not a stored
mock) over fixture predictions to exercise the invalid-page, modality, and
category-precedence scenarios end to end."""

import json
from pathlib import Path

from agent.classification.taxonomy import ALLOWED_DOCUMENT_TYPES
from agent.extractors.technical_spec.types import (
    ConstraintCandidate,
    DependencyCandidate,
    RequirementCandidate,
)
from agent.extractors.technical_spec.validation import (
    resolve_category_precedence,
    validate_constraint,
    validate_dependency,
    validate_requirement,
)

DATASET_PATH = (
    Path(__file__).resolve().parents[3]
    / "evals"
    / "datasets"
    / "technical_spec_v1.json"
)


def _load_samples() -> list[dict]:
    return json.loads(DATASET_PATH.read_text())["samples"]


def test_dataset_covers_all_required_scenarios() -> None:
    samples = {sample["sample_id"] for sample in _load_samples()}
    required = {
        "functional-with-id-001",
        "functional-without-id-002",
        "non-functional-measurable-001",
        "security-access-control-001",
        "integration-api-001",
        "modality-should-001",
        "modality-may-ambiguous-001",
        "category-overlap-security-functional-001",
        "descriptive-technology-mention-001",
        "constraint-technology-001",
        "constraint-performance-001",
        "constraint-compatibility-deployment-001",
        "dependency-external-001",
        "expected-empty-001",
        "invalid-page-001",
        "duplicate-requirement-001",
        "prompt-injection-001",
        "contract-routing-001",
        "generic-routing-001",
        "specialized-invalid-generic-valid-001",
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


def test_expected_functional_requirements_validate_against_their_own_pages() -> None:
    for sample in _load_samples():
        pages = _pages_for(sample)
        for expected in sample["expected_functional"]:
            requirement = RequirementCandidate(
                category="functional",
                statement="s",
                source_page=expected["source_page"],
                evidence=expected["evidence_contains"],
                confidence=0.7,
            )
            result = validate_requirement(requirement, pages)
            assert result.valid, f"{sample['sample_id']}: {result.error}"


def test_expected_constraints_validate_against_their_own_pages() -> None:
    for sample in _load_samples():
        pages = _pages_for(sample)
        for expected in sample["expected_constraints"]:
            constraint = ConstraintCandidate(
                category="technology",
                statement="s",
                source_page=expected["source_page"],
                evidence=expected["evidence_contains"],
                confidence=0.7,
            )
            result = validate_constraint(constraint, pages)
            assert result.valid, f"{sample['sample_id']}: {result.error}"


def test_expected_dependencies_validate_against_their_own_pages() -> None:
    for sample in _load_samples():
        pages = _pages_for(sample)
        for expected in sample["expected_dependencies"]:
            dependency = DependencyCandidate(
                name="n",
                description="d",
                source_page=expected["source_page"],
                evidence=expected["evidence_contains"],
                confidence=0.7,
            )
            result = validate_dependency(dependency, pages)
            assert result.valid, f"{sample['sample_id']}: {result.error}"


def test_invalid_page_sample_is_rejected() -> None:
    sample = next(s for s in _load_samples() if s["sample_id"] == "invalid-page-001")
    pages = _pages_for(sample)
    bad_requirement = RequirementCandidate(
        category="functional",
        statement="s",
        source_page=2,  # sample only has page 1
        evidence="FR-1: The system shall support multi-factor authentication.",
        confidence=0.5,
    )
    result = validate_requirement(bad_requirement, pages)
    assert result.valid is False


def test_ambiguous_may_sample_is_not_forced_into_must_priority() -> None:
    """Proves the modality-agreement check rejects a mismatched declared
    priority even when the evidence quote itself is exact."""
    sample = next(
        s for s in _load_samples() if s["sample_id"] == "modality-may-ambiguous-001"
    )
    pages = _pages_for(sample)
    mismatched = RequirementCandidate(
        category="functional",
        statement="s",
        priority="must",
        source_page=9,
        evidence="Customers may optionally enable dark mode in their preferences.",
        confidence=0.5,
    )
    result = validate_requirement(mismatched, pages)
    assert result.valid is False


def test_descriptive_technology_mention_sample_is_not_a_valid_constraint() -> None:
    sample = next(
        s
        for s in _load_samples()
        if s["sample_id"] == "descriptive-technology-mention-001"
    )
    pages = _pages_for(sample)
    descriptive_constraint = ConstraintCandidate(
        category="technology",
        statement="s",
        source_page=1,
        evidence="For context, similar systems in this space are often built on PostgreSQL.",
        confidence=0.5,
    )
    result = validate_constraint(descriptive_constraint, pages)
    assert result.valid is False
    assert sample["descriptive_mention_present"] is True


def test_category_overlap_sample_resolves_to_security_precedence() -> None:
    sample = next(
        s
        for s in _load_samples()
        if s["sample_id"] == "category-overlap-security-functional-001"
    )
    expected = sample["expected_security"][0]
    security_version = RequirementCandidate(
        category="security",
        statement="s",
        source_page=expected["source_page"],
        evidence=expected["evidence_contains"],
        confidence=0.9,
    )
    functional_version = RequirementCandidate(
        category="functional",
        statement="s2",
        source_page=expected["source_page"],
        evidence=expected["evidence_contains"],
        confidence=0.5,
    )
    resolved = resolve_category_precedence([functional_version, security_version])
    assert len(resolved) == 1
    assert resolved[0].category == "security"
    assert sample["category_overlap_present"] is True


def test_expected_empty_sample_has_no_expected_items_in_any_category() -> None:
    sample = next(s for s in _load_samples() if s["sample_id"] == "expected-empty-001")
    assert sample["expected_functional"] == []
    assert sample["expected_non_functional"] == []
    assert sample["expected_security"] == []
    assert sample["expected_integration"] == []
    assert sample["expected_constraints"] == []
    assert sample["expected_dependencies"] == []
