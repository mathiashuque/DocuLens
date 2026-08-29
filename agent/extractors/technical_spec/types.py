"""Typed structured-output contract produced by the technical-specification
extractor provider, before deterministic validation and ID assignment.
"""

import math

from pydantic import BaseModel, Field, field_validator

from agent.extractors.technical_spec.taxonomy import (
    ConstraintCategory,
    Priority,
    RequirementCategory,
)

MAX_REQUIREMENTS = 40
MAX_CONSTRAINTS = 20
MAX_DEPENDENCIES = 20


def _finite_unit_interval(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("confidence must be a finite number")
    if not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be within [0, 1]")
    return value


class RequirementCandidate(BaseModel):
    """One shared evidence-bearing requirement, tagged with the single
    category collection it belongs to (functional/non_functional/security/
    integration) — see `taxonomy.REQUIREMENT_CATEGORY_PRECEDENCE` for how
    cross-category duplicates of the same statement are resolved."""

    category: RequirementCategory
    identifier: str | None = Field(default=None, max_length=50)
    statement: str = Field(min_length=1, max_length=1000)
    priority: Priority = "unspecified"
    actor: str | None = Field(default=None, max_length=200)
    measurable_criterion: str | None = Field(default=None, max_length=200)
    source_page: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=1000)
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: float) -> float:
        return _finite_unit_interval(value)


class ConstraintCandidate(BaseModel):
    category: ConstraintCategory
    statement: str = Field(min_length=1, max_length=1000)
    value_text: str | None = Field(default=None, max_length=200)
    source_page: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=1000)
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: float) -> float:
        return _finite_unit_interval(value)


class DependencyCandidate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dependency_type: str | None = Field(default=None, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    source_page: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=1000)
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: float) -> float:
        return _finite_unit_interval(value)


class TechnicalSpecExtractionCandidate(BaseModel):
    """The full structured result requested from the technical-specification
    provider on first pass. Empty lists are valid: absence, not
    fabrication."""

    requirements: list[RequirementCandidate] = Field(
        default_factory=list, max_length=MAX_REQUIREMENTS
    )
    constraints: list[ConstraintCandidate] = Field(
        default_factory=list, max_length=MAX_CONSTRAINTS
    )
    dependencies: list[DependencyCandidate] = Field(
        default_factory=list, max_length=MAX_DEPENDENCIES
    )


class TechnicalSpecRepairCandidate(BaseModel):
    """Corrected replacements for only the invalid technical items from a
    prior pass. Items may be fewer than requested, including zero, when the
    provider correctly omits an unsupported claim instead of fabricating a
    fix."""

    requirements: list[RequirementCandidate] = Field(
        default_factory=list, max_length=MAX_REQUIREMENTS
    )
    constraints: list[ConstraintCandidate] = Field(
        default_factory=list, max_length=MAX_CONSTRAINTS
    )
    dependencies: list[DependencyCandidate] = Field(
        default_factory=list, max_length=MAX_DEPENDENCIES
    )
