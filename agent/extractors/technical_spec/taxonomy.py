"""Extractor identity and bounded vocabularies for the technical-
specification extractor.

`TECHNICAL_SPEC_EXTRACTOR` is what the API and persistence layers record as
`extractor` when a document's validated classification is
`technical_specification`.
"""

from typing import Final, Literal, get_args

TECHNICAL_SPEC_EXTRACTOR: Final[str] = "technical_specification_requirements"

RequirementCategory = Literal["functional", "non_functional", "security", "integration"]
ALLOWED_REQUIREMENT_CATEGORIES: Final[tuple[RequirementCategory, ...]] = get_args(
    RequirementCategory
)

# Deterministic category precedence for resolving the same underlying
# statement being reported under more than one category: lower index wins.
REQUIREMENT_CATEGORY_PRECEDENCE: Final[tuple[RequirementCategory, ...]] = (
    "security",
    "integration",
    "non_functional",
    "functional",
)

Priority = Literal["must", "should", "may", "unspecified"]
ALLOWED_PRIORITIES: Final[tuple[Priority, ...]] = get_args(Priority)

ConstraintCategory = Literal["technology", "performance", "deployment", "compatibility"]
ALLOWED_CONSTRAINT_CATEGORIES: Final[tuple[ConstraintCategory, ...]] = get_args(
    ConstraintCategory
)
