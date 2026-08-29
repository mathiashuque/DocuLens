"""Final, app-ID-assigned technical-specification extraction result.

IDs are generated here, in application code — never trusted from the
provider. Mirrors `agent.extractors.contract.result`.
"""

import uuid
from dataclasses import dataclass, field

from agent.extractors.technical_spec.provider import ProviderMetadata
from agent.extractors.technical_spec.taxonomy import TECHNICAL_SPEC_EXTRACTOR
from agent.extractors.technical_spec.types import (
    ConstraintCandidate,
    DependencyCandidate,
    RequirementCandidate,
)


@dataclass(frozen=True)
class RequirementResult:
    id: uuid.UUID
    category: str
    identifier: str | None
    statement: str
    priority: str
    actor: str | None
    measurable_criterion: str | None
    source_page: int
    evidence: str
    confidence: float


@dataclass(frozen=True)
class ConstraintResult:
    id: uuid.UUID
    category: str
    statement: str
    value_text: str | None
    source_page: int
    evidence: str
    confidence: float


@dataclass(frozen=True)
class DependencyResult:
    id: uuid.UUID
    name: str
    dependency_type: str | None
    description: str
    source_page: int
    evidence: str
    confidence: float


@dataclass(frozen=True)
class TechnicalSpecAnalysisResult:
    extractor: str = TECHNICAL_SPEC_EXTRACTOR
    requirements: tuple[RequirementResult, ...] = field(default_factory=tuple)
    constraints: tuple[ConstraintResult, ...] = field(default_factory=tuple)
    dependencies: tuple[DependencyResult, ...] = field(default_factory=tuple)
    provider: str = ""
    model: str = ""
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    @property
    def functional_requirements(self) -> tuple[RequirementResult, ...]:
        return tuple(r for r in self.requirements if r.category == "functional")

    @property
    def non_functional_requirements(self) -> tuple[RequirementResult, ...]:
        return tuple(r for r in self.requirements if r.category == "non_functional")

    @property
    def security_requirements(self) -> tuple[RequirementResult, ...]:
        return tuple(r for r in self.requirements if r.category == "security")

    @property
    def integration_requirements(self) -> tuple[RequirementResult, ...]:
        return tuple(r for r in self.requirements if r.category == "integration")


def assign_technical_spec_ids(
    *,
    requirements: list[RequirementCandidate],
    constraints: list[ConstraintCandidate],
    dependencies: list[DependencyCandidate],
    metadata: ProviderMetadata,
) -> TechnicalSpecAnalysisResult:
    return TechnicalSpecAnalysisResult(
        requirements=tuple(
            RequirementResult(
                id=uuid.uuid4(),
                category=item.category,
                identifier=item.identifier,
                statement=item.statement,
                priority=item.priority,
                actor=item.actor,
                measurable_criterion=item.measurable_criterion,
                source_page=item.source_page,
                evidence=item.evidence,
                confidence=item.confidence,
            )
            for item in requirements
        ),
        constraints=tuple(
            ConstraintResult(
                id=uuid.uuid4(),
                category=item.category,
                statement=item.statement,
                value_text=item.value_text,
                source_page=item.source_page,
                evidence=item.evidence,
                confidence=item.confidence,
            )
            for item in constraints
        ),
        dependencies=tuple(
            DependencyResult(
                id=uuid.uuid4(),
                name=item.name,
                dependency_type=item.dependency_type,
                description=item.description,
                source_page=item.source_page,
                evidence=item.evidence,
                confidence=item.confidence,
            )
            for item in dependencies
        ),
        provider=metadata.provider,
        model=metadata.model,
        latency_ms=metadata.latency_ms,
        input_tokens=metadata.input_tokens,
        output_tokens=metadata.output_tokens,
    )
