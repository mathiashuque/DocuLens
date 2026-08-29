"""Deterministic, bounded context selection for technical-specification
extraction.

Thin wrapper over `agent.classification.context.select_keyword_priority_context`
with technical-specification priority keywords: overview/scope/requirements/
capabilities/use cases, functional/non-functional, security/privacy/access
control/audit/encryption, APIs/integrations/interfaces/protocols/data
formats, performance/availability/capacity/scalability/reliability, and
architecture/platform/technology/compatibility/dependencies/constraints.
"""

from agent.classification.context import (
    DEFAULT_BUDGET_CHARS,
    ClassificationContext,
    SectionSpan,
    select_keyword_priority_context,
)

__all__ = [
    "DEFAULT_TECHNICAL_SPEC_BUDGET_CHARS",
    "SectionSpan",
    "select_technical_spec_context",
]

DEFAULT_TECHNICAL_SPEC_BUDGET_CHARS = DEFAULT_BUDGET_CHARS * 2

_PRIORITY_KEYWORDS: tuple[str, ...] = (
    "overview",
    "scope",
    "requirement",
    "capabilit",
    "use case",
    "functional",
    "security",
    "privacy",
    "access control",
    "audit",
    "encryption",
    "api",
    "integration",
    "interface",
    "protocol",
    "data format",
    "performance",
    "availability",
    "capacity",
    "scalability",
    "reliability",
    "architecture",
    "platform",
    "technology",
    "compatib",
    "dependenc",
    "constraint",
)


def select_technical_spec_context(
    *,
    filename: str,
    pages: list[tuple[int, str]],
    section_titles: list[str] | None = None,
    sections: list[SectionSpan] | None = None,
    budget_chars: int = DEFAULT_TECHNICAL_SPEC_BUDGET_CHARS,
) -> ClassificationContext:
    return select_keyword_priority_context(
        filename=filename,
        pages=pages,
        priority_keywords=_PRIORITY_KEYWORDS,
        section_titles=section_titles,
        sections=sections,
        budget_chars=budget_chars,
    )
