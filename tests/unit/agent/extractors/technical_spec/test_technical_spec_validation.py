"""Deterministic validation tests: page/quote pairs, identifier-in-evidence,
modality/priority agreement, constraint mandate-language rejection, and
category precedence resolution."""

from agent.extractors.technical_spec.types import (
    ConstraintCandidate,
    DependencyCandidate,
    RequirementCandidate,
)
from agent.extractors.technical_spec.validation import (
    dedupe_constraints,
    dedupe_dependencies,
    dedupe_requirements,
    resolve_category_precedence,
    validate_constraint,
    validate_dependency,
    validate_requirement,
)

PAGE_8 = "FR-12: The service shall allow administrators to revoke active sessions."
PAGE_3 = "Response time shall not exceed 200ms for 95% of requests."
PAGE_9 = "Customers may optionally enable dark mode in their preferences."
PAGES = {8: PAGE_8, 3: PAGE_3, 9: PAGE_9}


def test_validate_requirement_accepts_exact_quote_on_correct_page() -> None:
    requirement = RequirementCandidate(
        category="functional",
        identifier="FR-12",
        statement="Revoke active sessions",
        priority="must",
        source_page=8,
        evidence="FR-12: The service shall allow administrators to revoke active sessions.",
        confidence=0.98,
    )
    assert validate_requirement(requirement, PAGES).valid


def test_validate_requirement_rejects_wrong_page() -> None:
    requirement = RequirementCandidate(
        category="functional",
        statement="Revoke active sessions",
        source_page=3,
        evidence="FR-12: The service shall allow administrators to revoke active sessions.",
        confidence=0.9,
    )
    result = validate_requirement(requirement, PAGES)
    assert not result.valid
    assert "does not appear" in (result.error or "")


def test_validate_requirement_rejects_identifier_not_in_evidence() -> None:
    requirement = RequirementCandidate(
        category="functional",
        identifier="FR-99",
        statement="Revoke active sessions",
        source_page=8,
        evidence="FR-12: The service shall allow administrators to revoke active sessions.",
        confidence=0.9,
    )
    result = validate_requirement(requirement, PAGES)
    assert not result.valid
    assert "identifier" in (result.error or "")


def test_validate_requirement_rejects_must_priority_without_binding_language() -> None:
    requirement = RequirementCandidate(
        category="functional",
        statement="Dark mode preference",
        priority="must",
        source_page=9,
        evidence="Customers may optionally enable dark mode in their preferences.",
        confidence=0.5,
    )
    result = validate_requirement(requirement, PAGES)
    assert not result.valid
    assert "priority" in (result.error or "")


def test_validate_requirement_accepts_may_priority_with_permissive_language() -> None:
    requirement = RequirementCandidate(
        category="functional",
        statement="Dark mode preference",
        priority="may",
        source_page=9,
        evidence="Customers may optionally enable dark mode in their preferences.",
        confidence=0.7,
    )
    assert validate_requirement(requirement, PAGES).valid


def test_validate_requirement_unspecified_priority_skips_modality_check() -> None:
    requirement = RequirementCandidate(
        category="functional",
        statement="Dark mode preference",
        priority="unspecified",
        source_page=9,
        evidence="Customers may optionally enable dark mode in their preferences.",
        confidence=0.5,
    )
    assert validate_requirement(requirement, PAGES).valid


def test_validate_constraint_accepts_mandating_language() -> None:
    constraint = ConstraintCandidate(
        category="performance",
        statement="Response time limit",
        source_page=3,
        evidence="Response time shall not exceed 200ms for 95% of requests.",
        confidence=0.8,
    )
    assert validate_constraint(constraint, PAGES).valid


def test_validate_constraint_rejects_descriptive_mention() -> None:
    constraint = ConstraintCandidate(
        category="technology",
        statement="Dark mode availability",
        source_page=9,
        evidence="Customers may optionally enable dark mode in their preferences.",
        confidence=0.5,
    )
    result = validate_constraint(constraint, PAGES)
    assert not result.valid
    assert "mandate" in (result.error or "")


def test_validate_dependency_checks_quote_on_page() -> None:
    dependency = DependencyCandidate(
        name="Payment Gateway",
        description="d",
        source_page=8,
        evidence="not present anywhere",
        confidence=0.5,
    )
    assert not validate_dependency(dependency, PAGES).valid


def test_resolve_category_precedence_keeps_highest_precedence_category() -> None:
    security_version = RequirementCandidate(
        category="security",
        statement="Encrypt data",
        source_page=8,
        evidence="FR-12: The service shall allow administrators to revoke active sessions.",
        confidence=0.9,
    )
    functional_version = RequirementCandidate(
        category="functional",
        statement="Revoke sessions",
        source_page=8,
        evidence="FR-12: The service shall allow administrators to revoke active sessions.",
        confidence=0.5,
    )
    resolved = resolve_category_precedence([functional_version, security_version])
    assert len(resolved) == 1
    assert resolved[0].category == "security"


def test_resolve_category_precedence_preserves_distinct_statements() -> None:
    first = RequirementCandidate(
        category="functional",
        statement="a",
        source_page=8,
        evidence="FR-12: The service shall allow administrators to revoke active sessions.",
        confidence=0.9,
    )
    second = RequirementCandidate(
        category="non_functional",
        statement="b",
        source_page=3,
        evidence="Response time shall not exceed 200ms for 95% of requests.",
        confidence=0.9,
    )
    resolved = resolve_category_precedence([first, second])
    assert len(resolved) == 2


def test_dedupe_requirements_removes_exact_duplicates_within_category() -> None:
    requirement = RequirementCandidate(
        category="functional",
        statement="a",
        source_page=8,
        evidence="FR-12: The service shall allow administrators to revoke active sessions.",
        confidence=0.9,
    )
    duplicate = RequirementCandidate(
        category="functional",
        statement="a2",
        source_page=8,
        evidence="FR-12: The service shall allow administrators to revoke active sessions.",
        confidence=0.5,
    )
    assert dedupe_requirements([requirement, duplicate]) == [requirement]


def test_dedupe_constraints_removes_exact_duplicates() -> None:
    constraint = ConstraintCandidate(
        category="performance",
        statement="a",
        source_page=3,
        evidence=PAGE_3,
        confidence=0.9,
    )
    duplicate = ConstraintCandidate(
        category="performance",
        statement="a2",
        source_page=3,
        evidence=PAGE_3,
        confidence=0.1,
    )
    assert dedupe_constraints([constraint, duplicate]) == [constraint]


def test_dedupe_dependencies_removes_exact_duplicates() -> None:
    dependency = DependencyCandidate(
        name="n", description="d", source_page=8, evidence=PAGE_8, confidence=0.9
    )
    duplicate = DependencyCandidate(
        name="n2", description="d2", source_page=8, evidence=PAGE_8, confidence=0.1
    )
    assert dedupe_dependencies([dependency, duplicate]) == [dependency]
