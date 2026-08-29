"""Typed schema unit tests for the technical-specification extractor:
bounds, enums, nullable/raw values, and empty-list validity."""

import pytest
from pydantic import ValidationError

from agent.extractors.technical_spec.types import (
    ConstraintCandidate,
    DependencyCandidate,
    RequirementCandidate,
    TechnicalSpecExtractionCandidate,
)


def test_requirement_defaults_priority_to_unspecified() -> None:
    requirement = RequirementCandidate(
        category="functional",
        statement="The service shall allow session revocation.",
        source_page=8,
        evidence="FR-12: The service shall allow session revocation.",
        confidence=0.9,
    )
    assert requirement.priority == "unspecified"
    assert requirement.identifier is None


def test_requirement_requires_valid_category() -> None:
    with pytest.raises(ValidationError):
        RequirementCandidate(
            category="usability",  # type: ignore[arg-type]
            statement="s",
            source_page=1,
            evidence="e",
            confidence=0.5,
        )


def test_requirement_requires_valid_priority() -> None:
    with pytest.raises(ValidationError):
        RequirementCandidate(
            category="functional",
            statement="s",
            priority="mandatory",  # type: ignore[arg-type]
            source_page=1,
            evidence="e",
            confidence=0.5,
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.1, float("nan"), float("inf")])
def test_requirement_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        RequirementCandidate(
            category="functional",
            statement="s",
            source_page=1,
            evidence="e",
            confidence=confidence,
        )


def test_requirement_rejects_non_positive_source_page() -> None:
    with pytest.raises(ValidationError):
        RequirementCandidate(
            category="functional",
            statement="s",
            source_page=0,
            evidence="e",
            confidence=0.5,
        )


def test_requirement_allows_explicit_identifier_and_criterion() -> None:
    requirement = RequirementCandidate(
        category="non_functional",
        identifier="NFR-3",
        statement="99.9% monthly availability",
        priority="must",
        actor="Provider",
        measurable_criterion="99.9% monthly",
        source_page=8,
        evidence="NFR-3: Provider shall maintain 99.9% monthly availability",
        confidence=0.9,
    )
    assert requirement.identifier == "NFR-3"
    assert requirement.measurable_criterion == "99.9% monthly"


def test_constraint_requires_valid_category() -> None:
    with pytest.raises(ValidationError):
        ConstraintCandidate(
            category="licensing",  # type: ignore[arg-type]
            statement="s",
            source_page=1,
            evidence="e",
            confidence=0.5,
        )


def test_constraint_preserves_raw_value_text() -> None:
    constraint = ConstraintCandidate(
        category="performance",
        statement="Response time limit",
        value_text="under 200ms p95",
        source_page=3,
        evidence="Response time shall not exceed 200ms p95",
        confidence=0.8,
    )
    assert constraint.value_text == "under 200ms p95"


def test_dependency_allows_null_type() -> None:
    dependency = DependencyCandidate(
        name="Payment Gateway API",
        description="Integrates with the external payment gateway",
        source_page=5,
        evidence="The system depends on the Payment Gateway API for billing",
        confidence=0.7,
    )
    assert dependency.dependency_type is None


def test_extraction_candidate_allows_all_empty_categories() -> None:
    candidate = TechnicalSpecExtractionCandidate(
        requirements=[], constraints=[], dependencies=[]
    )
    assert candidate.requirements == []
    assert candidate.constraints == []
    assert candidate.dependencies == []
