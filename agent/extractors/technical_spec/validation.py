"""Pure, deterministic validation of technical-specification extraction
candidate items.

Mirrors `agent.extractors.contract.validation`'s exact-quote-on-page
checking (reusing `ItemValidationResult` and `normalize_whitespace`) and
adds three lexical, non-legal support checks: a requirement's declared
identifier must actually appear in its own evidence, a requirement's
declared priority must agree with the modality language in its evidence,
and a constraint's evidence must contain mandating/limiting language rather
than a merely descriptive mention. `resolve_category_precedence` is the
deterministic, documented rule that keeps the same underlying statement
from being reported in more than one requirement category.
"""

from agent.analysis.validation import ItemValidationResult
from agent.classification.validation import normalize_whitespace
from agent.extractors.technical_spec.taxonomy import REQUIREMENT_CATEGORY_PRECEDENCE
from agent.extractors.technical_spec.types import (
    ConstraintCandidate,
    DependencyCandidate,
    RequirementCandidate,
)

_MODALITY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "must": ("shall", "must", "is required to", "are required to", "required to"),
    "should": ("should", "recommended", "is advised to"),
    "may": ("may", "optional", "at its discretion", "is permitted to"),
}

_CONSTRAINT_KEYWORDS: tuple[str, ...] = (
    "shall",
    "must",
    "required",
    "limited to",
    "maximum",
    "minimum",
    "at least",
    "no more than",
    "shall not exceed",
    "only support",
    "compatible with",
    "must run",
    "must use",
)


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


def validate_requirement(
    requirement: RequirementCandidate, pages: dict[int, str]
) -> ItemValidationResult:
    error = _quote_on_page(requirement.evidence, requirement.source_page, pages)
    if error:
        return ItemValidationResult(valid=False, error=error)

    if (
        requirement.identifier is not None
        and requirement.identifier.lower() not in requirement.evidence.lower()
    ):
        return ItemValidationResult(
            valid=False,
            error="declared identifier does not appear in its own evidence",
        )

    keywords = _MODALITY_KEYWORDS.get(requirement.priority)
    if keywords is not None:
        lowered = requirement.evidence.lower()
        if not any(keyword in lowered for keyword in keywords):
            return ItemValidationResult(
                valid=False,
                error=f"evidence does not support {requirement.priority!r} priority",
            )

    return ItemValidationResult(valid=True)


def validate_constraint(
    constraint: ConstraintCandidate, pages: dict[int, str]
) -> ItemValidationResult:
    error = _quote_on_page(constraint.evidence, constraint.source_page, pages)
    if error:
        return ItemValidationResult(valid=False, error=error)
    lowered = constraint.evidence.lower()
    if not any(keyword in lowered for keyword in _CONSTRAINT_KEYWORDS):
        return ItemValidationResult(
            valid=False,
            error="evidence does not mandate or limit a choice",
        )
    return ItemValidationResult(valid=True)


def validate_dependency(
    dependency: DependencyCandidate, pages: dict[int, str]
) -> ItemValidationResult:
    error = _quote_on_page(dependency.evidence, dependency.source_page, pages)
    if error:
        return ItemValidationResult(valid=False, error=error)
    return ItemValidationResult(valid=True)


def resolve_category_precedence(
    requirements: list[RequirementCandidate],
) -> list[RequirementCandidate]:
    """When the same underlying statement (same page + evidence, regardless
    of category) is reported more than once, keep only the occurrence in the
    highest-precedence category (security, then integration, then
    non_functional, then functional) and drop the rest — the documented,
    deterministic rule preventing duplicate cross-category requirements."""
    best_by_key: dict[tuple[int, str], RequirementCandidate] = {}
    order: list[tuple[int, str]] = []
    for requirement in requirements:
        key = (requirement.source_page, normalize_whitespace(requirement.evidence))
        if key not in best_by_key:
            best_by_key[key] = requirement
            order.append(key)
            continue
        current = best_by_key[key]
        if REQUIREMENT_CATEGORY_PRECEDENCE.index(
            requirement.category
        ) < REQUIREMENT_CATEGORY_PRECEDENCE.index(current.category):
            best_by_key[key] = requirement
    return [best_by_key[key] for key in order]


def dedupe_requirements(
    requirements: list[RequirementCandidate],
) -> list[RequirementCandidate]:
    seen: set[tuple[str, int, str]] = set()
    deduped: list[RequirementCandidate] = []
    for requirement in requirements:
        key = (
            requirement.category,
            requirement.source_page,
            normalize_whitespace(requirement.evidence),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(requirement)
    return deduped


def dedupe_constraints(
    constraints: list[ConstraintCandidate],
) -> list[ConstraintCandidate]:
    seen: set[tuple[int, str]] = set()
    deduped: list[ConstraintCandidate] = []
    for constraint in constraints:
        key = (constraint.source_page, normalize_whitespace(constraint.evidence))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(constraint)
    return deduped


def dedupe_dependencies(
    dependencies: list[DependencyCandidate],
) -> list[DependencyCandidate]:
    seen: set[tuple[int, str]] = set()
    deduped: list[DependencyCandidate] = []
    for dependency in dependencies:
        key = (dependency.source_page, normalize_whitespace(dependency.evidence))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(dependency)
    return deduped
